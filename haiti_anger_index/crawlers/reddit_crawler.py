"""
Reddit crawler using PRAW.

Searches Haiti-related subreddits for posts and their top-level comments.
Requires REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET env variables.
"""

import logging
from typing import Dict, List

from haiti_anger_index import config
from haiti_anger_index.crawlers.base import BaseCrawler

logger = logging.getLogger(__name__)

try:
    import praw  # type: ignore
    _PRAW_AVAILABLE = True
except ImportError:
    _PRAW_AVAILABLE = False
    logger.warning("praw not installed — Reddit crawler disabled.")


class RedditCrawler(BaseCrawler):
    PLATFORM = "reddit"

    def __init__(self) -> None:
        super().__init__()
        self._reddit = None
        if _PRAW_AVAILABLE and config.REDDIT_CLIENT_ID and config.REDDIT_CLIENT_SECRET:
            self._reddit = praw.Reddit(
                client_id=config.REDDIT_CLIENT_ID,
                client_secret=config.REDDIT_CLIENT_SECRET,
                user_agent=config.REDDIT_USER_AGENT,
            )

    def fetch(self) -> List[Dict]:
        if self._reddit is None:
            logger.warning("[Reddit] Credentials not configured — skipping.")
            return []

        posts: List[Dict] = []
        per_sub = max(1, self.max_posts // len(config.REDDIT_SUBREDDITS))

        for sub_name in config.REDDIT_SUBREDDITS:
            if len(posts) >= self.max_posts:
                break
            try:
                subreddit = self._reddit.subreddit(sub_name)
                submissions = list(subreddit.search("Haiti OR Haïti OR Ayiti", limit=per_sub, sort="new"))
                for submission in submissions:
                    from datetime import datetime, timezone
                    ts = datetime.fromtimestamp(submission.created_utc, tz=timezone.utc).isoformat()
                    posts.append(
                        self._make_post(
                            post_id=submission.id,
                            content=f"{submission.title}\n{submission.selftext}".strip(),
                            created_at=ts,
                            url=f"https://reddit.com{submission.permalink}",
                            author=str(submission.author or ""),
                            likes=submission.score,
                            comments=submission.num_comments,
                        )
                    )
                    # Fetch top-level comments (up to 5 per post)
                    try:
                        submission.comments.replace_more(limit=0)
                        for comment in list(submission.comments)[:5]:
                            posts.append(
                                self._make_post(
                                    post_id=comment.id,
                                    content=comment.body,
                                    created_at=datetime.fromtimestamp(
                                        comment.created_utc, tz=timezone.utc
                                    ).isoformat(),
                                    url=f"https://reddit.com{comment.permalink}",
                                    author=str(comment.author or ""),
                                    likes=comment.score,
                                )
                            )
                    except Exception as exc:  # noqa: BLE001
                        logger.debug("[Reddit] Comment fetch error: %s", exc)
                self._sleep()
            except Exception as exc:  # noqa: BLE001
                logger.error("[Reddit] Subreddit '%s' failed: %s", sub_name, exc)

        return posts[: self.max_posts]
