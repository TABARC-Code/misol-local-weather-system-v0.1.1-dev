import unittest

from misol_local.sensor_health import analyse_station


def row(i, data, crosscheck=None, quality=None):
    return {
        "id": i,
        "station_id": "test",
        "received_at": f"2026-11-28T12:{i:02d}:00+00:00",
        "protocol": "test",
        "data": data,
        "crosscheck": crosscheck or {},
        "quality": quality or {},
    }


class SensorHealthTests(unittest.TestCase):
    def test_stable_station_is_not_called_broken(self):
        rows = [
            row(i, {
                "temperature_out_c": 10 + i * 0.05,
                "humidity_out_pct": 70 - i * 0.1,
                "pressure_relative_hpa": 1005 + i * 0.02,
                "wind_speed_ms": 2 + (i % 3) * 0.2,
                "wind_gust_ms": 3 + (i % 4) * 0.2,
                "rain_hour_mm": 0,
                "solar_radiation_wm2": 100 + i * 2,
            })
            for i in range(1, 21)
        ]
        result = analyse_station("test", rows)
        self.assertNotEqual(result["classification"], "probable_sensor_deterioration")
        self.assertGreaterEqual(result["overall_score"], 75)

    def test_flat_sensor_with_reference_disagreement_is_fault_evidence(self):
        rows = []
        for i in range(1, 21):
            rows.append(row(
                i,
                {"temperature_out_c": 12.0, "humidity_out_pct": 65.0},
                {"temperature_out_c": {
                    "status": "local_external_disagreement",
                    "providers": {"one": 18.0, "two": 18.2},
                }},
            ))
        result = analyse_station("test", rows)
        self.assertEqual(result["sensors"]["thermometer"]["verdict"], "probable_sensor_problem")
        self.assertEqual(result["classification"], "probable_sensor_deterioration")

    def test_corroborated_rapid_change_counts_as_event_evidence(self):
        rows = [
            row(i, {"temperature_out_c": 10 + i}, {
                "temperature_out_c": {"status": "ok", "providers": {"one": 10 + i}}
            }, {"flags": {"temperature_out_c": ["rapid_change"]}})
            for i in range(1, 13)
        ]
        result = analyse_station("test", rows)
        self.assertEqual(result["classification"], "probable_weather_event")


if __name__ == "__main__":
    unittest.main()
