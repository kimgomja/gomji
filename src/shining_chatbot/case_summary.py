"""Transparent, keyword-only summaries of the local SANUP-P SIF archive."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import streamlit as st

from shining_chatbot.work_plan import WorkItem


SIF_SOURCE_URL = "https://www.data.go.kr/data/15140383/fileData.do"
GENERIC_TERMS = {"작업", "공사", "설치", "준비", "계속", "자재", "반입", "정리", "보수", "점검", "휴대용", "이동식"}


@dataclass(frozen=True)
class CaseSummary:
    keyword: str
    field: str
    total: int
    counts: tuple[tuple[str, int], ...]


def _root() -> Path:
    return Path(os.getenv("SANUP_P_ROOT", r"C:\SANUP-P")).expanduser()


@st.cache_data(show_spinner=False)
def _read_cases(path: str, modified: float) -> pd.DataFrame:
    del modified
    data = pd.read_parquet(path, columns=["industry_major", "work_name", "unit_work", "causal_object", "accident_type"])
    return data.loc[data["industry_major"].eq("건설업")].fillna("")


def local_cases_available() -> bool:
    return (_root() / "data/personal/processed/source_01_sif_cases.parquet").is_file()


def summarize_cases(item: WorkItem) -> CaseSummary | None:
    """Use one explicit term; never call a keyword match a risk rate or prediction."""
    path = _root() / "data/personal/processed/source_01_sif_cases.parquet"
    if not path.is_file():
        return None
    frame = _read_cases(str(path), path.stat().st_mtime)
    activity_terms = [term for term in re.findall(r"[가-힣A-Za-z]{2,}", item.activity) if term not in GENERIC_TERMS]
    equipment_terms = [term for term in re.findall(r"[가-힣A-Za-z]{2,}", item.equipment) if term not in GENERIC_TERMS]
    work_text = frame["work_name"].astype(str) + " " + frame["unit_work"].astype(str)
    equipment_text = frame["causal_object"].astype(str)
    candidates: list[tuple[int, str, str, pd.Series]] = []
    for term in dict.fromkeys(activity_terms):
        mask = work_text.str.contains(term, regex=False, case=False)
        if mask.sum() >= 5:
            candidates.append((int(mask.sum()), term, "작업명·단위작업", mask))
    if not candidates:
        for term in dict.fromkeys(equipment_terms):
            mask = equipment_text.str.contains(term, regex=False, case=False)
            if mask.sum() >= 5:
                candidates.append((int(mask.sum()), term, "기인물", mask))
    if not candidates:
        return None
    total, keyword, field, mask = min(candidates, key=lambda value: value[0])
    counts = frame.loc[mask, "accident_type"].replace("", "미분류").value_counts().head(5)
    return CaseSummary(keyword, field, total, tuple((str(name), int(value)) for name, value in counts.items()))
