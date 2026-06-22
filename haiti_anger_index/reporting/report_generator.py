"""
HTML report generator for the Haiti Anger Index.

Renders the Jinja2 template with snapshot data and writes an HTML file.
Falls back to simple string formatting when Jinja2 is unavailable.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape  # type: ignore
    _JINJA2_AVAILABLE = True
except ImportError:
    _JINJA2_AVAILABLE = False
    logger.warning("jinja2 not installed — HTML report generation disabled.")

_TEMPLATES_DIR = Path(__file__).parent / "templates"


class ReportGenerator:
    """
    Generates an HTML report from a HAI snapshot dict.

    Usage::

        gen = ReportGenerator(output_dir="reports")
        path = gen.generate(snapshot, history)
    """

    def __init__(self, output_dir: str = "reports") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self._env = None
        if _JINJA2_AVAILABLE:
            self._env = Environment(
                loader=FileSystemLoader(str(_TEMPLATES_DIR)),
                autoescape=select_autoescape(["html"]),
            )
            self._env.filters["tojson"] = json.dumps

    # ── Public API ────────────────────────────────────────────────────────────

    def generate(
        self,
        snapshot: Dict,
        history: Optional[List[Dict]] = None,
    ) -> str:
        """
        Render the report and return the output file path.
        """
        context = self._build_context(snapshot, history or [])
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"hai_report_{ts}.html"
        output_path = self.output_dir / filename

        if self._env is not None:
            template = self._env.get_template("anger_index_report.html")
            html = template.render(**context)
        else:
            html = self._fallback_html(context)

        output_path.write_text(html, encoding="utf-8")
        logger.info("Report written → %s", output_path)
        return str(output_path)

    # ── Context builder ───────────────────────────────────────────────────────

    def _build_context(self, snapshot: Dict, history: List[Dict]) -> Dict:
        now = datetime.now(timezone.utc)
        total = snapshot.get("total_posts", 0)
        pos = snapshot.get("positive_count", 0)
        neg = snapshot.get("negative_count", 0)
        neu = snapshot.get("neutral_count", 0)

        def pct(n: int) -> float:
            return round(n / total * 100, 1) if total else 0.0

        trend = snapshot.get("trend", {})

        # Platform chart data
        plat_bd = snapshot.get("platform_breakdown", {})
        platform_labels = list(plat_bd.keys())
        platform_neg = [plat_bd[p].get("negative", 0) for p in platform_labels]
        platform_pos = [plat_bd[p].get("positive", 0) for p in platform_labels]
        platform_neu = [plat_bd[p].get("neutral", 0)  for p in platform_labels]

        # Language chart data
        lang_bd = snapshot.get("language_breakdown", {})
        lang_label_map = {"en": "English", "fr": "French", "ht": "Creole", "unknown": "Unknown"}
        lang_labels = [lang_label_map.get(k, k) for k in lang_bd.keys()]
        lang_neg = [lang_bd[k].get("negative", 0) for k in lang_bd.keys()]

        # Historical trend
        trend_labels: List[str] = []
        trend_scores: List[float] = []
        for h in reversed(history):
            dt_str = h.get("computed_at", "")
            try:
                dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                trend_labels.append(dt.strftime("%b %d"))
            except (ValueError, AttributeError):
                trend_labels.append(dt_str[:10])
            trend_scores.append(h.get("overall_index", 0.0))
        # Add current snapshot
        trend_labels.append(now.strftime("%b %d"))
        trend_scores.append(snapshot.get("overall_index", 0.0))

        return {
            "report_date": now.strftime("%B %d, %Y"),
            "year": now.year,
            "period_start": snapshot.get("period_start", "")[:10],
            "period_end": snapshot.get("period_end", "")[:10] or now.strftime("%Y-%m-%d"),
            "overall_index": snapshot.get("overall_index", 0.0),
            "anger_color": snapshot.get("anger_level_color", "#4CAF50"),
            "anger_level": snapshot.get("anger_level", "Calm"),
            "total_posts": total,
            "positive_count": pos,
            "negative_count": neg,
            "neutral_count": neu,
            "pos_pct": pct(pos),
            "neg_pct": pct(neg),
            "neu_pct": pct(neu),
            "trend_direction": trend.get("direction", "stable"),
            "trend_change": abs(trend.get("change", 0.0)),
            "top_drivers": snapshot.get("top_drivers", []),
            "platform_breakdown": plat_bd,
            "topic_breakdown": snapshot.get("topic_breakdown", {}),
            "language_breakdown": lang_bd,
            "platform_labels": platform_labels,
            "platform_neg": platform_neg,
            "platform_pos": platform_pos,
            "platform_neu": platform_neu,
            "lang_labels": lang_labels,
            "lang_neg": lang_neg,
            "history": history,
            "trend_labels": trend_labels,
            "trend_scores": trend_scores,
        }

    # ── Minimal fallback ──────────────────────────────────────────────────────

    @staticmethod
    def _fallback_html(ctx: Dict) -> str:
        return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"/><title>Haiti Anger Index</title></head>
<body>
<h1>Haiti Anger Index — {ctx['report_date']}</h1>
<h2>Overall Score: {ctx['overall_index']} / 100 — {ctx['anger_level']}</h2>
<p>Total posts: {ctx['total_posts']} |
   Negative: {ctx['neg_pct']}% |
   Positive: {ctx['pos_pct']}% |
   Neutral: {ctx['neu_pct']}%</p>
<h3>Top Drivers</h3>
<ul>
{''.join(f"<li>{d['label']}: {d['weighted_anger_score']}</li>" for d in ctx['top_drivers'])}
</ul>
<p><em>Generated by POLLNEX Insights</em></p>
</body></html>"""
