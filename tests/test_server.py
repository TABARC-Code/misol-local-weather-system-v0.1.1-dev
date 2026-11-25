import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from misol_local.config import AppConfig
from misol_local.server import App, AppServer


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        cfg = AppConfig()
        cfg.server.host = "127.0.0.1"
        cfg.server.port = 0
        cfg.server.database = Path(self.tmp.name) / "test.sqlite3"
        self.app = App(cfg)
        self.server = AppServer(("127.0.0.1", 0), self.app)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.app.mqtt.close()
        self.tmp.cleanup()

    def test_reject_impossible_removes_only_derived_bad_value(self):
        self.app.config.quality.reject_impossible = True
        result = self.app.ingest(
            {"PASSKEY": "abc123", "humidity": "140", "tempf": "50"},
            path="/data/report/",
            client_ip="192.0.2.44",
        )
        self.assertEqual(result["data"]["humidity_out_pct"], 140.0)
        self.assertNotIn("humidity_out_pct", result["best_estimate"])
        self.assertEqual(result["best_estimate"]["temperature_out_c"], 10.0)
        self.assertEqual(result["quality"]["descriptor"], "rejected")

    def test_ecowitt_post_then_latest(self):
        body = urlencode({"PASSKEY": "abc123", "tempf": "50", "humidity": "80"}).encode()
        req = Request(
            self.base + "/data/report/",
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urlopen(req, timeout=3) as response:
            self.assertEqual(response.status, 200)

        with urlopen(self.base + "/api/latest", timeout=3) as response:
            payload = json.loads(response.read())
        self.assertEqual(len(payload["stations"]), 1)
        self.assertEqual(payload["stations"][0]["data"]["temperature_out_c"], 10.0)
        self.assertEqual(payload["stations"][0]["raw"]["PASSKEY"], "<redacted>")


if __name__ == "__main__":
    unittest.main()
