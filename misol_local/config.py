"""Configuration loading for MISOL Local.

EXPERIMENTAL. The INI format is intentionally ordinary. A weather logger does
not become better because its configuration requires a templating language.

Author: TABARC-Code
"""

from __future__ import annotations

from configparser import ConfigParser
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8080
    database: Path = Path("data/misol.sqlite3")
    max_recent: int = 1000
    max_body_bytes: int = 65536


@dataclass(slots=True)
class PrivacyConfig:
    store_raw: bool = True
    redact_keys: set[str] = field(
        default_factory=lambda: {
            "passkey", "password", "stationkey", "station_key", "key",
            "token", "secret", "api_key", "apikey",
        }
    )


@dataclass(slots=True)
class CrossCheckConfig:
    enabled: bool = False
    latitude: float = 0.0
    longitude: float = 0.0
    interval_seconds: int = 600
    timeout_seconds: float = 5.0
    max_age_seconds: int = 1800
    fusion_mode: str = "fill_gaps"


@dataclass(slots=True)
class OpenWeatherConfig:
    enabled: bool = False
    api_key: str = ""
    endpoint: str = "https://api.openweathermap.org/data/2.5/weather"


@dataclass(slots=True)
class OpenMeteoConfig:
    enabled: bool = False
    endpoint: str = "https://api.open-meteo.com/v1/forecast"


@dataclass(slots=True)
class SatelliteConfig:
    enabled: bool = False
    endpoint: str = "https://satellite-api.open-meteo.com/v1/archive"


@dataclass(slots=True)
class QualityConfig:
    enabled: bool = True
    temporal_window_seconds: int = 3600
    reject_impossible: bool = False


@dataclass(slots=True)
class CalibrationConfig:
    enabled: bool = True
    apply_to_best_estimate: bool = False
    min_days: int = 14
    min_samples: int = 24
    window_samples: int = 500
    max_mad_fraction: float = 0.25


@dataclass(slots=True)
class MQTTConfig:
    enabled: bool = False
    host: str = "127.0.0.1"
    port: int = 1883
    topic_prefix: str = "misol-local"
    username: str = ""
    password: str = ""
    retain: bool = False


@dataclass(slots=True)
class AppConfig:
    server: ServerConfig = field(default_factory=ServerConfig)
    privacy: PrivacyConfig = field(default_factory=PrivacyConfig)
    mqtt: MQTTConfig = field(default_factory=MQTTConfig)
    crosscheck: CrossCheckConfig = field(default_factory=CrossCheckConfig)
    openweather: OpenWeatherConfig = field(default_factory=OpenWeatherConfig)
    openmeteo: OpenMeteoConfig = field(default_factory=OpenMeteoConfig)
    satellite: SatelliteConfig = field(default_factory=SatelliteConfig)
    quality: QualityConfig = field(default_factory=QualityConfig)
    calibration: CalibrationConfig = field(default_factory=CalibrationConfig)


def _get_bool(parser: ConfigParser, section: str, option: str, fallback: bool) -> bool:
    return parser.getboolean(section, option, fallback=fallback)


