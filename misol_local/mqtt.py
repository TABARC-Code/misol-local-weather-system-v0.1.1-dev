"""Optional MQTT output.

EXPERIMENTAL. Importing this module does not make MQTT mandatory; if enabled
without paho-mqtt installed, startup fails with a useful message instead.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from .config import MQTTConfig
from .protocol import ParsedObservation

LOG = logging.getLogger(__name__)


class MQTTPublisher:
    def __init__(self, config: MQTTConfig) -> None:
        self.config = config
        self._client: Any = None
        if not config.enabled:
            return

        try:
            import paho.mqtt.client as mqtt
        except ImportError as exc:  # pragma: no cover - environment-specific
            raise RuntimeError(
                "MQTT is enabled but paho-mqtt is not installed. "
                "Run: pip install -r requirements-optional.txt"
            ) from exc

        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        if config.username:
            self._client.username_pw_set(config.username, config.password or None)
        self._client.connect(config.host, config.port, keepalive=30)
        self._client.loop_start()
        LOG.info("MQTT enabled: %s:%s", config.host, config.port)

    def publish(self, observation: ParsedObservation) -> None:
        if self._client is None:
            return
        topic = f"{self.config.topic_prefix}/{observation.station_id}/state"
        payload = {
            "station_id": observation.station_id,
            "received_at": observation.received_at,
            "protocol": observation.protocol,
            **observation.normalised,
        }
        info = self._client.publish(
            topic,
            json.dumps(payload, sort_keys=True),
            qos=0,
            retain=self.config.retain,
        )
        if info.rc != 0:
            LOG.warning("MQTT publish returned rc=%s", info.rc)

    def close(self) -> None:
        if self._client is not None:
            self._client.loop_stop()
            self._client.disconnect()
