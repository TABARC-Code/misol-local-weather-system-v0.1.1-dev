import unittest

from misol_local.calibration import apply_profiles, build_profile, consensus_samples


class CalibrationTests(unittest.TestCase):
    def test_consensus_learning_requires_two_providers(self):
        local = {"temperature_out_c": 12.0}
        crosscheck = {
            "temperature_out_c": {
                "providers": {"openweather": 10.0, "openmeteo": 10.4},
                "selected_source": "local",
            }
        }
        samples = consensus_samples(local, crosscheck)
        self.assertEqual(len(samples), 1)
        self.assertAlmostEqual(samples[0].reference_value, 10.2)
        self.assertAlmostEqual(samples[0].bias, 1.8)

    def test_profile_requires_enough_stable_samples(self):
        profile = build_profile(
            "temperature_out_c",
            [1.0, 1.1, 0.9, 1.05],
            min_samples=4,
            max_mad_fraction=0.25,
        )
        self.assertTrue(profile.stable)
        self.assertAlmostEqual(profile.median_bias, 1.025)

    def test_apply_profile_keeps_correction_separate_until_enabled(self):
        profile = build_profile(
            "temperature_out_c",
            [1.0] * 24,
            min_samples=24,
            max_mad_fraction=0.25,
        )
        local = {"temperature_out_c": 12.0}
        crosscheck = {"temperature_out_c": {"selected_source": "local"}}
        unchanged, meta = apply_profiles(local, dict(local), crosscheck, {"temperature_out_c": profile}, apply=False)
        self.assertEqual(unchanged["temperature_out_c"], 12.0)
        self.assertFalse(meta["temperature_out_c"]["applied"])
        corrected, meta = apply_profiles(local, dict(local), crosscheck, {"temperature_out_c": profile}, apply=True)
        self.assertEqual(corrected["temperature_out_c"], 11.0)
        self.assertTrue(meta["temperature_out_c"]["applied"])


if __name__ == "__main__":
    unittest.main()
