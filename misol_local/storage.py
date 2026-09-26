"""SQLite persistence.

EXPERIMENTAL. SQLite is intentionally used here because one weather console
reporting every few seconds is not a distributed-systems problem.
"""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from threading import Lock
from typing import Iterable

from .protocol import ParsedObservation


SCHEMA = """
CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    station_id TEXT NOT NULL,
    received_at TEXT NOT NULL,
    protocol TEXT NOT NULL,
    normalised_json TEXT NOT NULL,
    raw_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_observations_station_time
    ON observations(station_id, received_at DESC);
"""


class Store:
    def __init__(self, path: Path, store_raw: bool = True) -> None:
        self.path = path
        self.store_raw = store_raw
        self._lock = Lock()
        path.parent.mkdir(parents=True, exist_ok=True)
        self._initialise()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _initialise(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    def add(self, observation: ParsedObservation) -> int:
        raw = json.dumps(observation.raw_redacted, sort_keys=True) if self.store_raw else None
        normalised = json.dumps(observation.normalised, sort_keys=True)
        with self._lock, self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO observations
                    (station_id, received_at, protocol, normalised_json, raw_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    observation.station_id,
                    observation.received_at,
                    observation.protocol,
                    normalised,
                    raw,
                ),
            )
            return int(cursor.lastrowid)

    @staticmethod
    def _row(row: sqlite3.Row) -> dict[str, object]:
        result: dict[str, object] = {
            "id": row["id"],
            "station_id": row["station_id"],
            "received_at": row["received_at"],
            "protocol": row["protocol"],
            "data": json.loads(row["normalised_json"]),
        }
        if row["raw_json"]:
            result["raw"] = json.loads(row["raw_json"])
        return result

    def recent(self, limit: int = 100) -> list[dict[str, object]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM observations ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._row(row) for row in rows]

    def latest(self) -> list[dict[str, object]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT o.*
                FROM observations o
                JOIN (
                    SELECT station_id, MAX(id) AS max_id
                    FROM observations
                    GROUP BY station_id
                ) latest ON latest.max_id = o.id
                ORDER BY o.station_id
                """
            ).fetchall()
        return [self._row(row) for row in rows]

    def count(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS count FROM observations").fetchone()
        return int(row["count"])

    def iter_recent(self, limit: int = 1000) -> Iterable[dict[str, object]]:
        yield from reversed(self.recent(limit))
