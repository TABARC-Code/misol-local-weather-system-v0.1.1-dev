"""Protocol parsing and normalisation.

EXPERIMENTAL clean-room implementation.

The Wi-Fi consoles in this family speak pleasantly unglamorous HTTP. Ecowitt
mode generally uses form fields in imperial units. Wunderground mode is close
enough that a shared tolerant parser is more useful than two brittle ones.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import math
from typing import Mapping

INHG_TO_HPA = 33.8638866667
IN_TO_MM = 25.4
MPH_TO_MS = 0.44704


@dataclass(slots=True)
class ParsedObservation:
    station_id: str
    received_at: str
    protocol: str
    normalised: dict[str, object]
    raw_redacted: dict[str, str]


def _float(data: Mapping[str, str], key: str) -> float | None:
    value = data.get(key)
    if value is None or value == "":
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _f_to_c(value: float) -> float:
    return (value - 32.0) * 5.0 / 9.0


def _put(out: dict[str, object], key: str, value: object | None, digits: int = 3) -> None:
    if value is None:
        return
    if isinstance(value, float):
        out[key] = round(value, digits)
    else:
        out[key] = value


def station_fingerprint(data: Mapping[str, str], client_ip: str = "unknown") -> str:
    """Return a stable local ID without persisting the station PASSKEY."""

    passkey = data.get("PASSKEY") or data.get("passkey")
    if passkey:
        digest = hashlib.sha256(passkey.encode("utf-8", "replace")).hexdigest()[:12]
        return f"station-{digest}"

    explicit = (
        data.get("stationid")
        or data.get("ID")
        or data.get("station_id")
        or data.get("mac")
        or data.get("MAC")
    )
    if explicit:
        safe = "".join(ch for ch in explicit if ch.isalnum() or ch in "-_:")[:48]
        return safe or "station-unknown"

    digest = hashlib.sha256(client_ip.encode("utf-8", "replace")).hexdigest()[:12]
    return f"client-{digest}"


def redact(data: Mapping[str, str], redact_keys: set[str]) -> dict[str, str]:
    cleaned: dict[str, str] = {}
    for key, value in data.items():
        if key.lower() in redact_keys:
            cleaned[key] = "<redacted>"
        else:
            cleaned[key] = str(value)
    return cleaned


def detect_protocol(path: str, data: Mapping[str, str]) -> str:
    lowered = path.lower()
    if "updateweatherstation" in lowered:
        return "wunderground"
    if "passkey" in {k.lower() for k in data}:
        return "ecowitt"
    return "unknown-form"


def normalise(data: Mapping[str, str]) -> dict[str, object]:
    """Translate common Fine Offset/Ecowitt/WU fields to a compact metric model.

    Unknown fields are not interpreted here; they remain available in the raw
    payload. That is deliberate. Guessing units is worse than leaving a field
    alone until a real packet tells us what it is.
    """

    out: dict[str, object] = {}

    # Identity / timing metadata.
    for source, target in (
        ("stationtype", "station_type"),
        ("model", "model"),
        ("runtime", "runtime"),
        ("freq", "frequency"),
    ):
        if data.get(source):
            out[target] = data[source]

    if data.get("dateutc"):
        out["station_time"] = data["dateutc"]

    # Temperatures arrive as Fahrenheit in the common custom-upload formats.
    for source, target in (
        ("tempf", "temperature_out_c"),
        ("tempinf", "temperature_in_c"),
        ("dewptf", "dew_point_c"),
        ("windchillf", "wind_chill_c"),
    ):
        value = _float(data, source)
        _put(out, target, None if value is None else _f_to_c(value))

    _put(out, "humidity_out_pct", _float(data, "humidity"), 1)
    _put(out, "humidity_in_pct", _float(data, "humidityin"), 1)

    for source, target in (
        ("baromrelin", "pressure_relative_hpa"),
        ("baromabsin", "pressure_absolute_hpa"),
    ):
        value = _float(data, source)
        _put(out, target, None if value is None else value * INHG_TO_HPA)

    _put(out, "wind_direction_deg", _float(data, "winddir"), 1)
    for source, target in (
        ("windspeedmph", "wind_speed_ms"),
        ("windgustmph", "wind_gust_ms"),
    ):
        value = _float(data, source)
        _put(out, target, None if value is None else value * MPH_TO_MS)

    rain_fields = (
        ("rainratein", "rain_rate_mm_h"),
        ("eventrainin", "rain_event_mm"),
        ("hourlyrainin", "rain_hour_mm"),
        ("dailyrainin", "rain_day_mm"),
        ("weeklyrainin", "rain_week_mm"),
        ("monthlyrainin", "rain_month_mm"),
        ("yearlyrainin", "rain_year_mm"),
        ("totalrainin", "rain_total_mm"),
    )
    for source, target in rain_fields:
        value = _float(data, source)
        _put(out, target, None if value is None else value * IN_TO_MM)

    _put(out, "solar_radiation_wm2", _float(data, "solarradiation"), 2)
    _put(out, "uv_index", _float(data, "uv"), 2)

    # Battery keys vary wildly. Keep a small set useful for the target family
    # while leaving everything else in raw data for later evidence-led parsing.
    for key, value in data.items():
        low = key.lower()
        if low.endswith("batt") or low.endswith("batt1") or "battery" in low:
            try:
                out[f"battery_raw.{low}"] = float(value)
            except (TypeError, ValueError):
                out[f"battery_raw.{low}"] = str(value)

    return out


def parse_observation(
    data: Mapping[str, str],
    *,
    path: str,
    client_ip: str,
    redact_keys: set[str],
) -> ParsedObservation:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return ParsedObservation(
        station_id=station_fingerprint(data, client_ip),
        received_at=now,
        protocol=detect_protocol(path, data),
        normalised=normalise(data),
        raw_redacted=redact(data, redact_keys),
    )
