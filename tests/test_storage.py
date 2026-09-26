import tempfile
import unittest
from pathlib import Path

from misol_local.protocol import ParsedObservation
from misol_local.storage import Store


class StorageTests(unittest.TestCase):
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "test.sqlite3")
            obs = ParsedObservation(
                station_id="station-test",
                received_at="2026-09-25T20:00:00+00:00",
                protocol="ecowitt",
                normalised={"temperature_out_c": 12.3},
                raw_redacted={"PASSKEY": "<redacted>", "tempf": "54.14"},
            )
            row_id = store.add(obs)
            self.assertGreater(row_id, 0)
            self.assertEqual(store.count(), 1)
            latest = store.latest()[0]
            self.assertEqual(latest["station_id"], "station-test")
            self.assertEqual(latest["data"]["temperature_out_c"], 12.3)
            self.assertEqual(latest["raw"]["PASSKEY"], "<redacted>")


if __name__ == "__main__":
    unittest.main()
