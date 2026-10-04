"""Compact forecast context with explicit site selection."""

from __future__ import annotations

from datetime import date
from html import escape

import streamlit as st

from shining_chatbot.weather_data import WeatherLocation, fetch_forecast, forecast_label, search_locations, work_weather_notes
from shining_chatbot.work_plan import WorkItem


@st.cache_data(ttl=3600, show_spinner=False)
def _locations(query: str) -> tuple[WeatherLocation, ...]:
    return search_locations(query)


@st.cache_data(ttl=1800, show_spinner=False)
def _forecast(location: WeatherLocation):
    return fetch_forecast(location)


def _weather_styles() -> None:
    st.markdown("""<style>
.weather-panel{border:1px solid #DCE7DC;border-radius:8px;background:#F7FAF6;padding:15px 18px;margin:17px 0 22px}
.weather-head{display:flex;justify-content:space-between;gap:18px;align-items:baseline}.weather-head strong{font-size:13px;font-weight:620;color:#294333}
.weather-head span{font-size:10px;color:#7B917F}.weather-values{display:flex;gap:24px;flex-wrap:wrap;margin:15px 0 5px}
.weather-value b{display:block;color:#324D3A;font-size:18px;line-height:1.2;font-weight:610;letter-spacing:-.03em}
.weather-value small{display:block;color:#879789;font-size:10px;margin-top:4px}.weather-notes{margin-top:10px;padding-top:10px;border-top:1px solid #E0E9DF;color:#506553;font-size:11px;line-height:1.65}
.weather-source{color:#68796D;font-size:10px;line-height:1.6;margin-top:8px}.weather-source a{color:#456A4E;text-decoration:underline;text-underline-offset:2px}
@media(max-width:640px){.weather-values{gap:12px}.weather-value{width:calc(50% - 10px)}}
</style>""", unsafe_allow_html=True)


def _location_setup() -> None:
    with st.expander("현장 예보 위치 설정", expanded=False):
        st.caption("현장과 가까운 시·군·구를 검색해 확인하세요. 계획서의 현장명에서 위치를 추측하지 않습니다.")
        with st.form("field_weather_search"):
            query = st.text_input("시·군·구 검색", placeholder="예: 수원시", max_chars=80, key="field_weather_query")
            searched = st.form_submit_button("위치 찾기")
        if searched:
            st.session_state.pop("field_weather_candidate", None)
            try:
                with st.spinner("현장 위치 검색 중..."):
                    st.session_state["field_location_candidates"] = _locations(query)
            except ValueError as exc:
                st.error(str(exc))
            else:
                if not st.session_state["field_location_candidates"]:
                    st.info("검색 결과가 없습니다. 가까운 시·군·구 이름으로 다시 검색하세요.")
        candidates = st.session_state.get("field_location_candidates", ())
        if candidates:
            labels = {
                f"{location.region} · {location.name} ({location.latitude:.3f}, {location.longitude:.3f})": location
                for location in candidates
            }
            selected = st.selectbox("현장과 가장 가까운 위치", list(labels), key="field_weather_candidate")
            if st.button("이 위치로 예보 연결", type="primary", key="field_weather_save"):
                st.session_state["field_weather_location"] = labels[selected]
                st.session_state.pop("field_location_candidates", None)
                st.rerun()


def weather_for_day(day: date):
    location: WeatherLocation | None = st.session_state.get("field_weather_location")
    if location is None:
        return None
    try:
        with st.spinner("현장 예보 불러오는 중..."):
            forecasts = _forecast(location)
    except ValueError as exc:
        st.session_state["field_weather_error"] = (day, str(exc))
        st.warning(str(exc))
        return None
    st.session_state.pop("field_weather_error", None)
    return next((forecast for forecast in forecasts if forecast.day == day), None)


def show_weather_panel(day: date, items: list[WorkItem]) -> None:
    _weather_styles()
    location: WeatherLocation | None = st.session_state.get("field_weather_location")
    if location is None:
        st.markdown(
            '<div class="weather-panel"><div class="weather-head"><strong>현장 날씨</strong><span>위치 설정 필요</span></div>'
            '<div class="weather-source">위치를 확인하면 이 날짜의 예보와 작업 관련 확인 문구를 표시합니다.</div></div>',
            unsafe_allow_html=True,
        )
        _location_setup()
        return
    forecast = weather_for_day(day)
    if forecast is None:
        error = st.session_state.get("field_weather_error")
        failed = isinstance(error, tuple) and error[0] == day
        guidance = (
            "예보 연결에 실패했습니다. 잠시 뒤 다시 시도하고 기상청 특보를 직접 확인하세요."
            if failed else
            "선택한 날짜의 예보 범위를 확인할 수 없습니다. 현장 기상과 기상특보를 직접 확인하세요."
        )
        st.markdown(
            '<div class="weather-panel"><div class="weather-head"><strong>현장 날씨</strong>'
            f'<span>{escape(location.region)} · {escape(location.name)}</span></div>'
            f'<div class="weather-source">{guidance}</div></div>',
            unsafe_allow_html=True,
        )
        if failed:
            if st.button("예보 다시 불러오기", key=f"field_weather_retry_{day}"):
                _forecast.clear()
                st.rerun()
        _location_setup()
        return
    values = (
        (forecast_label(forecast.weather_code), "하루 예보"),
        (f"{forecast.precipitation_probability_max}%" if forecast.precipitation_probability_max is not None else "—", "최대 강수확률"),
        (f"{forecast.temperature_max:.1f}°" if forecast.temperature_max is not None else "—", "최고 기온"),
        (f"{forecast.apparent_temperature_max:.1f}°" if forecast.apparent_temperature_max is not None else "—", "모델 체감 최고"),
        (f"{forecast.wind_gusts_max:.0f} km/h" if forecast.wind_gusts_max is not None else "—", "최대 순간풍속 예보"),
    )
    cells = "".join(f'<div class="weather-value"><b>{escape(value)}</b><small>{escape(label)}</small></div>' for value, label in values)
    notes = work_weather_notes(tuple(item.activity for item in items), forecast)
    note_html = "<br>".join(escape(note) for note in notes) if notes else "작업 전 현장 기상과 장비·작업 기준을 확인하세요."
    st.markdown(
        '<div class="weather-panel"><div class="weather-head"><strong>현장 날씨 · 작업 확인</strong>'
        f'<span>{escape(location.region)} · {escape(location.name)} · {day:%m.%d}</span></div>'
        f'<div class="weather-values">{cells}</div><div class="weather-notes">{note_html}</div>'
        '<div class="weather-source">모델 예보: <a href="https://open-meteo.com/en/docs" target="_blank" rel="noopener noreferrer">Open-Meteo</a> · '
        '<a href="https://www.weather.go.kr/w/weather/warning/status.do" target="_blank" rel="noopener noreferrer">기상청 특보 확인 ↗</a> · '
        '<a href="https://www.kosha.or.kr/safety1team/tr/reference.do?articleNo=456837&attachNo=263892&mode=download" target="_blank" rel="noopener noreferrer">안전보건공단 폭염 예방수칙 ↗</a> · '
        '<a href="https://www.moel.go.kr/news/cardinfo/view.do?bbs_seq=20251200063" target="_blank" rel="noopener noreferrer">고용노동부 한파 안전 안내 ↗</a> · '
        '모델 예보는 현장 측정이나 작업 허가 기준을 대신하지 않습니다.</div></div>',
        unsafe_allow_html=True,
    )
    _location_setup()
