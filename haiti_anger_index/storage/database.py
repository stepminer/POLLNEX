"""
SQLite storage layer for the Haiti Anger Index.

Schema
------
posts            — every collected social-media post (deduplicated by id + platform)
anger_index      — one snapshot per agent run with the computed HAI score
"""

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Dict, Generator, List, Optional

logger = logging.getLogger(__name__)

DDL = """
CREATE TABLE IF NOT EXISTS posts (
    id               TEXT    NOT NULL,
    platform         TEXT    NOT NULL,
    url              TEXT,
    author           TEXT,
    content          TEXT    NOT NULL,
    language         TEXT,
    created_at       TEXT,
    collected_at     TEXT    DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    likes            INTEGER DEFAULT 0,
    shares           INTEGER DEFAULT 0,
    comments         INTEGER DEFAULT 0,
    sentiment        TEXT,
    sentiment_score  REAL,
    topics           TEXT,
    engagement_score REAL    DEFAULT 0,
    PRIMARY KEY (id, platform)
);

CREATE TABLE IF NOT EXISTS anger_index (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    computed_at         TEXT    DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    period_start        TEXT,
    period_end          TEXT,
    overall_index       REAL,
    platform_breakdown  TEXT,
    topic_breakdown     TEXT,
    language_breakdown  TEXT,
    total_posts         INTEGER,
    positive_count      INTEGER,
    negative_count      INTEGER,
    neutral_count       INTEGER,
    anger_level         TEXT,
    anger_level_color   TEXT
);

CREATE TABLE IF NOT EXISTS reports (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    report_path TEXT,
    index_value REAL,
    summary     TEXT
);
"""


class Database:
    """Thin wrapper around sqlite3 for the Haiti Anger Index."""

    def __init__(self, db_path: str = "haiti_anger_index.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript(DDL)
        logger.info("Database initialised at %s", self.db_path)

    @contextmanager
    def _conn(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ── Posts ─────────────────────────────────────────────────────────────────

    def upsert_post(self, post: Dict) -> None:
        sql = """
        INSERT OR REPLACE INTO posts
            (id, platform, url, author, content, language, created_at,
             likes, shares, comments, sentiment, sentiment_score, topics, engagement_score)
        VALUES
            (:id, :platform, :url, :author, :content, :language, :created_at,
             :likes, :shares, :comments, :sentiment, :sentiment_score, :topics, :engagement_score)
        """
        row = dict(post)
        row.setdefault("url", None)
        row.setdefault("author", None)
        row.setdefault("language", None)
        row.setdefault("created_at", datetime.utcnow().isoformat())
        row.setdefault("likes", 0)
        row.setdefault("shares", 0)
        row.setdefault("comments", 0)
        row.setdefault("sentiment", None)
        row.setdefault("sentiment_score", None)
        row.setdefault("topics", None)
        row.setdefault("engagement_score", 0.0)
        if isinstance(row.get("topics"), list):
            row["topics"] = json.dumps(row["topics"])
        with self._conn() as conn:
            conn.execute(sql, row)

    def upsert_posts(self, posts: List[Dict]) -> None:
        for post in posts:
            self.upsert_post(post)
        logger.info("Upserted %d posts", len(posts))

    def get_unclassified_posts(self, limit: int = 1000) -> List[Dict]:
        sql = "SELECT * FROM posts WHERE sentiment IS NULL LIMIT ?"
        with self._conn() as conn:
            rows = conn.execute(sql, (limit,)).fetchall()
        return [dict(r) for r in rows]

    def update_post_classification(
        self,
        post_id: str,
        platform: str,
        language: str,
        sentiment: str,
        sentiment_score: float,
        topics: List[str],
    ) -> None:
        sql = """
        UPDATE posts
        SET language=?, sentiment=?, sentiment_score=?, topics=?
        WHERE id=? AND platform=?
        """
        with self._conn() as conn:
            conn.execute(
                sql,
                (language, sentiment, sentiment_score, json.dumps(topics), post_id, platform),
            )

    def get_posts_for_period(
        self,
        period_start: Optional[str] = None,
        period_end: Optional[str] = None,
    ) -> List[Dict]:
        conditions = ["sentiment IS NOT NULL"]
        params: List = []
        if period_start:
            conditions.append("collected_at >= ?")
            params.append(period_start)
        if period_end:
            conditions.append("collected_at <= ?")
            params.append(period_end)
        sql = "SELECT * FROM posts WHERE " + " AND ".join(conditions)
        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    # ── Anger Index ───────────────────────────────────────────────────────────

    def save_anger_index(self, snapshot: Dict) -> int:
        sql = """
        INSERT INTO anger_index
            (computed_at, period_start, period_end, overall_index,
             platform_breakdown, topic_breakdown, language_breakdown,
             total_posts, positive_count, negative_count, neutral_count,
             anger_level, anger_level_color)
        VALUES
            (:computed_at, :period_start, :period_end, :overall_index,
             :platform_breakdown, :topic_breakdown, :language_breakdown,
             :total_posts, :positive_count, :negative_count, :neutral_count,
             :anger_level, :anger_level_color)
        """
        row = dict(snapshot)
        for key in ("platform_breakdown", "topic_breakdown", "language_breakdown"):
            if isinstance(row.get(key), dict):
                row[key] = json.dumps(row[key])
        with self._conn() as conn:
            cursor = conn.execute(sql, row)
        return cursor.lastrowid

    def get_anger_index_history(self, limit: int = 52) -> List[Dict]:
        sql = "SELECT * FROM anger_index ORDER BY computed_at DESC LIMIT ?"
        with self._conn() as conn:
            rows = conn.execute(sql, (limit,)).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            for key in ("platform_breakdown", "topic_breakdown", "language_breakdown"):
                if d.get(key):
                    try:
                        d[key] = json.loads(d[key])
                    except (json.JSONDecodeError, TypeError):
                        pass
            results.append(d)
        return results

    def get_latest_anger_index(self) -> Optional[Dict]:
        history = self.get_anger_index_history(limit=1)
        return history[0] if history else None

    # ── Reports ───────────────────────────────────────────────────────────────

    def save_report(self, report_path: str, index_value: float, summary: str) -> None:
        sql = "INSERT INTO reports (report_path, index_value, summary) VALUES (?, ?, ?)"
        with self._conn() as conn:
            conn.execute(sql, (report_path, index_value, summary))
        logger.info("Report saved → %s", report_path)
