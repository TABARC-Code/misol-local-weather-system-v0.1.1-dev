"""HTTP server for MISOL Local.

EXPERIMENTAL. This is a LAN receiver, not a hardened internet-facing service.
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

from .config import AppConfig
from .mqtt import MQTTPublisher
from .protocol import parse_observation
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

    def ingest(self, data: dict[str, str], *, path: str, client_ip: str) -> dict[str, object]:
        observation = parse_observation(
            data,
            path=path,
            client_ip=client_ip,
            redact_keys=self.config.privacy.redact_keys,
        )
        row_id = self.store.add(observation)
        self.mqtt.publish(observation)
        LOG.info(
            "weather report id=%s station=%s protocol=%s fields=%s",
            row_id,
            observation.station_id,
            observation.protocol,
            len(data),
        )
        return {
            "id": row_id,
            "station_id": observation.station_id,
            "received_at": observation.received_at,
            "protocol": observation.protocol,
            "data": observation.normalised,
        }


class Handler(BaseHTTPRequestHandler):
    server_version = "MISOLLocal/0.1-experimental"

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
        self.end_headers()
        self.wfile.write(content)

    def _json(self, data: object, status: int = 200) -> None:
        self._send(
            status,
            json.dumps(data, indent=2, sort_keys=True).encode("utf-8"),
            "application/json; charset=utf-8",
        )

    def _form_data(self) -> dict[str, str]:
        length = int(self.headers.get("Content-Length", "0") or 0)
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
        pairs = parse_qs(decoded, keep_blank_values=True)
        return {key: values[-1] if values else "" for key, values in pairs.items()}

    def _query_data(self) -> dict[str, str]:
        pairs = parse_qs(urlparse(self.path).query, keep_blank_values=True)
        return {key: values[-1] if values else "" for key, values in pairs.items()}

    def _receiver_path(self) -> str:
        return urlparse(self.path).path

    def do_POST(self) -> None:  # noqa: N802
        path = self._receiver_path()
        if path not in RECEIVER_PATHS:
            self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
            return

        data = self._form_data()
        # A few firmwares append some fields in the query string even on POST.
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
            # WU clients often expect a small success body rather than JSON.
            self._send(200, b"success\n", "text/plain; charset=utf-8")
            LOG.debug("GET ingest result: %r", result)
            return

        if path == "/health":
            self._json({"status": "ok", "experimental": True, "observations": self.app.store.count()})
            return

        if path == "/api/latest":
            self._json({"stations": self.app.store.latest()})
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
            dynamic_fields.update(row.get("data", {}).keys())  # type: ignore[union-attr]

        fields = ["id", "station_id", "received_at", "protocol", *sorted(dynamic_fields)]
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            flattened = {k: row.get(k, "") for k in fields[:4]}
            flattened.update(row.get("data", {}))  # type: ignore[arg-type]
            writer.writerow(flattened)

        self._send(200, buffer.getvalue().encode("utf-8"), "text/csv; charset=utf-8")

    def _dashboard(self) -> None:
        latest = self.app.store.latest()
        cards: list[str] = []
        for row in latest:
            values = row.get("data", {})
            lines = "".join(
                f"<tr><th>{escape(str(k))}</th><td>{escape(str(v))}</td></tr>"
                for k, v in sorted(values.items())  # type: ignore[union-attr]
            )
            cards.append(
                f"""
                <section>
                  <h2>{escape(str(row['station_id']))}</h2>
                  <p>{escape(str(row['received_at']))} · {escape(str(row['protocol']))}</p>
                  <table>{lines or '<tr><td>No normalised fields yet.</td></tr>'}</table>
                </section>
                """
            )

        body = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MISOL Local — Experimental</title>
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
<p>Local weather-console receiver. Useful first, decorative later.</p></header>
<p><a href="/api/latest">latest JSON</a> · <a href="/api/recent">recent JSON</a> · <a href="/export.csv">CSV</a> · <a href="/health">health</a></p>
{''.join(cards) if cards else '<section><h2>No readings yet</h2><p>Point the console custom server at <code>/data/report/</code> on this machine.</p></section>'}
</body></html>"""
        self._send(200, body.encode("utf-8"), "text/html; charset=utf-8")


class AppServer(ThreadingHTTPServer):
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
