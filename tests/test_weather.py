"""Forecast parsing and work reminders remain deterministic without network access."""

from __future__ import annotations

import unittest
import os
from datetime import date
from unittest.mock import patch

from shining_chatbot.weather_data import DailyForecast, WeatherLocation, _api_url, fetch_forecast, forecast_label, search_locations, work_weather_notes


class WeatherTests(unittest.TestCase):
    @patch("shining_chatbot.weather_data._get_json")
    def test_location_and_forecast_parsing(self, get_json) -> None:
        get_json.side_effect = [
            {"results": [{"name": "수원시", "admin1": "경기도", "latitude": 37.26, "longitude": 127.03}]},
            {"daily": {"time": ["2026-10-12"], "weather_code": [61], "temperature_2m_max": [19.5],
                       "apparent_temperature_max": [18.8], "precipitation_probability_max": [70],
                       "precipitation_sum": [3.2], "wind_gusts_10m_max": [28.1]}},
        ]
        location, = search_locations("수원시")
        self.assertEqual(location, WeatherLocation("수원시", "경기도", 37.26, 127.03))
        forecast, = fetch_forecast(location)
        self.assertEqual(forecast.day, date(2026, 10, 12))
        self.assertEqual(forecast_label(forecast.weather_code), "비")
        self.assertEqual(forecast.precipitation_probability_max, 70)
        self.assertTrue(any("지반" in text for text in work_weather_notes(("터파기",), forecast)))

    def test_no_weather_alert_is_invented_without_forecast(self) -> None:
        forecast = DailyForecast(date(2026, 10, 12), 0, 20, 20, 0, 0, 18)
        self.assertEqual(work_weather_notes(("실내 마감",), forecast), ())

    def test_commercial_key_uses_customer_endpoint(self) -> None:
        with patch.dict(os.environ, {"OPEN_METEO_API_KEY": "test-key"}):
            self.assertEqual(_api_url("api"), "https://customer-api.open-meteo.com/v1/forecast")
            self.assertEqual(_api_url("geocoding-api"), "https://customer-geocoding-api.open-meteo.com/v1/search")


if __name__ == "__main__":
    unittest.main()
