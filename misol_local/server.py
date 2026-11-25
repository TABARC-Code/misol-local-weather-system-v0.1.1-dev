"""HTTP server for MISOL Local.

EXPERIMENTAL. This is a LAN receiver, not a hardened internet-facing service.

Author: TABARC-Code
"""

from __future__ import annotations

import csv
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import logging
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .calibration import ELIGIBLE_FIELDS, apply_profiles, build_profile, consensus_samples
from .config import AppConfig
from .external import ExternalManager
from .fusion import fuse
from .mqtt import MQTTPublisher
from .protocol import parse_observation
from .quality import assess
from .storage import Store

LOG = logging.getLogger(__name__)

RECEIVER_PATHS = {
    "/data/report",
    "/data/report/",
    "/weatherstation/updateweatherstation.php",
}


class App:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.store = Store(config.server.database, store_raw=config.privacy.store_raw)
        self.mqtt = MQTTPublisher(config.mqtt)
        self.external = ExternalManager(
            config.crosscheck,
            config.openweather,
            config.openmeteo,
            config.satellite,
        )

    def _profiles(self, station_id: str) -> dict[str, object]:
        profiles = {}
        if not self.config.calibration.enabled:
            return profiles
        for field in ELIGIBLE_FIELDS:
            biases = self.store.calibration_biases(
                station_id,
                field,
                self.config.calibration.window_samples,
            )
            profiles[field] = build_profile(
                field,
                biases,
                min_samples=self.config.calibration.min_samples,
                max_mad_fraction=self.config.calibration.max_mad_fraction,
            )
        return profiles

    def calibration_snapshot(self, station_id: str | None = None) -> dict[str, object]:
        stations = [station_id] if station_id else [str(row["station_id"]) for row in self.store.latest()]
        result: dict[str, object] = {}
        for station in stations:
            profiles = self._profiles(station)
            result[station] = {
                "sample_counts": self.store.calibration_counts(station),
                "profiles": {field: profile.as_dict() for field, profile in profiles.items()},
                "apply_to_best_estimate": self.config.calibration.apply_to_best_estimate,
            }
        return {"stations": result}

    def ingest(self, data: dict[str, str], *, path: str, client_ip: str) -> dict[str, object]:
        observation = parse_observation(
            data,
            path=path,
            client_ip=client_ip,
            redact_keys=self.config.privacy.redact_keys,
        )

        previous = self.store.latest_for_station(observation.station_id)
        quality_result = assess(
            observation.normalised,
            received_at=observation.received_at,
            previous=previous.get("data") if previous else None,
            previous_received_at=str(previous["received_at"]) if previous else None,
            temporal_window_seconds=self.config.quality.temporal_window_seconds,
        ) if self.config.quality.enabled else None

        rejected_fields: set[str] = set()
        if quality_result and self.config.quality.reject_impossible:
            rejected_fields = {
                field
                for field, flags in quality_result.flags.items()
                if "below_plausible_range" in flags or "above_plausible_range" in flags
            }

        # Raw data stays untouched. Only the derived fusion input drops physically
        # implausible values when the operator explicitly enables this safety valve.
        fusion_local = {
            field: value
            for field, value in observation.normalised.items()
            if field not in rejected_fields
        }

        self.external.kick()
        fusion = fuse(
            fusion_local,
            self.external.readings().values(),
            mode=self.config.crosscheck.fusion_mode,
            max_age_seconds=self.config.crosscheck.max_age_seconds,
        ) if self.config.crosscheck.enabled else None

        best = dict(fusion.best_estimate if fusion else fusion_local)
        crosscheck = fusion.crosscheck if fusion else {}
        calibration_metadata: dict[str, object] = {}

        if self.config.calibration.enabled and fusion:
            samples = consensus_samples(fusion_local, crosscheck)
            self.store.add_calibration_samples(
                observation.station_id,
                observation.received_at,
                samples,
            )
            profiles = self._profiles(observation.station_id)
            best, calibration_metadata = apply_profiles(
                observation.normalised,
                best,
                crosscheck,
                profiles,
                apply=self.config.calibration.apply_to_best_estimate,
            )

        row_id = self.store.add(
            observation,
            external=fusion.external if fusion else None,
            best_estimate=best,
            crosscheck=crosscheck,
            quality=quality_result.as_dict() if quality_result else None,
            calibration=calibration_metadata or None,
        )
        self.mqtt.publish(
            observation,
            best_estimate=best,
            crosscheck=crosscheck,
            quality=quality_result.as_dict() if quality_result else None,
            calibration=calibration_metadata or None,
        )
        LOG.info(
            "weather report id=%s station=%s protocol=%s fields=%s qc=%s",
            row_id,
            observation.station_id,
            observation.protocol,
            len(data),
            quality_result.descriptor if quality_result else "disabled",
        )
        return {
            "id": row_id,
            "station_id": observation.station_id,
            "received_at": observation.received_at,
            "protocol": observation.protocol,
            "data": observation.normalised,
            "best_estimate": best,
            "quality": quality_result.as_dict() if quality_result else {},
            "calibration": calibration_metadata,
            "crosscheck": crosscheck,
            "external": fusion.external if fusion else {},
        }


