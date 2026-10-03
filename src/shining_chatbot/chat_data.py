"""Answer regional and monthly questions from the dashboard's current CSV."""

from __future__ import annotations

from datetime import date
from uuid import uuid4

import pandas as pd


REGION_ALIASES = {
    "서울": ("서울특별시", "서울시", "서울"),
    "부산": ("부산광역시", "부산시", "부산"),
    "대구": ("대구광역시", "대구시", "대구"),
    "인천": ("인천광역시", "인천시", "인천"),
    "광주": ("광주광역시", "광주시", "광주"),
    "대전": ("대전광역시", "대전시", "대전"),
    "울산": ("울산광역시", "울산시", "울산"),
    "세종": ("세종특별자치시", "세종시", "세종"),
    "경기": ("경기도", "경기"),
    "강원": ("강원특별자치도", "강원도", "강원"),
    "충북": ("충청북도", "충북"),
    "충남": ("충청남도", "충남"),
    "전북": ("전북특별자치도", "전라북도", "전북"),
    "전남": ("전라남도", "전남"),
    "경북": ("경상북도", "경북"),
    "경남": ("경상남도", "경남"),
    "제주": ("제주특별자치도", "제주도", "제주"),
}


def _region_in(text: str, frame: pd.DataFrame) -> str | None:
    for region, aliases in REGION_ALIASES.items():
        if any(alias in text for alias in aliases):
            return region
    for value in sorted(frame["지역"].dropna().astype(str).unique(), key=len, reverse=True):
        if value in text:
            return value
    return None


def _matching_rows(frame: pd.DataFrame, region: str | None) -> pd.DataFrame:
    if region is None:
        return frame
    aliases = REGION_ALIASES.get(region, (region,))
    values = frame["지역"].astype(str)
    return frame.loc[values.map(lambda value: any(alias in value or value in alias for alias in aliases))]


def answer_data_question(
    question: str,
    frame: pd.DataFrame,
    *,
    is_sample: bool,
    history: list[dict],
) -> dict | None:
    """Return a local-data response, or None for a document RAG question."""
    monthly = any(term in question for term in ("월간", "월별", "매월")) and any(
        term in question for term in ("그래프", "차트", "추이", "발생", "사고", "보여", "그려")
    )
    region = _region_in(question, frame)
    context_note = ""
    if monthly and region is None and "전체" not in question:
        previous_region = next(
            (
                previous_region
                for message in reversed(history)
                if message.get("role") == "user"
                if (previous_region := _region_in(str(message.get("content") or ""), frame))
            ),
            None,
        )
        if previous_region and _matching_rows(frame, previous_region).empty:
            context_note = f"직전에 물어본 {previous_region} 기록은 현재 CSV에 없어 전체 지역의 그래프를 보여드립니다. "
        else:
            region = previous_region
    if not monthly and region is None:
        return None

    selected = _matching_rows(frame, region)
    source_label = "시연용 가상 데이터" if is_sample else "업로드한 CSV"
    subject = f"{region} 지역" if region else "전체 지역"
    if selected.empty:
        next_step = (
            "이 샘플에는 실제 지역별 현황이 담겨 있지 않습니다. 왼쪽 CSV 관리에서 제주 기록이 포함된 파일을 올리면 조회할 수 있습니다."
            if is_sample else "이는 해당 지역의 실제 사고가 0건이라는 뜻이 아닙니다. 업로드한 파일의 지역 표기와 포함 범위를 확인해 주세요."
        )
        return {
            "role": "assistant",
            "status": "data_answer",
            "content": f"현재 **{source_label}**에 **{subject} 사고 기록이 없습니다.** {next_step}",
        }

    if monthly:
        latest = frame["발생일"].max()
        earliest = frame["발생일"].min()
        start = max(earliest.to_period("M"), latest.to_period("M") - 23).start_time.date()
        end = latest.date()
        in_period = selected.loc[selected["발생일"].dt.date.between(start, end)]
        return {
            "role": "assistant",
            "status": "data_answer",
            "content": (
                context_note + f"**{source_label} · {subject}**의 월별 사고 기록입니다. "
                f"{start:%Y.%m}–{end:%Y.%m} 기간에 **{len(in_period):,}건**이 있습니다. "
                "그래프의 막대에 마우스를 올리면 월별 건수와 재해정도를 볼 수 있습니다."
            ),
            "chart": {"region": region, "start": start.isoformat(), "end": end.isoformat(), "id": f"chat-{uuid4().hex[:8]}"},
        }

    counts = selected["사고유형"].value_counts()
    leading_type = f" 가장 많은 사고유형은 **{counts.index[0]} {counts.iloc[0]:,}건**입니다." if not counts.empty else ""
    earliest = selected["발생일"].min()
    latest = selected["발생일"].max()
    return {
        "role": "assistant",
        "status": "data_answer",
        "content": (
            f"**{source_label}**에서 **{subject} 사고 기록 {len(selected):,}건**을 확인했습니다. "
            f"기록 기간은 {earliest:%Y.%m.%d}–{latest:%Y.%m.%d}입니다.{leading_type} "
            "이 수치는 현재 CSV에 포함된 기록만 집계합니다."
        ),
    }


def chart_frame(frame: pd.DataFrame, chart: dict) -> tuple[pd.DataFrame, date, date]:
    selected = _matching_rows(frame, chart.get("region"))
    start, end = date.fromisoformat(chart["start"]), date.fromisoformat(chart["end"])
    return selected.loc[selected["발생일"].dt.date.between(start, end)], start, end
