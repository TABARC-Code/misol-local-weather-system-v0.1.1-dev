import unittest

from misol_local.quality import assess


class QualityTests(unittest.TestCase):
    def test_impossible_humidity_is_rejected(self):
        result = assess({"humidity_out_pct": 140.0}, received_at="2026-11-25T12:00:00+00:00")
        self.assertEqual(result.descriptor, "rejected")
        self.assertIn("above_plausible_range", result.flags["humidity_out_pct"])

    def test_fast_pressure_change_is_questioned(self):
        result = assess(
            {"pressure_relative_hpa": 1030.0},
            received_at="2026-11-25T12:10:00+00:00",
            previous={"pressure_relative_hpa": 1000.0},
            previous_received_at="2026-11-25T12:00:00+00:00",
        )
        self.assertEqual(result.descriptor, "questioned")
        self.assertIn("rapid_change", result.flags["pressure_relative_hpa"])

    def test_gust_below_wind_is_flagged(self):
        result = assess(
            {"wind_speed_ms": 10.0, "wind_gust_ms": 7.0},
            received_at="2026-11-25T12:00:00+00:00",
        )
        self.assertIn("gust_below_sustained_wind", result.flags["wind_gust_ms"])


if __name__ == "__main__":
    unittest.main()
