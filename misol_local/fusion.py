"""Conservative weather cross-checking and fusion.

EXPERIMENTAL. The point is to make dubious readings visible, not to manufacture
precision by averaging numbers simply because several computers supplied them.

Author: TABARC-Code
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import fabs
from typing import Iterable

from .external import ExternalReading


TOLERANCES: dict[str, float] = {
    "temperature_out_c": 2.5,
    "humidity_out_pct": 15.0,
    "pressure_relative_hpa": 6.0,
    "wind_speed_ms": 4.0,
    "wind_gust_ms": 6.0,
    "wind_direction_deg": 50.0,
    "rain_hour_mm": 5.0,
    "solar_radiation_wm2": 180.0,
}


@dataclass(slots=True)
class FusionResult:
    best_estimate: dict[str, object]
    crosscheck: dict[str, object]
    external: dict[str, object]


def _age_seconds(timestamp: str, now: datetime) -> float | None:
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return max(0.0, (now - parsed.astimezone(timezone.utc)).total_seconds())
    except (TypeError, ValueError):
        return None


def _numeric(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _angular_difference(a: float, b: float) -> float:
    diff = fabs(a - b) % 360.0
    return min(diff, 360.0 - diff)


def _difference(field: str, a: float, b: float) -> float:
    if field == "wind_direction_deg":
        return _angular_difference(a, b)
    return fabs(a - b)


def _fresh(readings: Iterable[ExternalReading], max_age_seconds: int) -> list[ExternalReading]:
    now = datetime.now(timezone.utc)
    fresh: list[ExternalReading] = []
    for reading in readings:
        age = _age_seconds(reading.observed_at, now)
        if age is None or age <= max_age_seconds:
            fresh.append(reading)
    return fresh


def fuse(
    local: dict[str, object],
    readings: Iterable[ExternalReading],
    *,
    mode: str = "fill_gaps",
    max_age_seconds: int = 1800,
) -> FusionResult:
    """Build a separate best-estimate view while preserving local data unchanged."""

    mode = mode.strip().lower()
    if mode not in {"compare_only", "fill_gaps", "guarded"}:
        mode = "fill_gaps"

    usable = _fresh(readings, max_age_seconds)
    best = dict(local)
    checks: dict[str, object] = {}
    external_payload = {r.provider: r.as_dict() for r in usable}

    fields = set(local)
    for reading in usable:
        fields.update(reading.data)

    for field in sorted(fields):
        local_value = _numeric(local.get(field))
        provider_values: list[tuple[str, float]] = []
        for reading in usable:
            value = _numeric(reading.data.get(field))
            if value is not None:
                provider_values.append((reading.provider, value))

        if not provider_values:
            continue

        field_check: dict[str, object] = {
            "local": local_value,
            "providers": {name: value for name, value in provider_values},
            "status": "reference_only" if local_value is None else "ok",
            "selected_source": "local" if local_value is not None else None,
        }

        tolerance = TOLERANCES.get(field)
        if tolerance is not None:
            field_check["tolerance"] = tolerance

        if local_value is None:
            if mode != "compare_only":
                source, value = provider_values[0]
                best[field] = value
                field_check["status"] = "filled"
                field_check["selected_source"] = source
            checks[field] = field_check
            continue

        if tolerance is None:
            checks[field] = field_check
            continue

        differences = {
            name: round(_difference(field, local_value, value), 3)
            for name, value in provider_values
        }
        field_check["difference"] = differences
        outliers = [name for name, diff in differences.items() if diff > tolerance]
        if outliers:
            field_check["status"] = "local_external_disagreement"

        if mode == "guarded" and len(provider_values) >= 2:
            agreeing_pair: tuple[tuple[str, float], tuple[str, float]] | None = None
            for idx, left in enumerate(provider_values):
                for right in provider_values[idx + 1 :]:
                    if _difference(field, left[1], right[1]) <= tolerance / 2:
                        if (
                            _difference(field, local_value, left[1]) > tolerance
                            and _difference(field, local_value, right[1]) > tolerance
                        ):
                            agreeing_pair = (left, right)
                            break
                if agreeing_pair:
                    break

            if agreeing_pair:
                selected = (agreeing_pair[0][1] + agreeing_pair[1][1]) / 2.0
                best[field] = round(selected, 3)
                field_check["status"] = "corrected_by_external_consensus"
                field_check["selected_source"] = "+".join(
                    (agreeing_pair[0][0], agreeing_pair[1][0])
                )

        checks[field] = field_check

    return FusionResult(best_estimate=best, crosscheck=checks, external=external_payload)
