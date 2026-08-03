#!/usr/bin/env python3
"""Run HAI agent with network-first mode and SQLite cache fallback."""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = REPO_ROOT / "data" / "hai_cache.db"


def ensure_cache_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS hai_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recorded_at TEXT NOT NULL,
            source TEXT NOT NULL,
            payload_json TEXT NOT NULL
        )
        """
    )
    connection.commit()


def fetch_live_payload(url: str, timeout: int) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "pollnex-hai-agent/1.0"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
    parsed = json.loads(body)
    if isinstance(parsed, dict):
        return parsed
    return {"value": parsed}


def save_snapshot(connection: sqlite3.Connection, source: str, payload: dict[str, Any]) -> None:
    connection.execute(
        """
        INSERT INTO hai_snapshots (recorded_at, source, payload_json)
        VALUES (?, ?, ?)
        """,
        (
            datetime.now(timezone.utc).isoformat(),
            source,
            json.dumps(payload, sort_keys=True, separators=(",", ":")),
        ),
    )
    connection.commit()


def load_latest_snapshot(connection: sqlite3.Connection) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT payload_json
        FROM hai_snapshots
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()
    if not row:
        return None
    return json.loads(row[0])


def normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    if "hai_score" not in normalized and "score" in normalized:
        normalized["hai_score"] = normalized["score"]
    return normalized


def main() -> int:
    db_path = Path(os.getenv("HAI_CACHE_DB", str(DEFAULT_DB_PATH)))
    source_url = os.getenv("HAI_SOURCE_URL", "").strip()
    timeout_seconds = int(os.getenv("HAI_REQUEST_TIMEOUT_SECONDS", "8"))

    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        ensure_cache_schema(connection)

        runtime_mode = "cached"
        payload: dict[str, Any] | None = None

        if source_url:
            try:
                payload = normalize_payload(fetch_live_payload(source_url, timeout_seconds))
                save_snapshot(connection, "network", payload)
                runtime_mode = "network"
            except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
                print(f"[WARN] Network source unavailable, falling back to cached DB: {error}")

        if payload is None:
            payload = load_latest_snapshot(connection)
            if payload is None:
                print(
                    "[ERROR] No cached HAI snapshot found and network source is unavailable.",
                    file=sys.stderr,
                )
                return 1

    print(f"[INFO] HAI agent runtime mode: {runtime_mode}")
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
