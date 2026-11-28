import unittest
from misol_local.calibration import historical_profile, apply_profiles

class HistoricalTests(unittest.TestCase):
    def test_short_history(self):
        self.assertFalse(historical_profile("temperature_out_c", [1.0]*13).stable)

    def test_stable_history(self):
        p = historical_profile("temperature_out_c", [1.0]*14)
        self.assertTrue(p.stable)
        self.assertEqual(p.days, 14)

    def test_drift(self):
        p = historical_profile("temperature_out_c", [0.0]*14+[2.0]*7)
        self.assertFalse(p.stable)
        self.assertEqual(p.drift, 2.0)

    def test_rejected_not_reintroduced(self):
        p = historical_profile("temperature_out_c", [1.0]*14)
        result, _ = apply_profiles({"temperature_out_c": 99}, {}, {},
                                  {"temperature_out_c": p}, apply=True)
        self.assertEqual(result, {})
