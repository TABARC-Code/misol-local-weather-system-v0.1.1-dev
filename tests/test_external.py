import unittest

from misol_local.config import CrossCheckConfig, OpenMeteoConfig, OpenWeatherConfig, SatelliteConfig
from misol_local.external import fetch_openmeteo, fetch_openweather, fetch_satellite_radiation


class ExternalProviderTests(unittest.TestCase):
    def test_openweather_mapping(self):
        cfg = OpenWeatherConfig(enabled=True, api_key="test-key")
        cross = CrossCheckConfig(enabled=True, latitude=52.0, longitude=-1.0)

        def fake_getter(url, timeout):
            self.assertIn("units=metric", url)
            self.assertIn("appid=test-key", url)
            return {
                "dt": 1795600000,
                "name": "Testville",
                "main": {"temp": 11.2, "humidity": 78, "pressure": 1008},
                "wind": {"speed": 3.1, "deg": 240, "gust": 5.2},
                "rain": {"1h": 0.7},
                "clouds": {"all": 65},
            }

        reading = fetch_openweather(cfg, cross, getter=fake_getter)
        self.assertEqual(reading.provider, "openweather")
        self.assertEqual(reading.data["temperature_out_c"], 11.2)
        self.assertEqual(reading.data["wind_direction_deg"], 240.0)
        self.assertEqual(reading.data["rain_hour_mm"], 0.7)
        self.assertEqual(reading.metadata["cloud_cover_pct"], 65.0)

    def test_openmeteo_current_mapping(self):
        cfg = OpenMeteoConfig(enabled=True)
        cross = CrossCheckConfig(enabled=True, latitude=52.0, longitude=-1.0)

        def fake_getter(url, timeout):
            self.assertIn("current=", url)
            self.assertIn("wind_speed_unit=ms", url)
            return {
                "latitude": 52.0,
                "longitude": -1.0,
                "elevation": 90.0,
                "current": {
                    "time": "2026-11-25T12:00",
                    "interval": 900,
                    "temperature_2m": 10.5,
                    "relative_humidity_2m": 79,
                    "pressure_msl": 1014.2,
                    "wind_speed_10m": 3.0,
                    "wind_direction_10m": 245,
                    "wind_gusts_10m": 5.8,
                    "shortwave_radiation": 140.0,
                },
            }

        reading = fetch_openmeteo(cfg, cross, getter=fake_getter)
        self.assertEqual(reading.provider, "openmeteo")
        self.assertEqual(reading.data["temperature_out_c"], 10.5)
        self.assertEqual(reading.data["pressure_relative_hpa"], 1014.2)
        self.assertEqual(reading.metadata["source_kind"], "weather_model_current")

    def test_satellite_mapping_uses_latest_numeric_value(self):
        cfg = SatelliteConfig(enabled=True)
        cross = CrossCheckConfig(enabled=True, latitude=52.0, longitude=-1.0)

        def fake_getter(url, timeout):
            self.assertIn("shortwave_radiation_instant", url)
            return {
                "latitude": 52.0,
                "longitude": -1.0,
                "hourly": {
                    "time": ["2026-11-25T11:40", "2026-11-25T11:50", "2026-11-25T12:00"],
                    "shortwave_radiation_instant": [201.0, 217.5, None],
                },
            }

        reading = fetch_satellite_radiation(cfg, cross, getter=fake_getter)
        self.assertEqual(reading.provider, "openmeteo_satellite")
        self.assertEqual(reading.observed_at, "2026-11-25T11:50")
        self.assertEqual(reading.data["solar_radiation_wm2"], 217.5)


if __name__ == "__main__":
    unittest.main()
