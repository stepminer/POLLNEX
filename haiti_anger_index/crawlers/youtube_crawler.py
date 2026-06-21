"""
YouTube crawler using the YouTube Data API v3.

Searches for Haiti-related videos and collects their top-level comments.
Requires the environment variable YOUTUBE_API_KEY.
"""

import logging
from typing import Dict, List

from haiti_anger_index import config
from haiti_anger_index.crawlers.base import BaseCrawler

logger = logging.getLogger(__name__)

try:
    from googleapiclient.discovery import build  # type: ignore
    _GOOGLE_API_AVAILABLE = True
except ImportError:
    _GOOGLE_API_AVAILABLE = False
    logger.warning("google-api-python-client not installed — YouTube crawler disabled.")


class YouTubeCrawler(BaseCrawler):
    PLATFORM = "youtube"

    def __init__(self) -> None:
        super().__init__()
        self._service = None
        if _GOOGLE_API_AVAILABLE and config.YOUTUBE_API_KEY:
            self._service = build("youtube", "v3", developerKey=config.YOUTUBE_API_KEY)

    # ── Public API ────────────────────────────────────────────────────────────

    def fetch(self) -> List[Dict]:
        if self._service is None:
            logger.warning("[YouTube] No API key configured — skipping.")
            return []

        video_ids = self._search_videos()
        posts: List[Dict] = []
        for vid_id in video_ids:
            if len(posts) >= self.max_posts:
                break
            posts.extend(self._fetch_comments(vid_id))
            self._sleep()
        return posts[: self.max_posts]

    # ── Private helpers ───────────────────────────────────────────────────────

    def _search_videos(self) -> List[str]:
        video_ids: List[str] = []
        for term in config.YOUTUBE_SEARCH_TERMS:
            try:
                response = (
                    self._service.search()
                    .list(
                        q=term,
                        part="id",
                        type="video",
                        maxResults=10,
                        relevanceLanguage="fr",
                        order="date",
                    )
                    .execute()
                )
                for item in response.get("items", []):
                    vid_id = item.get("id", {}).get("videoId")
                    if vid_id and vid_id not in video_ids:
                        video_ids.append(vid_id)
                self._sleep()
            except Exception as exc:  # noqa: BLE001
                logger.error("[YouTube] Search '%s' failed: %s", term, exc)
        return video_ids

    def _fetch_comments(self, video_id: str) -> List[Dict]:
        posts: List[Dict] = []
        try:
            response = (
                self._service.commentThreads()
                .list(
                    part="snippet",
                    videoId=video_id,
                    maxResults=50,
                    order="relevance",
                    textFormat="plainText",
                )
                .execute()
            )
            for item in response.get("items", []):
                snippet = item["snippet"]["topLevelComment"]["snippet"]
                posts.append(
                    self._make_post(
                        post_id=item["id"],
                        content=snippet.get("textDisplay", ""),
                        created_at=snippet.get("publishedAt", ""),
                        url=f"https://www.youtube.com/watch?v={video_id}",
                        author=snippet.get("authorDisplayName", ""),
                        likes=snippet.get("likeCount", 0),
                    )
                )
        except Exception as exc:  # noqa: BLE001
            logger.error("[YouTube] Comments for %s failed: %s", video_id, exc)
        return posts
