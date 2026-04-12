"""
Haiti Anger Index (HAI) calculator.

The index mirrors the methodology of Pollara's Rage Index:
- Overall score 0–100.
- Broken down by platform, topic, and language.
- Time-series trend (week-over-week change).
- Identifies the primary drivers of anger.

Formula
-------
The raw score is a blend of:
  1. Simple negative-sentiment rate (40 %)
  2. Engagement-weighted negative rate (40 %)
  3. Topic-severity adjustment (20 %)

The blended score is then min-max normalised to [0, 100].
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from haiti_anger_index import config

logger = logging.getLogger(__name__)


class AngerIndexCalculator:
    """
    Computes the Haiti Anger Index from compiled statistics.

    Usage::

        calc = AngerIndexCalculator()
        snapshot = calc.compute(stats, period_start, period_end)
    """

    # Weights for the three components
    W_NEG_RATE = 0.40
    W_ENG_WEIGHTED = 0.40
    W_TOPIC_SEVERITY = 0.20

    def compute(
        self,
        stats: Dict,
        period_start: Optional[str] = None,
        period_end: Optional[str] = None,
        history: Optional[List[Dict]] = None,
    ) -> Dict:
        """
        Compute the HAI snapshot.

        Parameters
        ----------
        stats : dict
            Output of DataCompiler.compile().
        period_start / period_end : str (ISO-8601)
            Time window covered by this snapshot.
        history : list of previous snapshots (used for trend calculation).

        Returns
        -------
        A dict ready to be saved via Database.save_anger_index().
        """
        if not stats or stats.get("total", 0) == 0:
            return self._zero_snapshot(period_start, period_end)

        raw_score = self._raw_score(stats)
        overall_index = round(raw_score * 100, 1)
        anger_level, anger_color = self._get_level(overall_index)

        platform_breakdown = self._platform_breakdown(stats["platforms"])
        topic_breakdown = self._topic_breakdown(stats["topics"])
        language_breakdown = self._language_breakdown(stats["languages"])

        trend = self._compute_trend(overall_index, history)

        return {
            "computed_at": datetime.now(timezone.utc).isoformat(),
            "period_start": period_start or "",
            "period_end": period_end or datetime.now(timezone.utc).isoformat(),
            "overall_index": overall_index,
            "platform_breakdown": platform_breakdown,
            "topic_breakdown": topic_breakdown,
            "language_breakdown": language_breakdown,
            "total_posts": stats["total"],
            "positive_count": stats["positive"],
            "negative_count": stats["negative"],
            "neutral_count": stats["neutral"],
            "anger_level": anger_level,
            "anger_level_color": anger_color,
            "trend": trend,
            "top_drivers": self._top_drivers(stats["topics"]),
            "neg_rate": stats["neg_rate"],
            "weighted_neg_rate": stats["weighted_neg_rate"],
        }

    # ── Score calculation ─────────────────────────────────────────────────────

    def _raw_score(self, stats: Dict) -> float:
        neg_rate = stats.get("neg_rate", 0.0)
        eng_rate = stats.get("weighted_neg_rate", 0.0)
        topic_severity = self._topic_severity_score(stats.get("topics", {}))

        score = (
            self.W_NEG_RATE * neg_rate
            + self.W_ENG_WEIGHTED * eng_rate
            + self.W_TOPIC_SEVERITY * topic_severity
        )
        return min(max(score, 0.0), 1.0)

    def _topic_severity_score(self, topics: Dict) -> float:
        """
        Weighted average of per-topic negative rates, where each topic's
        weight is taken from config.TOPICS.
        """
        total_w = 0.0
        weighted_neg = 0.0
        for topic_key, data in topics.items():
            topic_cfg = config.TOPICS.get(topic_key, {})
            weight = topic_cfg.get("weight", 1.0)
            neg_rate = data.get("neg_rate", 0.0)
            total_w += weight * data.get("total", 0)
            weighted_neg += weight * data.get("total", 0) * neg_rate
        return (weighted_neg / total_w) if total_w else 0.0

    # ── Per-breakdown helpers ─────────────────────────────────────────────────

    def _platform_breakdown(self, platforms: Dict) -> Dict:
        result = {}
        for plat, data in platforms.items():
            total = data.get("total", 0)
            neg = data.get("negative", 0)
            pos = data.get("positive", 0)
            result[plat] = {
                "label": plat.replace("_", " ").title(),
                "total": total,
                "positive": pos,
                "negative": neg,
                "neutral": data.get("neutral", 0),
                "neg_rate": data.get("neg_rate", 0.0),
                "hai_contribution": round(data.get("neg_rate", 0.0) * 100, 1),
            }
        return result

    def _topic_breakdown(self, topics: Dict) -> Dict:
        result = {}
        for key, data in topics.items():
            topic_cfg = config.TOPICS.get(key, {})
            neg_rate = data.get("neg_rate", 0.0)
            weight = topic_cfg.get("weight", 1.0)
            result[key] = {
                "label": topic_cfg.get("label", key.replace("_", " ").title()),
                "label_fr": topic_cfg.get("label_fr", ""),
                "label_ht": topic_cfg.get("label_ht", ""),
                "total": data.get("total", 0),
                "positive": data.get("positive", 0),
                "negative": data.get("negative", 0),
                "neutral": data.get("neutral", 0),
                "neg_rate": neg_rate,
                "severity_weight": weight,
                "weighted_anger_score": round(neg_rate * weight * 100, 1),
                "weighted_neg_score": data.get("weighted_neg_score", 0.0),
            }
        return result

    def _language_breakdown(self, languages: Dict) -> Dict:
        result = {}
        lang_labels = {"en": "English", "fr": "French", "ht": "Haitian Creole", "unknown": "Unknown"}
        for lang, data in languages.items():
            result[lang] = {
                "label": lang_labels.get(lang, lang.upper()),
                "total": data.get("total", 0),
                "positive": data.get("positive", 0),
                "negative": data.get("negative", 0),
                "neutral": data.get("neutral", 0),
                "neg_rate": data.get("neg_rate", 0.0),
            }
        return result

    # ── Trend ─────────────────────────────────────────────────────────────────

    def _compute_trend(self, current: float, history: Optional[List[Dict]]) -> Dict:
        if not history:
            return {"direction": "stable", "change": 0.0, "previous": None}
        prev = history[0].get("overall_index")
        if prev is None:
            return {"direction": "stable", "change": 0.0, "previous": None}
        change = round(current - prev, 1)
        if change > 1:
            direction = "rising"
        elif change < -1:
            direction = "falling"
        else:
            direction = "stable"
        return {"direction": direction, "change": change, "previous": round(prev, 1)}

    # ── Top drivers ───────────────────────────────────────────────────────────

    def _top_drivers(self, topics: Dict, top_n: int = 5) -> List[Dict]:
        """Return the top N topics driving anger, sorted by weighted_anger_score."""
        scored = []
        for key, data in topics.items():
            topic_cfg = config.TOPICS.get(key, {})
            neg_rate = data.get("neg_rate", 0.0)
            weight = topic_cfg.get("weight", 1.0)
            scored.append({
                "key": key,
                "label": topic_cfg.get("label", key.replace("_", " ").title()),
                "neg_rate": neg_rate,
                "weighted_anger_score": round(neg_rate * weight * 100, 1),
                "total_posts": data.get("total", 0),
            })
        scored.sort(key=lambda x: x["weighted_anger_score"], reverse=True)
        return scored[:top_n]

    # ── Level lookup ──────────────────────────────────────────────────────────

    @staticmethod
    def _get_level(score: float) -> Tuple[str, str]:
        for lo, hi, label, _label_fr, _label_ht, color in config.ANGER_LEVELS:
            if lo <= score <= hi:
                return label, color
        return "Enraged", "#F44336"

    @staticmethod
    def _zero_snapshot(period_start: Optional[str], period_end: Optional[str]) -> Dict:
        return {
            "computed_at": datetime.now(timezone.utc).isoformat(),
            "period_start": period_start or "",
            "period_end": period_end or datetime.now(timezone.utc).isoformat(),
            "overall_index": 0.0,
            "platform_breakdown": {},
            "topic_breakdown": {},
            "language_breakdown": {},
            "total_posts": 0,
            "positive_count": 0,
            "negative_count": 0,
            "neutral_count": 0,
            "anger_level": "Calm",
            "anger_level_color": "#4CAF50",
            "trend": {"direction": "stable", "change": 0.0, "previous": None},
            "top_drivers": [],
            "neg_rate": 0.0,
            "weighted_neg_rate": 0.0,
        }
