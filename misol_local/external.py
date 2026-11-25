"""External comparison sources for MISOL Local.

EXPERIMENTAL side-project code.

The local station remains the primary instrument. External services are useful
for cross-checking, gap filling and spotting a sensor that has quietly gone
peculiar. They are not permitted to rewrite the raw station observation.

Author: TABARC-Code
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import logging
from threading import Lock, Thread
import time
from typing import Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .config import CrossCheckConfig, OpenMeteoConfig, OpenWeatherConfig, SatelliteConfig

LOG = logging.getLogger(__name__)


@dataclass(slots=True)
class ExternalReading:
    provider: str
    observed_at: str
    fetched_at: str
    data: dict[str, float | int | str] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "observed_at": self.observed_at,
            "fetched_at": self.fetched_at,
            "data": self.data,
            "metadata": self.metadata,
        }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _timestamp_to_iso(value: object) -> str:
    try:
        return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat(timespec="seconds")
    except (TypeError, ValueError, OSError):
        return _utc_now()


def _get_json(url: str, timeout: float) -> dict[str, object]:
    request = Request(
        url,
        headers={
            "User-Agent": "MISOL-Local/0.3 experimental TABARC-Code",
            "Accept": "application/json",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("weather provider returned a non-object JSON document")
    return payload


def fetch_openweather(
    config: OpenWeatherConfig,
    crosscheck: CrossCheckConfig,
    *,
    getter: Callable[[str, float], dict[str, object]] = _get_json,
) -> ExternalReading:
    if not config.api_key:
        raise ValueError("OpenWeather is enabled but api_key is empty")

    query = urlencode(
        {
            "lat": crosscheck.latitude,
            "lon": crosscheck.longitude,
            "appid": config.api_key,
            "units": "metric",
        }
    )
    payload = getter(f"{config.endpoint}?{query}", crosscheck.timeout_seconds)

    main = payload.get("main") if isinstance(payload.get("main"), dict) else {}
    wind = payload.get("wind") if isinstance(payload.get("wind"), dict) else {}
    rain = payload.get("rain") if isinstance(payload.get("rain"), dict) else {}
    clouds = payload.get("clouds") if isinstance(payload.get("clouds"), dict) else {}

    data: dict[str, float | int | str] = {}

    def number(container: dict, key: str, target: str) -> None:
        value = container.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            data[target] = float(value)

    number(main, "temp", "temperature_out_c")
    number(main, "humidity", "humidity_out_pct")
    number(main, "pressure", "pressure_relative_hpa")
    number(wind, "speed", "wind_speed_ms")
    number(wind, "gust", "wind_gust_ms")
    number(wind, "deg", "wind_direction_deg")
    number(rain, "1h", "rain_hour_mm")

    metadata: dict[str, object] = {"source_kind": "regional_blended_current"}
    if isinstance(clouds.get("all"), (int, float)):
        metadata["cloud_cover_pct"] = float(clouds["all"])
    if isinstance(payload.get("name"), str):
        metadata["location_name"] = payload["name"]
    if isinstance(payload.get("id"), (int, float)):
        metadata["provider_location_id"] = int(payload["id"])

    return ExternalReading(
        provider="openweather",
        observed_at=_timestamp_to_iso(payload.get("dt")),
        fetched_at=_utc_now(),
        data=data,
        metadata=metadata,
    )


def fetch_openmeteo(
    config: OpenMeteoConfig,
    crosscheck: CrossCheckConfig,
    *,
    getter: Callable[[str, float], dict[str, object]] = _get_json,
) -> ExternalReading:
    variables = ",".join(
        (
            "temperature_2m",
            "relative_humidity_2m",
            "pressure_msl",
            "wind_speed_10m",
            "wind_direction_10m",
            "wind_gusts_10m",
            "shortwave_radiation",
        )
    )
    query = urlencode(
        {
            "latitude": crosscheck.latitude,
            "longitude": crosscheck.longitude,
            "current": variables,
            "wind_speed_unit": "ms",
            "timezone": "UTC",
            "forecast_days": 1,
        }
    )
    payload = getter(f"{config.endpoint}?{query}", crosscheck.timeout_seconds)
    current = payload.get("current") if isinstance(payload.get("current"), dict) else {}

    mapping = {
        "temperature_2m": "temperature_out_c",
        "relative_humidity_2m": "humidity_out_pct",
        "pressure_msl": "pressure_relative_hpa",
        "wind_speed_10m": "wind_speed_ms",
        "wind_direction_10m": "wind_direction_deg",
        "wind_gusts_10m": "wind_gust_ms",
        "shortwave_radiation": "solar_radiation_wm2",
    }
    data: dict[str, float | int | str] = {}
    for source, target in mapping.items():
        value = current.get(source)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            data[target] = float(value)

    metadata: dict[str, object] = {"source_kind": "weather_model_current"}
    for key in ("latitude", "longitude", "elevation", "generationtime_ms"):
        if key in payload:
            metadata[key] = payload[key]
    if isinstance(current.get("interval"), (int, float)):
        metadata["interval_seconds"] = current["interval"]

    return ExternalReading(
        provider="openmeteo",
        observed_at=str(current.get("time") or _utc_now()),
        fetched_at=_utc_now(),
        data=data,
        metadata=metadata,
    )


def fetch_satellite_radiation(
    config: SatelliteConfig,
    crosscheck: CrossCheckConfig,
    *,
    getter: Callable[[str, float], dict[str, object]] = _get_json,
) -> ExternalReading:
    query = urlencode(
        {
            "latitude": crosscheck.latitude,
            "longitude": crosscheck.longitude,
            "hourly": "shortwave_radiation_instant",
            "past_hours": 2,
            "forecast_hours": 0,
            "timezone": "UTC",
            "temporal_resolution": "native",
            "models": "satellite_radiation_seamless",
        }
    )
    payload = getter(f"{config.endpoint}?{query}", crosscheck.timeout_seconds)

    hourly = payload.get("hourly") if isinstance(payload.get("hourly"), dict) else {}
    times = hourly.get("time") if isinstance(hourly.get("time"), list) else []
    values = (
        hourly.get("shortwave_radiation_instant")
        if isinstance(hourly.get("shortwave_radiation_instant"), list)
        else []
    )

    observed_at = _utc_now()
    radiation: float | None = None
    for stamp, value in reversed(list(zip(times, values))):
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            radiation = float(value)
            observed_at = str(stamp)
            break

    data: dict[str, float | int | str] = {}
    if radiation is not None:
        data["solar_radiation_wm2"] = radiation

    metadata: dict[str, object] = {"source_kind": "satellite_observation"}
    for key in ("latitude", "longitude", "elevation", "generationtime_ms"):
        if key in payload:
            metadata[key] = payload[key]

    return ExternalReading(
        provider="openmeteo_satellite",
        observed_at=observed_at,
        fetched_at=_utc_now(),
        data=data,
        metadata=metadata,
    )


class ExternalManager:
    def __init__(
        self,
        crosscheck: CrossCheckConfig,
        openweather: OpenWeatherConfig,
        openmeteo: OpenMeteoConfig,
        satellite: SatelliteConfig,
    ) -> None:
        self.crosscheck = crosscheck
        self.openweather = openweather
        self.openmeteo = openmeteo
        self.satellite = satellite
        self._lock = Lock()
        self._readings: dict[str, ExternalReading] = {}
        self._errors: dict[str, str] = {}
        self._health: dict[str, dict[str, object]] = {}
        self._last_attempt_monotonic = 0.0
        self._refreshing = False

    def kick(self) -> None:
        if not self.crosscheck.enabled:
            return
        now = time.monotonic()
        with self._lock:
            if self._refreshing:
                return
            if now - self._last_attempt_monotonic < self.crosscheck.interval_seconds:
                return
            self._refreshing = True
            self._last_attempt_monotonic = now
        Thread(target=self._refresh, name="misol-external-weather", daemon=True).start()

    def _fetch_one(self, name: str, function: Callable[[], ExternalReading]) -> tuple[ExternalReading | None, str | None]:
        started = time.monotonic()
        try:
            reading = function()
        except Exception as exc:
            elapsed = round((time.monotonic() - started) * 1000.0, 1)
            with self._lock:
                previous = self._health.get(name, {})
                self._health[name] = {
                    "ok": False,
                    "last_attempt": _utc_now(),
                    "last_success": previous.get("last_success"),
                    "latency_ms": elapsed,
                    "consecutive_failures": int(previous.get("consecutive_failures", 0)) + 1,
                }
            return None, f"{type(exc).__name__}: {exc}"

        elapsed = round((time.monotonic() - started) * 1000.0, 1)
        with self._lock:
            self._health[name] = {
                "ok": True,
                "last_attempt": _utc_now(),
                "last_success": reading.fetched_at,
                "latency_ms": elapsed,
                "consecutive_failures": 0,
            }
        return reading, None

    def _refresh(self) -> None:
        updates: dict[str, ExternalReading] = {}
        errors: dict[str, str] = {}
        try:
            providers: list[tuple[str, Callable[[], ExternalReading]]] = []
            if self.openweather.enabled:
                providers.append(("openweather", lambda: fetch_openweather(self.openweather, self.crosscheck)))
            if self.openmeteo.enabled:
                providers.append(("openmeteo", lambda: fetch_openmeteo(self.openmeteo, self.crosscheck)))
            if self.satellite.enabled:
                providers.append(("openmeteo_satellite", lambda: fetch_satellite_radiation(self.satellite, self.crosscheck)))

            for name, function in providers:
                reading, error = self._fetch_one(name, function)
                if reading is not None:
                    updates[name] = reading
                if error:
                    errors[name] = error
                    LOG.warning("%s cross-check failed: %s", name, error)

            with self._lock:
                self._readings.update(updates)
                self._errors = errors
        finally:
            with self._lock:
                self._refreshing = False

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            return {
                "enabled": self.crosscheck.enabled,
                "refreshing": self._refreshing,
                "readings": {name: reading.as_dict() for name, reading in self._readings.items()},
                "errors": dict(self._errors),
                "health": dict(self._health),
            }

    def readings(self) -> dict[str, ExternalReading]:
        with self._lock:
            return dict(self._readings)
