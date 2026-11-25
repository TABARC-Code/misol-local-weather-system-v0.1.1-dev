"""Slow historical calibration support for MISOL Local.

EXPERIMENTAL. Calibration is evidence, not permission to rewrite history. Raw
observations remain untouched and every learned correction carries provenance.

Author: TABARC-Code
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median

from .fusion import TOLERANCES, _difference


ELIGIBLE_FIELDS = {
    "temperature_out_c",
    "humidity_out_pct",
    "pressure_relative_hpa",
    "wind_speed_ms",
    "wind_gust_ms",
    "solar_radiation_wm2",
}


@dataclass(slots=True)
class CalibrationSample:
    field: str
    local_value: float
    reference_value: float
    bias: float
    providers: list[str]


@dataclass(slots=True)
class CalibrationProfile:
    field: str
    samples: int
    median_bias: float
    mad: float
    stable: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "field": self.field,
            "samples": self.samples,
            "median_bias": round(self.median_bias, 4),
            "mad": round(self.mad, 4),
            "stable": self.stable,
        }


def consensus_samples(
    local: dict[str, object],
    crosscheck: dict[str, object],
) -> list[CalibrationSample]:
    """Create learning samples only when at least two external sources agree."""

    samples: list[CalibrationSample] = []
    for field in ELIGIBLE_FIELDS:
        local_value = local.get(field)
        check = crosscheck.get(field)
        if not isinstance(local_value, (int, float)) or isinstance(local_value, bool):
            continue
        if not isinstance(check, dict):
            continue
        providers = check.get("providers")
        if not isinstance(providers, dict) or len(providers) < 2:
            continue

        values = [
            (str(name), float(value))
            for name, value in providers.items()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        ]
        if len(values) < 2:
            continue

        tolerance = TOLERANCES.get(field)
        if tolerance is None:
            continue

        agreeing: list[tuple[str, float]] = []
        for name, value in values:
            if all(_difference(field, value, other) <= tolerance / 2.0 for _, other in values):
                agreeing.append((name, value))
        if len(agreeing) < 2:
            continue

        reference = median([value for _, value in agreeing])
        local_float = float(local_value)
        samples.append(
            CalibrationSample(
                field=field,
                local_value=local_float,
                reference_value=reference,
                bias=local_float - reference,
                providers=[name for name, _ in agreeing],
            )
        )
    return samples


def build_profile(
    field: str,
    biases: list[float],
    *,
    min_samples: int,
    max_mad_fraction: float,
) -> CalibrationProfile:
    if not biases:
        return CalibrationProfile(field, 0, 0.0, 0.0, False)
    centre = median(biases)
    deviations = [abs(value - centre) for value in biases]
    mad = median(deviations)
    tolerance = TOLERANCES.get(field, 1.0)
    stable = len(biases) >= min_samples and mad <= tolerance * max_mad_fraction
    return CalibrationProfile(field, len(biases), centre, mad, stable)


def apply_profiles(
    local: dict[str, object],
    best_estimate: dict[str, object],
    crosscheck: dict[str, object],
    profiles: dict[str, CalibrationProfile],
    *,
    apply: bool,
) -> tuple[dict[str, object], dict[str, object]]:
    calibrated = dict(best_estimate)
    metadata: dict[str, object] = {}

    for field, profile in profiles.items():
        local_value = local.get(field)
        if not isinstance(local_value, (int, float)) or isinstance(local_value, bool):
            continue
        check = crosscheck.get(field)
        selected_source = check.get("selected_source") if isinstance(check, dict) else "local"
        can_apply = profile.stable and selected_source in {None, "local"}
        corrected = float(local_value) - profile.median_bias
        metadata[field] = {
            **profile.as_dict(),
            "correction": round(-profile.median_bias, 4),
            "candidate_value": round(corrected, 4),
            "applied": bool(apply and can_apply),
        }
        if apply and can_apply:
            calibrated[field] = round(corrected, 4)

    return calibrated, metadata