def load_config(path: str | Path | None = None) -> AppConfig:
    cfg = AppConfig()
    path = Path("config.ini") if path is None else Path(path)
    if not path.exists():
        return cfg

    parser = ConfigParser()
    parser.read(path, encoding="utf-8")

    cfg.server.host = parser.get("server", "host", fallback=cfg.server.host)
    cfg.server.port = parser.getint("server", "port", fallback=cfg.server.port)
    cfg.server.database = Path(parser.get("server", "database", fallback=str(cfg.server.database)))
    cfg.server.max_recent = parser.getint("server", "max_recent", fallback=cfg.server.max_recent)
    cfg.server.max_body_bytes = parser.getint("server", "max_body_bytes", fallback=cfg.server.max_body_bytes)

    cfg.privacy.store_raw = _get_bool(parser, "privacy", "store_raw", cfg.privacy.store_raw)
    raw_redact = parser.get("privacy", "redact_keys", fallback=",").split(",")
    extra = {item.strip().lower() for item in raw_redact if item.strip()}
    if extra:
        cfg.privacy.redact_keys.update(extra)

    cfg.mqtt.enabled = _get_bool(parser, "mqtt", "enabled", cfg.mqtt.enabled)
    cfg.mqtt.host = parser.get("mqtt", "host", fallback=cfg.mqtt.host)
    cfg.mqtt.port = parser.getint("mqtt", "port", fallback=cfg.mqtt.port)
    cfg.mqtt.topic_prefix = parser.get("mqtt", "topic_prefix", fallback=cfg.mqtt.topic_prefix).strip("/")
    cfg.mqtt.username = parser.get("mqtt", "username", fallback=cfg.mqtt.username)
    cfg.mqtt.password = parser.get("mqtt", "password", fallback=cfg.mqtt.password)
    cfg.mqtt.retain = _get_bool(parser, "mqtt", "retain", cfg.mqtt.retain)

    cfg.crosscheck.enabled = _get_bool(parser, "crosscheck", "enabled", cfg.crosscheck.enabled)
    cfg.crosscheck.latitude = parser.getfloat("crosscheck", "latitude", fallback=cfg.crosscheck.latitude)
    cfg.crosscheck.longitude = parser.getfloat("crosscheck", "longitude", fallback=cfg.crosscheck.longitude)
    cfg.crosscheck.interval_seconds = parser.getint("crosscheck", "interval_seconds", fallback=cfg.crosscheck.interval_seconds)
    cfg.crosscheck.timeout_seconds = parser.getfloat("crosscheck", "timeout_seconds", fallback=cfg.crosscheck.timeout_seconds)
    cfg.crosscheck.max_age_seconds = parser.getint("crosscheck", "max_age_seconds", fallback=cfg.crosscheck.max_age_seconds)
    cfg.crosscheck.fusion_mode = parser.get("crosscheck", "fusion_mode", fallback=cfg.crosscheck.fusion_mode).strip().lower()

    cfg.openweather.enabled = _get_bool(parser, "openweather", "enabled", cfg.openweather.enabled)
    cfg.openweather.api_key = parser.get("openweather", "api_key", fallback=cfg.openweather.api_key).strip()
    cfg.openweather.endpoint = parser.get("openweather", "endpoint", fallback=cfg.openweather.endpoint).strip()

    cfg.openmeteo.enabled = _get_bool(parser, "openmeteo", "enabled", cfg.openmeteo.enabled)
    cfg.openmeteo.endpoint = parser.get("openmeteo", "endpoint", fallback=cfg.openmeteo.endpoint).strip()

    cfg.satellite.enabled = _get_bool(parser, "satellite", "enabled", cfg.satellite.enabled)
    cfg.satellite.endpoint = parser.get("satellite", "endpoint", fallback=cfg.satellite.endpoint).strip()

    cfg.quality.enabled = _get_bool(parser, "quality", "enabled", cfg.quality.enabled)
    cfg.quality.temporal_window_seconds = parser.getint("quality", "temporal_window_seconds", fallback=cfg.quality.temporal_window_seconds)
    cfg.quality.reject_impossible = _get_bool(parser, "quality", "reject_impossible", cfg.quality.reject_impossible)

    cfg.calibration.enabled = _get_bool(parser, "calibration", "enabled", cfg.calibration.enabled)
    cfg.calibration.apply_to_best_estimate = _get_bool(parser, "calibration", "apply_to_best_estimate", cfg.calibration.apply_to_best_estimate)
    cfg.calibration.min_days = max(14, parser.getint("calibration", "min_days", fallback=14))
    cfg.calibration.min_samples = parser.getint("calibration", "min_samples", fallback=cfg.calibration.min_samples)
    cfg.calibration.window_samples = parser.getint("calibration", "window_samples", fallback=cfg.calibration.window_samples)
    cfg.calibration.max_mad_fraction = parser.getfloat("calibration", "max_mad_fraction", fallback=cfg.calibration.max_mad_fraction)

    return cfg
