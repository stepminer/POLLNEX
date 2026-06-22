"""
Twitter / X crawler using the v2 API (tweepy).

Requires the environment variable TWITTER_BEARER_TOKEN.
Falls back gracefully when no token is configured.
"""

import logging
from typing import Dict, List

from haiti_anger_index import config
from haiti_anger_index.crawlers.base import BaseCrawler

logger = logging.getLogger(__name__)

try:
    import tweepy  # type: ignore
    _TWEEPY_AVAILABLE = True
except ImportError:
    _TWEEPY_AVAILABLE = False
    logger.warning("tweepy not installed — Twitter crawler disabled.")


class TwitterCrawler(BaseCrawler):
    PLATFORM = "twitter"

    def __init__(self) -> None:
        super().__init__()
        self._client = None
        if _TWEEPY_AVAILABLE and config.TWITTER_BEARER_TOKEN:
            self._client = tweepy.Client(
                bearer_token=config.TWITTER_BEARER_TOKEN,
                wait_on_rate_limit=True,
            )

    def fetch(self) -> List[Dict]:
        if self._client is None:
            logger.warning("[Twitter] No bearer token configured — skipping.")
            return []

        posts: List[Dict] = []
        tweet_fields = ["created_at", "public_metrics", "author_id", "lang"]

        for query in config.TWITTER_SEARCH_QUERIES:
            if len(posts) >= self.max_posts:
                break
            try:
                response = self._client.search_recent_tweets(
                    query=f"{query} -is:retweet",
                    max_results=min(100, self.max_posts - len(posts)),
                    tweet_fields=tweet_fields,
                )
                if not response.data:
                    continue
                for tweet in response.data:
                    metrics = tweet.public_metrics or {}
                    posts.append(
                        self._make_post(
                            post_id=str(tweet.id),
                            content=tweet.text,
                            created_at=str(tweet.created_at or ""),
                            url=f"https://twitter.com/i/web/status/{tweet.id}",
                            author=str(tweet.author_id or ""),
                            likes=metrics.get("like_count", 0),
                            shares=metrics.get("retweet_count", 0),
                            comments=metrics.get("reply_count", 0),
                        )
                    )
                    if len(posts) >= self.max_posts:
                        break
                self._sleep()
            except Exception as exc:  # noqa: BLE001
                logger.error("[Twitter] Query '%s' failed: %s", query, exc)
        return posts
