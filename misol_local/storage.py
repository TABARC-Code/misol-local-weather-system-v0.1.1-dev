"""SQLite persistence for MISOL Local.

EXPERIMENTAL. SQLite is intentionally used here because one weather console
reporting every few seconds is not a distributed-systems problem.

Author: TABARC-Code
"""

from __future__ import annotations

from contextlib import closing
import json
from pathlib import Path
import sqlite3
from threading import Lock
from typing import Iterable

from .calibration import CalibrationSample
from .protocol import ParsedObservation


SCHEMA = """
CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    station_id TEXT NOT NULL,
    received_at TEXT NOT NULL,
    protocol TEXT NOT NULL,
    normalised_json TEXT NOT NULL,
    raw_json TEXT,
    external_json TEXT,
    best_estimate_json TEXT,
    crosscheck_json TEXT,
    quality_json TEXT,
    calibration_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_observations_station_time
    ON observations(station_id, received_at DESC);

CREATE TABLE IF NOT EXISTS calibration_samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    station_id TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    field TEXT NOT NULL,
    local_value REAL NOT NULL,
    reference_value REAL NOT NULL,
    bias REAL NOT NULL,
    providers_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_calibration_station_field
    ON calibration_samples(station_id, field, id DESC);
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
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _initialise(self) -> None:
        with closing(self._connect()) as conn, conn:
            conn.executescript(SCHEMA)
            columns = {row[1] for row in conn.execute("PRAGMA table_info(observations)")}
            for name in ("external_json", "best_estimate_json", "crosscheck_json", "quality_json", "calibration_json"):
                if name not in columns:
                    conn.execute(f"ALTER TABLE observations ADD COLUMN {name} TEXT")

    def add(self, observation: ParsedObservation, *, external=None, best_estimate=None, crosscheck=None, quality=None, calibration=None) -> int:
        raw = json.dumps(observation.raw_redacted, sort_keys=True) if self.store_raw else None
        normalised = json.dumps(observation.normalised, sort_keys=True)
        values = [
            json.dumps(value, sort_keys=True) if value else None
            for value in (external, best_estimate, crosscheck, quality, calibration)
        ]
        with self._lock, closing(self._connect()) as conn, conn:
            cursor = conn.execute(
                """
                INSERT INTO observations
                    (station_id, received_at, protocol, normalised_json, raw_json,
                     external_json, best_estimate_json, crosscheck_json, quality_json, calibration_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (observation.station_id, observation.received_at, observation.protocol, normalised, raw, *values),
            )
            return int(cursor.lastrowid)

    def add_calibration_samples(self, station_id: str, observed_at: str, samples: list[CalibrationSample]) -> int:
        if not samples:
            return 0
        rows = [
            (station_id, observed_at, s.field, s.local_value, s.reference_value, s.bias, json.dumps(s.providers, sort_keys=True))
            for s in samples
        ]
        with self._lock, closing(self._connect()) as conn, conn:
            conn.executemany(
                """
                INSERT INTO calibration_samples
                    (station_id, observed_at, field, local_value, reference_value, bias, providers_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        return len(rows)

    def calibration_biases(self, station_id: str, field: str, limit: int) -> list[float]:
        with closing(self._connect()) as conn, conn:
            rows = conn.execute(
                "SELECT bias FROM calibration_samples WHERE station_id = ? AND field = ? ORDER BY id DESC LIMIT ?",
                (station_id, field, limit),
            ).fetchall()
        return [float(row["bias"]) for row in rows]

    def calibration_counts(self, station_id: str) -> dict[str, int]:
        with closing(self._connect()) as conn, conn:
            rows = conn.execute(
                "SELECT field, COUNT(*) AS count FROM calibration_samples WHERE station_id = ? GROUP BY field ORDER BY field",
                (station_id,),
            ).fetchall()
        return {str(row["field"]): int(row["count"]) for row in rows}

    @staticmethod
    def _row(row: sqlite3.Row) -> dict[str, object]:
        result: dict[str, object] = {
            "id": row["id"],
            "station_id": row["station_id"],
            "received_at": row["received_at"],
            "protocol": row["protocol"],
            "data": json.loads(row["normalised_json"]),
        }
        for column, target in (
            ("raw_json", "raw"), ("external_json", "external"),
            ("best_estimate_json", "best_estimate"), ("crosscheck_json", "crosscheck"),
            ("quality_json", "quality"), ("calibration_json", "calibration"),
        ):
            if column in row.keys() and row[column]:
                result[target] = json.loads(row[column])
        return result

    def recent(self, limit: int = 100) -> list[dict[str, object]]:
        with closing(self._connect()) as conn, conn:
            rows = conn.execute("SELECT * FROM observations ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [self._row(row) for row in rows]

    def latest_for_station(self, station_id: str) -> dict[str, object] | None:
        with closing(self._connect()) as conn, conn:
            row = conn.execute("SELECT * FROM observations WHERE station_id = ? ORDER BY id DESC LIMIT 1", (station_id,)).fetchone()
        return self._row(row) if row else None

    def latest(self) -> list[dict[str, object]]:
        with closing(self._connect()) as conn, conn:
            rows = conn.execute(
                """
                SELECT o.* FROM observations o
                JOIN (
                    SELECT station_id, MAX(id) AS max_id
                    FROM observations GROUP BY station_id
                ) latest ON latest.max_id = o.id
                ORDER BY o.station_id
                """
            ).fetchall()
        return [self._row(row) for row in rows]

    def count(self) -> int:
        with closing(self._connect()) as conn, conn:
            row = conn.execute("SELECT COUNT(*) AS count FROM observations").fetchone()
        return int(row["count"])

    def iter_recent(self, limit: int = 1000) -> Iterable[dict[str, object]]:
        yield from reversed(self.recent(limit))