class Handler(BaseHTTPRequestHandler):
    server_version = "MISOLLocal/0.3-experimental"

    @property
    def app(self) -> App:
        return self.server.app  # type: ignore[attr-defined]

    def log_message(self, format: str, *args: object) -> None:
        LOG.debug("%s - %s", self.address_string(), format % args)

    def _send(self, status: int, content: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(content)

    def _json(self, data: object, status: int = 200) -> None:
        self._send(
            status,
            json.dumps(data, indent=2, sort_keys=True).encode("utf-8"),
            "application/json; charset=utf-8",
        )

    def _form_data(self) -> dict[str, str] | None:
        try:
            length = int(self.headers.get("Content-Length", "0") or 0)
        except ValueError:
            return None
        if length < 0 or length > self.app.config.server.max_body_bytes:
            return None
        body = self.rfile.read(length) if length else b""
        content_type = self.headers.get("Content-Type", "")

        if "application/json" in content_type:
            try:
                parsed = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return {}
            if isinstance(parsed, dict):
                return {str(k): str(v) for k, v in parsed.items()}
            return {}

        decoded = body.decode("utf-8", "replace")
        pairs = parse_qs(decoded, keep_blank_values=True, max_num_fields=512)
        return {key: values[-1] if values else "" for key, values in pairs.items()}

    def _query_data(self) -> dict[str, str]:
        pairs = parse_qs(urlparse(self.path).query, keep_blank_values=True, max_num_fields=512)
        return {key: values[-1] if values else "" for key, values in pairs.items()}

    def _receiver_path(self) -> str:
        return urlparse(self.path).path

    def do_POST(self) -> None:  # noqa: N802
        path = self._receiver_path()
        if path not in RECEIVER_PATHS:
            self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
            return

        data = self._form_data()
        if data is None:
            self._json({"error": "request body too large or invalid"}, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
            return
        data.update(self._query_data())
        if not data:
            self._json({"error": "empty weather report"}, HTTPStatus.BAD_REQUEST)
            return

        result = self.app.ingest(data, path=path, client_ip=self.client_address[0])
        self._json({"ok": True, **result})

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path

        if path in RECEIVER_PATHS and parsed.query:
            data = self._query_data()
            result = self.app.ingest(data, path=path, client_ip=self.client_address[0])
            self._send(200, b"success\n", "text/plain; charset=utf-8")
            LOG.debug("GET ingest result: %r", result)
            return

        if path == "/health":
            self._json({
                "status": "ok",
                "experimental": True,
                "observations": self.app.store.count(),
                "external": self.app.external.snapshot(),
            })
            return

        if path == "/api/latest":
            self._json({"stations": self.app.store.latest()})
            return

        if path == "/api/crosscheck":
            self.app.external.kick()
            self._json(self.app.external.snapshot())
            return

        if path == "/api/calibration":
            query = parse_qs(parsed.query)
            station = query.get("station", [None])[0]
            self._json(self.app.calibration_snapshot(station))
            return

        if path == "/api/recent":
            query = parse_qs(parsed.query)
            try:
                limit = int(query.get("limit", ["100"])[0])
            except ValueError:
                limit = 100
            limit = max(1, min(limit, self.app.config.server.max_recent))
            self._json({"observations": self.app.store.recent(limit)})
            return

        if path == "/export.csv":
            self._export_csv(parsed.query)
            return

        if path == "/":
            self._dashboard()
            return

        self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    def _export_csv(self, query_string: str) -> None:
        query = parse_qs(query_string)
        try:
            limit = int(query.get("limit", ["1000"])[0])
        except ValueError:
            limit = 1000
        limit = max(1, min(limit, self.app.config.server.max_recent))
        rows = list(self.app.store.iter_recent(limit))

        dynamic_fields: set[str] = set()
        for row in rows:
            dynamic_fields.update(row.get("data", {}).keys())

        fields = ["id", "station_id", "received_at", "protocol", *sorted(dynamic_fields)]
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            flattened = {k: row.get(k, "") for k in fields[:4]}
            flattened.update(row.get("data", {}))
            writer.writerow(flattened)

        self._send(200, buffer.getvalue().encode("utf-8"), "text/csv; charset=utf-8")

    def _dashboard(self) -> None:
        latest = self.app.store.latest()
        cards: list[str] = []
        for row in latest:
            values = row.get("best_estimate") or row.get("data", {})
            quality = row.get("quality", {})
            quality_text = quality.get("descriptor", "not checked") if isinstance(quality, dict) else "not checked"
            lines = "".join(
                f"<tr><th>{escape(str(k))}</th><td>{escape(str(v))}</td></tr>"
                for k, v in sorted(values.items())
            )
            cards.append(
                f"""
                <section>
                  <h2>{escape(str(row['station_id']))}</h2>
                  <p>{escape(str(row['received_at']))} | {escape(str(row['protocol']))} | QC: {escape(str(quality_text))}</p>
                  <table>{lines or '<tr><td>No normalised fields yet.</td></tr>'}</table>
                </section>
                """
            )

        body = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MISOL Local - Experimental</title>
<style>
:root {{ color-scheme: dark; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; }}
body {{ max-width: 1100px; margin: 2rem auto; padding: 0 1rem; background:#111; color:#eee; }}
a {{ color:#9fd3ff; }}
header {{ border-bottom:1px solid #444; margin-bottom:2rem; }}
.badge {{ display:inline-block; padding:.2rem .5rem; border:1px solid #a77; border-radius:.3rem; }}
section {{ border:1px solid #333; border-radius:.5rem; padding:1rem; margin:1rem 0; background:#181818; }}
table {{ border-collapse:collapse; width:100%; }} th,td {{ text-align:left; border-bottom:1px solid #292929; padding:.35rem .5rem; }}
th {{ width:42%; color:#bbb; }}
code {{ background:#222; padding:.1rem .25rem; }}
</style>
</head>
<body>
<header><h1>MISOL Local</h1><p class="badge">EXPERIMENTAL</p>
<p>Local weather-console receiver with conservative cross-checking and calibration.</p></header>
<p><a href="/api/latest">latest JSON</a> | <a href="/api/recent">recent JSON</a> | <a href="/api/crosscheck">cross-check</a> | <a href="/api/calibration">calibration</a> | <a href="/export.csv">CSV</a> | <a href="/health">health</a></p>
{''.join(cards) if cards else '<section><h2>No readings yet</h2><p>Point the console custom server at <code>/data/report/</code> on this machine.</p></section>'}
</body></html>"""
        self._send(200, body.encode("utf-8"), "text/html; charset=utf-8")


class AppServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], app: App) -> None:
        super().__init__(address, Handler)
        self.app = app


def run_server(config: AppConfig) -> None:
    app = App(config)
    server = AppServer((config.server.host, config.server.port), app)
    LOG.warning("EXPERIMENTAL receiver listening on http://%s:%s", config.server.host, config.server.port)
    LOG.info("Database: %s", Path(config.server.database).resolve())
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        LOG.info("Stopping")
    finally:
        app.mqtt.close()
        server.server_close()
