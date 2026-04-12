"""
RSS / News crawler.

Parses Haitian news RSS feeds and returns article summaries as posts.
Uses the feedparser library (pure-Python, no API key needed).
"""

import hashlib
import logging
from typing import Dict, List

from haiti_anger_index import config
from haiti_anger_index.crawlers.base import BaseCrawler

logger = logging.getLogger(__name__)

try:
    import feedparser  # type: ignore
    _FEEDPARSER_AVAILABLE = True
except ImportError:
    _FEEDPARSER_AVAILABLE = False
    logger.warning("feedparser not installed — RSS crawler disabled.")


class RSSCrawler(BaseCrawler):
    PLATFORM = "news_rss"

    def fetch(self) -> List[Dict]:
        if not _FEEDPARSER_AVAILABLE:
            logger.warning("[RSS] feedparser not available — skipping.")
            return []

        posts: List[Dict] = []
        per_feed = max(1, self.max_posts // max(len(config.RSS_FEEDS), 1))

        for source_name, feed_url in config.RSS_FEEDS.items():
            if len(posts) >= self.max_posts:
                break
            try:
                feed = feedparser.parse(feed_url)
                entries = feed.entries[:per_feed]
                for entry in entries:
                    title = entry.get("title", "")
                    summary = entry.get("summary", entry.get("description", ""))
                    content = f"{title}\n{summary}".strip()
                    if not content:
                        continue

                    link = entry.get("link", "")
                    published = entry.get("published", entry.get("updated", ""))
                    # Stable ID from URL hash
                    post_id = hashlib.md5(link.encode()).hexdigest() if link else hashlib.md5(content[:100].encode()).hexdigest()

                    posts.append(
                        self._make_post(
                            post_id=f"{source_name}_{post_id}",
                            content=content,
                            created_at=published,
                            url=link,
                            author=source_name,
                        )
                    )
                self._sleep()
            except Exception as exc:  # noqa: BLE001
                logger.error("[RSS] Feed '%s' failed: %s", source_name, exc)

        return posts[: self.max_posts]
