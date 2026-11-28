"""Explainable station and sensor health analysis.

EXPERIMENTAL. This module reports evidence. It does not rewrite observations or
pretend a regional model is a calibration laboratory.

Author: TABARC-Code
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from statistics import median
from typing import Iterable


SENSORS: dict[str, tuple[str, ...]] = {
    "thermometer": ("temperature_out_c",),
    "hygrometer": ("humidity_out_pct",),
    "barometer": ("pressure_relative_hpa", "pressure_absolute_hpa"),
    "anemometer": ("wind_speed_ms", "wind_gust_ms", "wind_direction_deg"),
    "rain_gauge": ("rain_rate_mm_h", "rain_hour_mm", "rain_day_mm"),
    "solar_uv": ("solar_radiation_wm2", "uv_index"),
}

FLAT_EPSILON = {
    "temperature_out_c": 0.05,
    "humidity_out_pct": 0.2,
    "pressure_relative_hpa": 0.05,
    "pressure_absolute_hpa": 0.05,
    "wind_speed_ms": 0.05,
    "wind_gust_ms": 0.05,
    "wind_direction_deg": 0.5,
    "solar_radiation_wm2": 1.0,
    "uv_index": 0.05,
}


@dataclass(slots=True)
class SensorHealth:
    sensor: str
    score: int = 100
    state: str = "healthy"
    verdict: str = "normal"
    evidence: list[str] = field(default_factory=list)
    maintenance: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "sensor": self.sensor,
            "score": max(0, min(100, self.score)),
            "state": self.state,
            "verdict": self.verdict,
            "evidence": self.evidence,
            "maintenance": self.maintenance,
        }


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if isfinite(value) else None


def _values(rows: list[dict[str, object]], field: str) -> list[float]:
    result = []
    for row in rows:
        data = row.get("data")
        if isinstance(data, dict):
            value = _number(data.get(field))
            if value is not None:
                result.append(value)
    return result


def _quality_flags(rows: list[dict[str, object]], fields: Iterable[str]) -> list[str]:
    wanted = set(fields)
    found: list[str] = []
    for row in rows[-12:]:
        quality = row.get("quality")
        flags = quality.get("flags") if isinstance(quality, dict) else None
        if not isinstance(flags, dict):
            continue
        for name, items in flags.items():
            if name in wanted and isinstance(items, list):
                found.extend(str(item) for item in items)
    return found


def _reference_disagreements(rows: list[dict[str, object]], fields: Iterable[str]) -> tuple[int, int]:
    wanted = set(fields)
    disagreements = 0
    corroborated_rapid = 0
    for row in rows[-12:]:
        cross = row.get("crosscheck")
        quality = row.get("quality")
        qflags = quality.get("flags") if isinstance(quality, dict) else {}
        if not isinstance(cross, dict):
            continue
        for field in wanted:
            item = cross.get(field)
            if not isinstance(item, dict):
                continue
            if item.get("status") == "local_external_disagreement":
                disagreements += 1
            flags = qflags.get(field, []) if isinstance(qflags, dict) else []
            providers = item.get("providers")
            if "rapid_change" in flags and isinstance(providers, dict) and providers:
                if item.get("status") == "ok":
                    corroborated_rapid += 1
    return disagreements, corroborated_rapid


def _flatline(rows: list[dict[str, object]], sensor: str, fields: tuple[str, ...]) -> bool:
    # Rain sitting at zero is weather, not a broken rain gauge. A flat wind trace
    # can also be real, so it needs external disagreement before it becomes useful.
    if sensor == "rain_gauge":
        return False
    for field in fields:
        values = _values(rows[-20:], field)
        if len(values) < 12:
            continue
        epsilon = FLAT_EPSILON.get(field)
        if epsilon is not None and max(values) - min(values) <= epsilon:
            return True
    return False


def _storm_signature(rows: list[dict[str, object]]) -> bool:
    if len(rows) < 4:
        return False
    latest = rows[-1].get("data")
    first = rows[max(0, len(rows) - 12)].get("data")
    if not isinstance(latest, dict) or not isinstance(first, dict):
        return False
    rain = _number(latest.get("rain_rate_mm_h")) or _number(latest.get("rain_hour_mm")) or 0.0
    gust = _number(latest.get("wind_gust_ms")) or 0.0
    p0 = _number(first.get("pressure_relative_hpa"))
    p1 = _number(latest.get("pressure_relative_hpa"))
    pressure_drop = (p0 - p1) if p0 is not None and p1 is not None else 0.0
    return rain > 0.0 and gust >= 8.0 and pressure_drop >= 0.8


def analyse_station(
    station_id: str,
    rows: list[dict[str, object]],
    *,
    calibration_profiles: dict[str, object] | None = None,
) -> dict[str, object]:
    """Return an explainable health report from recent immutable observations."""

    rows = list(reversed(rows)) if len(rows) > 1 and int(rows[0].get("id", 0)) > int(rows[-1].get("id", 0)) else rows
    if not rows:
        return {
            "station_id": station_id,
            "overall_score": 0,
            "state": "no_data",
            "classification": "unknown",
            "sensors": {},
            "evidence": ["No observations are available."],
        }

    profiles = calibration_profiles or {}
    sensors: dict[str, SensorHealth] = {}
    event_votes = 0
    fault_votes = 0

    for sensor, fields in SENSORS.items():
        health = SensorHealth(sensor=sensor)
        present = sum(1 for row in rows[-20:] if isinstance(row.get("data"), dict)
                      and any(_number(row["data"].get(field)) is not None for field in fields))
        expected = min(20, len(rows))
        if expected and present / expected < 0.8:
            health.score -= 25
            health.evidence.append(f"Data present in only {present} of the last {expected} observations.")
            health.maintenance.append("Check sensor power, radio link and console field mapping.")
            fault_votes += 1

        flags = _quality_flags(rows, fields)
        impossible = sum(flag in {"below_plausible_range", "above_plausible_range"} for flag in flags)
        if impossible:
            health.score -= 40
            health.evidence.append("One or more readings crossed broad physical plausibility limits.")
            fault_votes += 2

        disagreements, corroborated_rapid = _reference_disagreements(rows, fields)
        flat = _flatline(rows, sensor, fields)
        if flat and disagreements:
            health.score -= 30
            health.evidence.append("The sensor trace is nearly flat while external references disagree.")
            health.maintenance.append("Inspect the sensor for obstruction, seizure, contamination or a stale data path.")
            fault_votes += 2
        elif flat:
            health.score -= 8
            health.evidence.append("The recent trace is unusually flat. No external contradiction is available.")
        if disagreements >= 3:
            health.score -= 20
            health.evidence.append(f"Repeated disagreement with external references occurred {disagreements} times recently.")
            fault_votes += 1
        elif disagreements:
            health.score -= 6
            health.evidence.append("A recent local/reference disagreement needs more evidence before calling it a fault.")

        if corroborated_rapid:
            health.evidence.append("A rapid local change was also supported by external data.")
            event_votes += 1

        for field in fields:
            profile = profiles.get(field)
            drift = getattr(profile, "drift", None)
            stable = getattr(profile, "stable", False)
            if isinstance(drift, (int, float)) and isfinite(float(drift)) and abs(float(drift)) > 0:
                health.evidence.append(f"Historical drift indicator for {field}: {float(drift):+.2f}.")
                if not stable:
                    health.score -= 15
                    health.maintenance.append("Compare against a trusted physical reference before applying any correction.")
                    fault_votes += 1
                break

        if sensor == "rain_gauge":
            recent_rain = _values(rows[-20:], "rain_hour_mm")
            if recent_rain and max(recent_rain) == 0 and disagreements:
                health.score -= 18
                health.evidence.append("Local rainfall remains zero while a reference reports rain.")
                health.maintenance.append("Inspect the funnel, tipping mechanism, level and debris path.")
                fault_votes += 1

        if sensor == "anemometer" and flat and disagreements:
            health.maintenance.append("Check cups/vane movement and bearings before changing software thresholds.")

        if sensor == "hygrometer" and any("Historical drift" in item for item in health.evidence):
            health.maintenance.append("Humidity elements can age. Treat persistent drift as a maintenance clue, not an automatic correction.")

        if health.score < 50:
            health.state = "maintenance_required"
            health.verdict = "probable_sensor_problem"
        elif health.score < 75:
            health.state = "monitor"
            health.verdict = "suspect"
        elif health.score < 90:
            health.state = "watch"
            health.verdict = "minor_concern"
        sensors[sensor] = health

    if _storm_signature(rows):
        event_votes += 2

    scores = [item.score for item in sensors.values()]
    overall = round(median(scores)) if scores else 0
    classification = "normal"
    if event_votes > fault_votes and event_votes:
        classification = "probable_weather_event"
    elif fault_votes >= 3 and fault_votes > event_votes:
        classification = "probable_sensor_deterioration"
    elif event_votes or fault_votes:
        classification = "uncertain"

    state = "healthy"
    if overall < 50:
        state = "maintenance_required"
    elif overall < 75:
        state = "monitor"
    elif overall < 90:
        state = "watch"

    evidence = [
        f"Event evidence votes: {event_votes}.",
        f"Sensor-fault evidence votes: {fault_votes}.",
        "Health scores are diagnostic hints, not calibration certificates.",
    ]
    return {
        "station_id": station_id,
        "overall_score": overall,
        "state": state,
        "classification": classification,
        "sensors": {name: item.as_dict() for name, item in sensors.items()},
        "evidence": evidence,
    }
