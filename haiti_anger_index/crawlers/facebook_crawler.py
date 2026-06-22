"""
Facebook / Instagram crawler via the Graph API.

Public page posts are accessible with a valid Page Access Token or
App Access Token.  Falls back gracefully when none is configured.

Note: Direct scraping of Facebook is prohibited by Meta's ToS.
      This crawler uses only the official Graph API.
"""

import logging
from typing import Dict, List
from urllib.parse import urlencode

import requests

from haiti_anger_index import config
from haiti_anger_index.crawlers.base import BaseCrawler

logger = logging.getLogger(__name__)

# Public Facebook pages / accounts relevant to Haiti
HAITI_FB_PAGES = [
    "LeNouvellisteHaiti",
    "HaitiLibreOfficial",
    "RadioKiskeya",
    "alternativepresshaiti",
    "loophaiti",
]

GRAPH_API_BASE = "https://graph.facebook.com/v19.0"


class FacebookCrawler(BaseCrawler):
    PLATFORM = "facebook"

    def __init__(self) -> None:
        super().__init__()
        self._token = config.FACEBOOK_ACCESS_TOKEN

    def fetch(self) -> List[Dict]:
        if not self._token:
            logger.warning("[Facebook] No access token configured — skipping.")
            return []

        posts: List[Dict] = []
        per_page = max(1, self.max_posts // len(HAITI_FB_PAGES))

        for page_id in HAITI_FB_PAGES:
            if len(posts) >= self.max_posts:
                break
            posts.extend(self._fetch_page_posts(page_id, per_page))
            self._sleep()

        return posts[: self.max_posts]

    # ── Private ───────────────────────────────────────────────────────────────

    def _fetch_page_posts(self, page_id: str, limit: int) -> List[Dict]:
        params = {
            "fields": "id,message,created_time,permalink_url,reactions.summary(true),shares,comments.summary(true)",
            "limit": limit,
            "access_token": self._token,
        }
        url = f"{GRAPH_API_BASE}/{page_id}/posts?{urlencode(params)}"
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            result: List[Dict] = []
            for item in data.get("data", []):
                message = item.get("message", "")
                if not message:
                    continue
                likes = item.get("reactions", {}).get("summary", {}).get("total_count", 0)
                shares = item.get("shares", {}).get("count", 0)
                comments = item.get("comments", {}).get("summary", {}).get("total_count", 0)
                result.append(
                    self._make_post(
                        post_id=item["id"],
                        content=message,
                        created_at=item.get("created_time", ""),
                        url=item.get("permalink_url", ""),
                        author=page_id,
                        likes=likes,
                        shares=shares,
                        comments=comments,
                    )
                )
            return result
        except Exception as exc:  # noqa: BLE001
            logger.error("[Facebook] Page '%s' failed: %s", page_id, exc)
            return []
