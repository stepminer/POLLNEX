"""
Data compiler: aggregates classified posts into per-platform and
overall statistics used by the Anger Index calculator.
"""

import json
import logging
import math
from collections import defaultdict
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

from haiti_anger_index import config


class DataCompiler:
    """
    Compiles a list of classified post dicts into aggregate statistics.

    Input posts must have: platform, sentiment, sentiment_score,
    language, topics (JSON string or list), engagement_score.
    """

    def compile(self, posts: List[Dict]) -> Dict:
        """
        Return a statistics dict with keys:

            total, positive, negative, neutral,
            platforms, languages, topics,
            neg_rate, weighted_neg_rate,
            top_negative_keywords
        """
        if not posts:
            return self._empty()

        total = len(posts)
        pos = sum(1 for p in posts if p.get("sentiment") == "POSITIVE")
        neg = sum(1 for p in posts if p.get("sentiment") == "NEGATIVE")
        neu = sum(1 for p in posts if p.get("sentiment") == "NEUTRAL")

        platforms = self._by_platform(posts)
        languages = self._by_language(posts)
        topics = self._by_topic(posts)
        neg_rate = neg / total if total else 0.0
        weighted_neg_rate = self._weighted_neg_rate(posts)

        return {
            "total": total,
            "positive": pos,
            "negative": neg,
            "neutral": neu,
            "neg_rate": round(neg_rate, 4),
            "weighted_neg_rate": round(weighted_neg_rate, 4),
            "platforms": platforms,
            "languages": languages,
            "topics": topics,
        }

    # ── Per-platform breakdown ────────────────────────────────────────────────

    def _by_platform(self, posts: List[Dict]) -> Dict:
        buckets: Dict[str, Dict] = defaultdict(lambda: {"total": 0, "positive": 0, "negative": 0, "neutral": 0})
        for p in posts:
            plat = p.get("platform", "unknown")
            sent = p.get("sentiment", "NEUTRAL")
            buckets[plat]["total"] += 1
            buckets[plat][sent.lower()] = buckets[plat].get(sent.lower(), 0) + 1

        result = {}
        for plat, counts in buckets.items():
            t = counts["total"]
            result[plat] = {
                "total": t,
                "positive": counts.get("positive", 0),
                "negative": counts.get("negative", 0),
                "neutral": counts.get("neutral", 0),
                "neg_rate": round(counts.get("negative", 0) / t, 4) if t else 0.0,
            }
        return result

    # ── Per-language breakdown ────────────────────────────────────────────────

    def _by_language(self, posts: List[Dict]) -> Dict:
        buckets: Dict[str, Dict] = defaultdict(lambda: {"total": 0, "positive": 0, "negative": 0, "neutral": 0})
        for p in posts:
            lang = p.get("language") or "unknown"
            sent = p.get("sentiment", "NEUTRAL")
            buckets[lang]["total"] += 1
            buckets[lang][sent.lower()] = buckets[lang].get(sent.lower(), 0) + 1

        result = {}
        for lang, counts in buckets.items():
            t = counts["total"]
            result[lang] = {
                "total": t,
                "positive": counts.get("positive", 0),
                "negative": counts.get("negative", 0),
                "neutral": counts.get("neutral", 0),
                "neg_rate": round(counts.get("negative", 0) / t, 4) if t else 0.0,
            }
        return result

    # ── Per-topic breakdown ───────────────────────────────────────────────────

    def _by_topic(self, posts: List[Dict]) -> Dict:
        buckets: Dict[str, Dict] = defaultdict(lambda: {
            "total": 0, "positive": 0, "negative": 0, "neutral": 0,
            "neg_rate": 0.0, "weighted_neg_score": 0.0,
        })

        for p in posts:
            topics = p.get("topics") or []
            if isinstance(topics, str):
                try:
                    topics = json.loads(topics)
                except (json.JSONDecodeError, TypeError):
                    topics = ["general"]

            sent = p.get("sentiment", "NEUTRAL")
            score = float(p.get("sentiment_score") or 0.5)
            eng = float(p.get("engagement_score") or 1.0)

            for topic in topics:
                buckets[topic]["total"] += 1
                buckets[topic][sent.lower()] = buckets[topic].get(sent.lower(), 0) + 1
                if sent == "NEGATIVE":
                    weight = config.TOPICS.get(topic, {}).get("weight", 1.0)
                    buckets[topic]["weighted_neg_score"] += score * eng * weight

        result = {}
        for topic, counts in buckets.items():
            t = counts["total"]
            result[topic] = {
                "total": t,
                "positive": counts.get("positive", 0),
                "negative": counts.get("negative", 0),
                "neutral": counts.get("neutral", 0),
                "neg_rate": round(counts.get("negative", 0) / t, 4) if t else 0.0,
                "weighted_neg_score": round(counts.get("weighted_neg_score", 0.0), 2),
                "label": config.TOPICS.get(topic, {}).get("label", topic.replace("_", " ").title()),
            }
        return result

    # ── Engagement-weighted negative rate ────────────────────────────────────

    def _weighted_neg_rate(self, posts: List[Dict]) -> float:
        """
        Compute engagement-weighted negative sentiment rate.

        Posts with higher engagement counts more toward the index.
        Uses log(1 + engagement) to dampen outliers.
        """
        total_weight = 0.0
        neg_weight = 0.0
        for p in posts:
            eng = float(p.get("engagement_score") or 1.0)
            w = math.log1p(eng)
            total_weight += w
            if p.get("sentiment") == "NEGATIVE":
                score = float(p.get("sentiment_score") or 0.5)
                neg_weight += w * score
        return (neg_weight / total_weight) if total_weight else 0.0

    @staticmethod
    def _empty() -> Dict:
        return {
            "total": 0,
            "positive": 0,
            "negative": 0,
            "neutral": 0,
            "neg_rate": 0.0,
            "weighted_neg_rate": 0.0,
            "platforms": {},
            "languages": {},
            "topics": {},
        }
