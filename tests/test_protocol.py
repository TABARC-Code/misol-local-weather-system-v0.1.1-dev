import unittest

from misol_local.protocol import parse_observation


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.redact = {"passkey", "password", "key", "token", "secret"}

    def test_ecowitt_payload_normalises_common_values(self):
        payload = {
            "PASSKEY": "not-for-the-database",
            "stationtype": "EasyWeatherV1.6.6",
            "dateutc": "2026-09-25 19:01:02",
            "tempf": "50.0",
            "humidity": "81",
            "baromrelin": "29.92",
            "baromabsin": "29.40",
            "winddir": "247",
            "windspeedmph": "10",
            "windgustmph": "18",
            "dailyrainin": "0.25",
            "solarradiation": "321.4",
            "uv": "1.0",
        }
        obs = parse_observation(
            payload,
            path="/data/report/",
            client_ip="192.0.2.4",
            redact_keys=self.redact,
        )
        self.assertEqual(obs.protocol, "ecowitt")
        self.assertTrue(obs.station_id.startswith("station-"))
        self.assertEqual(obs.raw_redacted["PASSKEY"], "<redacted>")
        self.assertAlmostEqual(obs.normalised["temperature_out_c"], 10.0)
        self.assertAlmostEqual(obs.normalised["wind_speed_ms"], 4.47, places=2)
        self.assertAlmostEqual(obs.normalised["rain_day_mm"], 6.35, places=2)
        self.assertAlmostEqual(obs.normalised["pressure_relative_hpa"], 1013.21, places=1)

    def test_wunderground_path_detected_without_passkey(self):
        obs = parse_observation(
            {"ID": "TEST01", "tempf": "68", "humidity": "50"},
            path="/weatherstation/updateweatherstation.php",
            client_ip="192.0.2.5",
            redact_keys=self.redact,
        )
        self.assertEqual(obs.protocol, "wunderground")
        self.assertEqual(obs.station_id, "TEST01")
        self.assertAlmostEqual(obs.normalised["temperature_out_c"], 20.0)

    def test_bad_numeric_field_does_not_break_report(self):
        obs = parse_observation(
            {"tempf": "definitely warm-ish", "humidity": "60"},
            path="/data/report/",
            client_ip="192.0.2.6",
            redact_keys=self.redact,
        )
        self.assertNotIn("temperature_out_c", obs.normalised)
        self.assertEqual(obs.normalised["humidity_out_pct"], 60.0)


if __name__ == "__main__":
    unittest.main()
