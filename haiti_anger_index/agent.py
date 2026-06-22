"""
Haiti Anger Index — Main Orchestration Agent
============================================

Usage
-----
Run once (default):
    python -m haiti_anger_index.agent

Run on a schedule (every 6 hours):
    python -m haiti_anger_index.agent --schedule 6h

Dry run (no DB writes, just print stats):
    python -m haiti_anger_index.agent --dry-run

Options
-------
--db        Path to SQLite database  (default: haiti_anger_index.db)
--reports   Directory for HTML reports (default: reports/)
--schedule  Run interval: 1h, 6h, 12h, 24h
--dry-run   Print results without saving
--no-model  Skip ML model; use keyword-based fallback classifier
--platforms Comma-separated list: twitter,facebook,youtube,reddit,rss
            (default: all)
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("hai_agent.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("hai.agent")

from haiti_anger_index import config
from haiti_anger_index.aggregator.data_compiler import DataCompiler
from haiti_anger_index.classifier.language_detector import detect_language
from haiti_anger_index.classifier.sentiment_classifier import SentimentClassifier
from haiti_anger_index.classifier.topic_classifier import classify_topics
from haiti_anger_index.crawlers.facebook_crawler import FacebookCrawler
from haiti_anger_index.crawlers.reddit_crawler import RedditCrawler
from haiti_anger_index.crawlers.rss_crawler import RSSCrawler
from haiti_anger_index.crawlers.twitter_crawler import TwitterCrawler
from haiti_anger_index.crawlers.youtube_crawler import YouTubeCrawler
from haiti_anger_index.index.anger_index import AngerIndexCalculator
from haiti_anger_index.reporting.report_generator import ReportGenerator
from haiti_anger_index.storage.database import Database

_SCHEDULE_MAP = {"1h": 3600, "6h": 21600, "12h": 43200, "24h": 86400}

_ALL_PLATFORMS = ["twitter", "facebook", "youtube", "reddit", "rss"]


class HaitiAngerIndexAgent:
    """
    End-to-end pipeline:
      1. Crawl social media
      2. Classify language + sentiment + topics
      3. Compile statistics
      4. Compute HAI score
      5. Persist to DB
      6. Generate HTML report
    """

    def __init__(
        self,
        db_path: str = config.DB_PATH,
        reports_dir: str = config.REPORTS_DIR,
        platforms: Optional[List[str]] = None,
        dry_run: bool = False,
    ) -> None:
        self.dry_run = dry_run
        self.platforms = platforms or _ALL_PLATFORMS

        self.db = Database(db_path) if not dry_run else None
        self.classifier = SentimentClassifier()
        self.compiler = DataCompiler()
        self.calculator = AngerIndexCalculator()
        self.reporter = ReportGenerator(reports_dir)

        self._crawlers = self._build_crawlers()

    # ── Public API ────────────────────────────────────────────────────────────

    def run_once(self) -> Dict:
        """Execute a full pipeline cycle and return the snapshot dict."""
        run_start = datetime.now(timezone.utc)
        logger.info("=" * 60)
        logger.info("Haiti Anger Index Agent — run started %s", run_start.isoformat())

        # Step 1: Crawl
        raw_posts = self._crawl_all()
        logger.info("Total raw posts collected: %d", len(raw_posts))

        if not raw_posts:
            logger.warning("No posts collected — aborting run.")
            return {}

        # Step 2: Persist raw posts
        if self.db:
            self.db.upsert_posts(raw_posts)

        # Step 3: Classify (language + sentiment + topics)
        classified = self._classify(raw_posts)

        # Step 4: Update DB with classifications
        if self.db:
            for post in classified:
                self.db.update_post_classification(
                    post_id=post["id"],
                    platform=post["platform"],
                    language=post.get("language", "unknown"),
                    sentiment=post["sentiment"],
                    sentiment_score=post["sentiment_score"],
                    topics=post["topics"] if isinstance(post["topics"], list) else [],
                )

        # Step 5: Compile statistics
        stats = self.compiler.compile(classified)
        logger.info(
            "Stats → total=%d neg=%d pos=%d neu=%d neg_rate=%.3f",
            stats["total"],
            stats["negative"],
            stats["positive"],
            stats["neutral"],
            stats["neg_rate"],
        )

        # Step 6: Compute HAI
        history = self.db.get_anger_index_history(limit=52) if self.db else []
        period_end = datetime.now(timezone.utc).isoformat()
        period_start = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        snapshot = self.calculator.compute(stats, period_start, period_end, history)

        logger.info(
            "HAI Score: %.1f / 100  [%s]  trend=%s",
            snapshot["overall_index"],
            snapshot["anger_level"],
            snapshot.get("trend", {}).get("direction", "stable"),
        )

        # Step 7: Save snapshot
        if self.db:
            self.db.save_anger_index(snapshot)

        # Step 8: Generate report
        report_path = self.reporter.generate(snapshot, history)
        summary = (
            f"HAI={snapshot['overall_index']} | {snapshot['anger_level']} | "
            f"{stats['total']} posts | neg_rate={stats['neg_rate']:.1%}"
        )
        if self.db:
            self.db.save_report(report_path, snapshot["overall_index"], summary)

        logger.info("Report: %s", report_path)
        logger.info("Run completed in %.1f s", (datetime.now(timezone.utc) - run_start).total_seconds())

        if self.dry_run:
            self._print_summary(snapshot)

        return snapshot

    # ── Crawling ──────────────────────────────────────────────────────────────

    def _crawl_all(self) -> List[Dict]:
        posts: List[Dict] = []
        for name, crawler in self._crawlers.items():
            if name not in self.platforms:
                continue
            result = crawler.run()
            logger.info("[%s] → %d posts", name, len(result))
            posts.extend(result)
        return posts

    # ── Classification ────────────────────────────────────────────────────────

    def _classify(self, posts: List[Dict]) -> List[Dict]:
        logger.info("Classifying %d posts …", len(posts))
        texts = [p["content"] for p in posts]

        # Language detection
        languages = [detect_language(t) for t in texts]

        # Sentiment (batch)
        sentiments = self.classifier.classify_batch(texts)

        # Topics
        topics_list = [classify_topics(t) for t in texts]

        for i, post in enumerate(posts):
            post["language"] = languages[i]
            post["sentiment"], post["sentiment_score"] = sentiments[i]
            post["topics"] = topics_list[i]

        logger.info(
            "Classification done. neg=%d pos=%d neu=%d",
            sum(1 for p in posts if p["sentiment"] == "NEGATIVE"),
            sum(1 for p in posts if p["sentiment"] == "POSITIVE"),
            sum(1 for p in posts if p["sentiment"] == "NEUTRAL"),
        )
        return posts

    # ── Builder helpers ───────────────────────────────────────────────────────

    def _build_crawlers(self) -> Dict:
        return {
            "twitter": TwitterCrawler(),
            "facebook": FacebookCrawler(),
            "youtube": YouTubeCrawler(),
            "reddit": RedditCrawler(),
            "rss": RSSCrawler(),
        }

    # ── Printing ──────────────────────────────────────────────────────────────

    @staticmethod
    def _print_summary(snapshot: Dict) -> None:
        print("\n" + "=" * 60)
        print(f"  🇭🇹  HAITI ANGER INDEX (HAI™) — POLLNEX Insights")
        print("=" * 60)
        print(f"  Score       : {snapshot['overall_index']} / 100")
        print(f"  Level       : {snapshot['anger_level']}")
        print(f"  Posts       : {snapshot['total_posts']}")
        print(f"  Negative    : {snapshot['negative_count']}  "
              f"({snapshot['negative_count'] / max(snapshot['total_posts'], 1):.1%})")
        print(f"  Positive    : {snapshot['positive_count']}")
        print(f"  Neutral     : {snapshot['neutral_count']}")
        trend = snapshot.get("trend", {})
        direction = trend.get("direction", "stable")
        change = trend.get("change", 0)
        arrow = "▲" if direction == "rising" else ("▼" if direction == "falling" else "→")
        print(f"  Trend       : {arrow} {direction} ({change:+.1f} pts)")
        print("\n  Top Drivers:")
        for d in snapshot.get("top_drivers", []):
            print(f"    • {d['label']:30s}  anger={d['weighted_anger_score']:.1f}")
        print("=" * 60)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Haiti Anger Index Agent — POLLNEX Insights"
    )
    parser.add_argument("--db", default=config.DB_PATH, help="SQLite database path")
    parser.add_argument("--reports", default=config.REPORTS_DIR, help="Reports output directory")
    parser.add_argument("--schedule", choices=list(_SCHEDULE_MAP.keys()), default=None,
                        help="Run interval (e.g. 6h)")
    parser.add_argument("--dry-run", action="store_true", help="Print results, don't save")
    parser.add_argument("--platforms", default=",".join(_ALL_PLATFORMS),
                        help="Comma-separated platforms to crawl")
    args = parser.parse_args()

    platforms = [p.strip() for p in args.platforms.split(",") if p.strip()]

    agent = HaitiAngerIndexAgent(
        db_path=args.db,
        reports_dir=args.reports,
        platforms=platforms,
        dry_run=args.dry_run,
    )

    if args.schedule:
        interval = _SCHEDULE_MAP[args.schedule]
        logger.info("Running on a %s schedule (every %d seconds)", args.schedule, interval)
        while True:
            agent.run_once()
            logger.info("Next run in %d seconds …", interval)
            time.sleep(interval)
    else:
        agent.run_once()


if __name__ == "__main__":
    main()
