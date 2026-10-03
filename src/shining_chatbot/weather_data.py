"""Optional location-based forecast context for the field dashboard."""

from __future__ import annotations

import os
import json
from dataclasses import dataclass
from datetime import date
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen



@dataclass(frozen=True)
class WeatherLocation:
    name: str
    region: str
    latitude: float
    longitude: float


@dataclass(frozen=True)
class DailyForecast:
    day: date
    weather_code: int | None
    temperature_max: float | None
    apparent_temperature_max: float | None
    precipitation_probability_max: int | None
    precipitation_sum: float | None
    wind_gusts_max: float | None


def _api_url(service: str) -> str:
    key = os.getenv("OPEN_METEO_API_KEY", "").strip()
    host = f"customer-{service}" if key else service
    return f"https://{host}.open-meteo.com/v1/{'search' if service == 'geocoding-api' else 'forecast'}"


def _get_json(service: str, params: dict) -> dict:
    key = os.getenv("OPEN_METEO_API_KEY", "").strip()
    if key:
        params = {**params, "apikey": key}
    try:
        with urlopen(f"{_api_url(service)}?{urlencode(params)}", timeout=7) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("기상 정보를 불러오지 못했습니다. 잠시 뒤 다시 시도하세요.") from exc
    if not isinstance(payload, dict) or payload.get("error"):
        raise ValueError("기상 서비스가 요청을 처리하지 못했습니다.")
    return payload


def search_locations(query: str) -> tuple[WeatherLocation, ...]:
    query = query.strip()
    if len(query) < 2 or len(query) > 80:
        raise ValueError("시·군·구 이름을 두 글자 이상 입력하세요.")
    payload = _get_json("geocoding-api", {
        "name": query, "count": 10, "language": "ko", "countryCode": "KR",
    })
    results = payload.get("results", [])
    if not isinstance(results, list):
        raise ValueError("위치 검색 결과를 읽을 수 없습니다.")
    locations = []
    for result in results:
        try:
            location = WeatherLocation(
                name=str(result["name"]), region=str(result.get("admin1") or result.get("country") or "대한민국"),
                latitude=float(result["latitude"]), longitude=float(result["longitude"]),
            )
        except (KeyError, TypeError, ValueError):
            continue
        if 33 <= location.latitude <= 39.5 and 124 <= location.longitude <= 132:
            locations.append(location)
    return tuple(locations)


def fetch_forecast(location: WeatherLocation) -> tuple[DailyForecast, ...]:
    if not (-90 <= location.latitude <= 90 and -180 <= location.longitude <= 180):
        raise ValueError("현장 위치의 좌표를 확인하세요.")
    payload = _get_json("api", {
        "latitude": location.latitude,
        "longitude": location.longitude,
        "daily": "weather_code,temperature_2m_max,apparent_temperature_max,precipitation_probability_max,precipitation_sum,wind_gusts_10m_max",
        "timezone": "Asia/Seoul",
        "forecast_days": 16,
    })
    daily = payload.get("daily", {})
    days = daily.get("time", []) if isinstance(daily, dict) else []
    if not isinstance(days, list) or not days:
        raise ValueError("선택한 위치의 예보 날짜가 없습니다.")

    def number(key: str, index: int, convert: type) -> int | float | None:
        values = daily.get(key, [])
        if not isinstance(values, list) or index >= len(values) or values[index] is None:
            return None
        try:
            return convert(values[index])
        except (TypeError, ValueError):
            return None

    try:
        return tuple(
            DailyForecast(
                day=date.fromisoformat(value),
                weather_code=number("weather_code", index, int),
                temperature_max=number("temperature_2m_max", index, float),
                apparent_temperature_max=number("apparent_temperature_max", index, float),
                precipitation_probability_max=number("precipitation_probability_max", index, int),
                precipitation_sum=number("precipitation_sum", index, float),
                wind_gusts_max=number("wind_gusts_10m_max", index, float),
            )
            for index, value in enumerate(days)
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("예보 날짜 형식을 읽을 수 없습니다.") from exc


def forecast_label(code: int | None) -> str:
    if code is None:
        return "예보 정보 없음"
    if code in (0, 1):
        return "맑음"
    if code in (2, 3):
        return "구름"
    if code in (45, 48):
        return "안개"
    if code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82):
        return "비"
    if code in (71, 73, 75, 77, 85, 86):
        return "눈"
    if code in (95, 96, 97, 99):
        return "뇌우"
    return "기상 변화"


def forecast_summary(location: WeatherLocation, forecast: DailyForecast) -> str:
    values = [f"{location.region} {location.name}", forecast_label(forecast.weather_code)]
    if forecast.temperature_max is not None:
        values.append(f"최고 기온 {forecast.temperature_max:.1f}°C")
    if forecast.apparent_temperature_max is not None:
        values.append(f"모델 체감 최고 {forecast.apparent_temperature_max:.1f}°C")
    if forecast.precipitation_probability_max is not None:
        values.append(f"최대 강수확률 {forecast.precipitation_probability_max}%")
    if forecast.wind_gusts_max is not None:
        values.append(f"최대 순간풍속 {forecast.wind_gusts_max:.0f} km/h")
    return " · ".join(values)


def work_weather_notes(activities: tuple[str, ...], forecast: DailyForecast) -> tuple[str, ...]:
    text = " ".join(activities)
    notes = []
    wet = forecast.weather_code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 71, 73, 75, 77, 80, 81, 82, 85, 86, 95, 96, 97, 99)
    if wet:
        notes.append("강수 예보가 있습니다. 작업 구역의 미끄럼과 전기 설비 상태를 현장에서 확인하세요.")
    if any(word in text for word in ("양중", "크레인", "타워크레인", "비계", "고소", "철골")):
        notes.append("양중·고소 작업은 예보와 별도로 현장 실측 풍속 및 장비·작업 기준을 확인하세요.")
    if any(word in text for word in ("굴착", "터파기", "흙막이")) and wet:
        notes.append("굴착 작업은 강수 이후 지반·사면·배수 상태를 다시 확인하세요.")
    apparent = forecast.apparent_temperature_max
    if apparent is not None and apparent >= 31:
        notes.append(
            f"모델 체감 최고 {apparent:.1f}°C 예보입니다. 옥외·고온 작업이 있으면 현장 체감온도를 직접 측정하고 물·그늘·냉방·휴식 조치를 확인하세요."
        )
    if apparent is not None and apparent >= 33:
        notes.append("옥외·고온 작업의 현장 체감온도가 33°C 이상이면 원칙적으로 2시간 이내 20분 이상 휴식 등 최신 온열질환 예방 기준을 확인하세요.")
    if (apparent is not None and apparent < 0) or forecast.weather_code in (71, 73, 75, 77, 85, 86):
        notes.append("영하·눈 예보입니다. 옥외·저온 작업의 방한복, 따뜻한 쉼터와 물, 작업시간대 조정을 확인하세요.")
    return tuple(notes)
