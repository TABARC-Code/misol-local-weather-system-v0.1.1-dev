"""Weather observation quality checks.

EXPERIMENTAL clean-room implementation. The checks deliberately produce flags
rather than pretending that an automated rule knows more than the weather.

Author: TABARC-Code
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import fabs


@dataclass(frozen=True, slots=True)
class Rule:
    minimum: float | None = None
    maximum: float | None = None
    max_change_per_hour: float | None = None


RULES: dict[str, Rule] = {
    "temperature_out_c": Rule(-60.0, 60.0, 15.0),
    "humidity_out_pct": Rule(0.0, 100.0, 55.0),
    "pressure_relative_hpa": Rule(850.0, 1100.0, 15.0),
    "pressure_absolute_hpa": Rule(500.0, 1100.0, 15.0),
    "wind_speed_ms": Rule(0.0, 80.0, 65.0),
    "wind_gust_ms": Rule(0.0, 100.0, 80.0),
    "wind_direction_deg": Rule(0.0, 360.0, None),
    "rain_rate_mm_h": Rule(0.0, 500.0, None),
    "rain_hour_mm": Rule(0.0, 300.0, None),
    "rain_day_mm": Rule(0.0, 1000.0, None),
    "solar_radiation_wm2": Rule(0.0, 1600.0, None),
    "uv_index": Rule(0.0, 20.0, None),
}


@dataclass(slots=True)
class QualityResult:
    descriptor: str
    flags: dict[str, list[str]]
    summary: dict[str, int]

    def as_dict(self) -> dict[str, object]:
        return {
            "descriptor": self.descriptor,
            "flags": self.flags,
            "summary": self.summary,
        }


def _numeric(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _parse_time(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def assess(
    current: dict[str, object],
    *,
    received_at: str,
    previous: dict[str, object] | None = None,
    previous_received_at: str | None = None,
    temporal_window_seconds: int = 3600,
) -> QualityResult:
    """Flag validity, temporal and simple internal-consistency problems."""

    flags: dict[str, list[str]] = {}

    for field, rule in RULES.items():
        value = _numeric(current.get(field))
        if value is None:
            continue
        field_flags: list[str] = []
        if rule.minimum is not None and value < rule.minimum:
            field_flags.append("below_plausible_range")
        if rule.maximum is not None and value > rule.maximum:
            field_flags.append("above_plausible_range")
        if field_flags:
            flags[field] = field_flags

    if previous and previous_received_at:
        now = _parse_time(received_at)
        before = _parse_time(previous_received_at)
        if now and before:
            seconds = (now - before).total_seconds()
            if 0 < seconds <= temporal_window_seconds:
                hours = max(seconds / 3600.0, 1.0 / 60.0)
                for field, rule in RULES.items():
                    if rule.max_change_per_hour is None:
                        continue
                    current_value = _numeric(current.get(field))
                    previous_value = _numeric(previous.get(field))
                    if current_value is None or previous_value is None:
                        continue
                    rate = fabs(current_value - previous_value) / hours
                    if rate > rule.max_change_per_hour:
                        flags.setdefault(field, []).append("rapid_change")

    wind = _numeric(current.get("wind_speed_ms"))
    gust = _numeric(current.get("wind_gust_ms"))
    if wind is not None and gust is not None and gust + 0.5 < wind:
        flags.setdefault("wind_gust_ms", []).append("gust_below_sustained_wind")

    rejected = sum(
        1
        for items in flags.values()
        if "below_plausible_range" in items or "above_plausible_range" in items
    )
    questioned = sum(1 for items in flags.values() if items)
    descriptor = "pass"
    if rejected:
        descriptor = "rejected"
    elif questioned:
        descriptor = "questioned"

    return QualityResult(
        descriptor=descriptor,
        flags=flags,
        summary={"flagged_fields": questioned, "rejected_fields": rejected},
    )
