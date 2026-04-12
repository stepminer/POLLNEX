"""
Abstract base class for all social-media crawlers.
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, List

from haiti_anger_index import config

logger = logging.getLogger(__name__)


class BaseCrawler(ABC):
    """
    Every platform crawler inherits from this class.

    Subclasses must implement :py:meth:`fetch` which returns a list of
    post dicts with at minimum the keys:

        id, platform, content, created_at

    Optional but encouraged: url, author, likes, shares, comments.
    """

    PLATFORM: str = "unknown"

    def __init__(self) -> None:
        self.delay = config.CRAWL_DELAY
        self.max_posts = config.MAX_POSTS_PER_PLATFORM

    @abstractmethod
    def fetch(self) -> List[Dict]:
        """Fetch posts and return normalised dicts."""

    def _sleep(self) -> None:
        time.sleep(self.delay)

    def _make_post(
        self,
        post_id: str,
        content: str,
        created_at: str = "",
        url: str = "",
        author: str = "",
        likes: int = 0,
        shares: int = 0,
        comments: int = 0,
    ) -> Dict:
        """Return a normalised post dict."""
        return {
            "id": str(post_id),
            "platform": self.PLATFORM,
            "content": content,
            "created_at": created_at,
            "url": url,
            "author": author,
            "likes": likes,
            "shares": shares,
            "comments": comments,
            "sentiment": None,
            "sentiment_score": None,
            "topics": None,
            "engagement_score": float(likes + shares * 2 + comments * 1.5),
        }

    def run(self) -> List[Dict]:
        logger.info("[%s] Starting crawl …", self.PLATFORM)
        try:
            posts = self.fetch()
            logger.info("[%s] Fetched %d posts", self.PLATFORM, len(posts))
            return posts
        except Exception as exc:  # noqa: BLE001
            logger.error("[%s] Crawl failed: %s", self.PLATFORM, exc)
            return []
