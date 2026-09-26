"""Configuration loading for MISOL Local.

EXPERIMENTAL. The INI format is intentionally ordinary. A weather logger does
not become better because its configuration requires a templating language.
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


@dataclass(slots=True)
class PrivacyConfig:
    store_raw: bool = True
    redact_keys: set[str] = field(
        default_factory=lambda: {
            "passkey",
            "password",
            "stationkey",
            "station_key",
            "key",
            "token",
            "secret",
        }
    )


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


def _get_bool(parser: ConfigParser, section: str, option: str, fallback: bool) -> bool:
    return parser.getboolean(section, option, fallback=fallback)


def load_config(path: str | Path | None = None) -> AppConfig:
    cfg = AppConfig()
    if path is None:
        path = Path("config.ini")
    else:
        path = Path(path)

    if not path.exists():
        return cfg

    parser = ConfigParser()
    parser.read(path, encoding="utf-8")

    cfg.server.host = parser.get("server", "host", fallback=cfg.server.host)
    cfg.server.port = parser.getint("server", "port", fallback=cfg.server.port)
    cfg.server.database = Path(parser.get("server", "database", fallback=str(cfg.server.database)))
    cfg.server.max_recent = parser.getint("server", "max_recent", fallback=cfg.server.max_recent)

    cfg.privacy.store_raw = _get_bool(parser, "privacy", "store_raw", cfg.privacy.store_raw)
    raw_redact = parser.get("privacy", "redact_keys", fallback=",").split(",")
    extra = {item.strip().lower() for item in raw_redact if item.strip()}
    if extra:
        cfg.privacy.redact_keys = extra

    cfg.mqtt.enabled = _get_bool(parser, "mqtt", "enabled", cfg.mqtt.enabled)
    cfg.mqtt.host = parser.get("mqtt", "host", fallback=cfg.mqtt.host)
    cfg.mqtt.port = parser.getint("mqtt", "port", fallback=cfg.mqtt.port)
    cfg.mqtt.topic_prefix = parser.get("mqtt", "topic_prefix", fallback=cfg.mqtt.topic_prefix).strip("/")
    cfg.mqtt.username = parser.get("mqtt", "username", fallback=cfg.mqtt.username)
    cfg.mqtt.password = parser.get("mqtt", "password", fallback=cfg.mqtt.password)
    cfg.mqtt.retain = _get_bool(parser, "mqtt", "retain", cfg.mqtt.retain)

    return cfg
