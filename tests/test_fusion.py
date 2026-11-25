import unittest
from datetime import datetime, timezone

from misol_local.external import ExternalReading
from misol_local.fusion import fuse


class FusionTests(unittest.TestCase):
    def reading(self, provider, data):
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        return ExternalReading(provider, now, now, data)

    def test_fill_gaps_does_not_overwrite_local(self):
        local = {"temperature_out_c": 10.0}
        external = self.reading("openweather", {"temperature_out_c": 13.5, "humidity_out_pct": 80.0})
        result = fuse(local, [external], mode="fill_gaps")
        self.assertEqual(result.best_estimate["temperature_out_c"], 10.0)
        self.assertEqual(result.best_estimate["humidity_out_pct"], 80.0)
        self.assertEqual(result.crosscheck["temperature_out_c"]["status"], "local_external_disagreement")

    def test_guarded_requires_two_agreeing_external_sources(self):
        local = {"temperature_out_c": 20.0}
        a = self.reading("source_a", {"temperature_out_c": 10.0})
        b = self.reading("source_b", {"temperature_out_c": 10.4})
        result = fuse(local, [a, b], mode="guarded")
        self.assertAlmostEqual(result.best_estimate["temperature_out_c"], 10.2)
        self.assertEqual(result.crosscheck["temperature_out_c"]["status"], "corrected_by_external_consensus")

    def test_one_external_source_never_corrects_existing_local_value(self):
        local = {"temperature_out_c": 20.0}
        a = self.reading("openweather", {"temperature_out_c": 5.0})
        result = fuse(local, [a], mode="guarded")
        self.assertEqual(result.best_estimate["temperature_out_c"], 20.0)


if __name__ == "__main__":
    unittest.main()
