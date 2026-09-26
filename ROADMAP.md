# Roadmap ish

I kept this intentionally short. A side project does not need a five-year strategic transformation deck.

## v0.1 — local capture

- Ecowitt/Wunderground HTTP intake
- redacted raw payload storage
- normalised metric fields
- SQLite
- JSON/CSV read-back
- optional MQTT
- Windows setup scripts
- unit tests

## v0.2 — target-hardware validation

- capture real payloads from the MISOL console
- add target-specific fixture files
- document every emitted key
- confirm calibration behaviour
- confirm retry/timeout behaviour
- handle any odd content type or path behaviour

## v0.3 — Home Assistant

- MQTT discovery
- stable device/entity IDs
- availability topic
- selected diagnostic sensors

## Later, if it remains fun

- rtl_433 parallel receiver for 433/868 MHz models
- compare RF observations against console HTTP output
- optional upstream forwarding
- Grafana/InfluxDB exporter
- compact service installer for Windows
- small packet-inspection page
