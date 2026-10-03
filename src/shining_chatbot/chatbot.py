"""Separate Streamlit page for the SANUP-P source-grounded chatbot."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import streamlit as st

from shining_chatbot.chat_data import answer_data_question, chart_frame
from shining_chatbot.business_time import today_korea
from shining_chatbot.field_chat import field_intent, field_quick_answer, requested_weather_day
from shining_chatbot.field_session import clear_site_context
from shining_chatbot.infographics import monthly_infographic
from shining_chatbot.plan_revision import make_revision
from shining_chatbot.tbm_data import daily_items
from shining_chatbot.weather_data import forecast_summary, work_weather_notes
from shining_chatbot.weather_panel import weather_for_day
from shining_chatbot.work_plan import WorkPlan, read_work_plan


DEFAULT_ROOT = Path(r"C:\SANUP-P")
SOURCE_OPTIONS = {
    "전체 자료": "all",
    "SIF 사고사례": "sif",
    "사고조사보고서": "moel_report",
    "KOSHA GUIDE": "kosha_guide",
}
SEARCH_OPTIONS = {
    "의미 검색": "semantic",
    "문자·의미 혼합": "hybrid_rrf",
    "문자 검색": "lexical",
}
ERROR_MESSAGES = {
    "index_readonly": "SANUP-P 검색 색인의 쓰기 권한이 없어 열지 못했습니다. 앱을 색인에 접근할 수 있는 사용자 계정으로 실행해 주세요.",
    "index_invalid": "SANUP-P 검색 색인과 문서 데이터가 일치하지 않습니다. SANUP-P에서 색인 상태를 확인해 주세요.",
    "semantic_key_missing": "의미 검색에 사용할 OpenAI API 키를 찾지 못했습니다. 키를 설정하거나 문자 검색을 선택해 주세요.",
    "AuthenticationError": "OpenAI API 키 인증에 실패했습니다. SANUP-P의 API 키를 확인해 주세요.",
    "PermissionDeniedError": "설정된 OpenAI 모델에 접근할 수 없습니다. SANUP-P의 OPENAI_MODEL 설정을 확인해 주세요.",
    "NotFoundError": "설정된 OpenAI 모델을 찾지 못했습니다. SANUP-P의 OPENAI_MODEL 설정을 확인해 주세요.",
    "RateLimitError": "OpenAI API 요청 한도에 도달했습니다. 계정 사용량과 결제 설정을 확인한 뒤 다시 시도해 주세요.",
    "APIConnectionError": "OpenAI API에 연결하지 못했습니다. 네트워크 연결을 확인한 뒤 다시 시도해 주세요.",
    "APITimeoutError": "OpenAI API 응답 시간이 초과됐습니다. 잠시 후 다시 시도해 주세요.",
    "Timeout": "검색 또는 답변 시간이 초과됐습니다. 검색 조건을 좁혀 다시 시도해 주세요.",
    "RuntimeUnavailable": "SANUP-P 가상환경을 실행하지 못했습니다. 연결 경로와 가상환경을 확인해 주세요.",
    "InvalidResponse": "챗봇 실행 결과를 읽지 못했습니다. SANUP-P 실행 환경을 확인해 주세요.",
}


def _root() -> Path:
    return Path(os.getenv("SANUP_P_ROOT", str(DEFAULT_ROOT))).expanduser()


def _has_api_key(root: Path) -> bool:
    if os.getenv("OPENAI_API_KEY", "").strip():
        return True
    try:
        for line in (root / ".env").read_text(encoding="utf-8-sig").splitlines():
            name, separator, value = line.partition("=")
            if separator and name.strip() == "OPENAI_API_KEY" and value.strip().strip("\"'"):
                return True
    except OSError:
        pass
    return False


def _missing_files(root: Path) -> list[str]:
    required = (
        ".venv/Scripts/python.exe",
        "src/retriever.py",
        "src/rag_chain.py",
        "data/personal/corpus/chunks.jsonl",
        "data/personal/corpus/index_meta.json",
        "data/personal/corpus/index_meta_semantic.json",
        "chroma_db/personal/chroma.sqlite3",
    )
    return [item for item in required if not (root / item).is_file()]


def ask_sanup(root: Path, request: dict) -> dict:
    bridge = Path(__file__).with_name("rag_bridge.py")
    command = [str(root / ".venv/Scripts/python.exe"), "-X", "utf8", str(bridge), str(root)]
    try:
        completed = subprocess.run(
            command,
            input=json.dumps(request, ensure_ascii=False),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=150,
            cwd=root,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"status": "error", "code": "Timeout", "answer": "", "sources": []}
    except OSError:
        return {"status": "error", "code": "RuntimeUnavailable", "answer": "", "sources": []}
    try:
        result = json.loads(completed.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        return {"status": "error", "code": "InvalidResponse", "answer": "", "sources": []}
    if not isinstance(result, dict):
        return {"status": "error", "code": "InvalidResponse", "answer": "", "sources": []}
    return result


def _show_sources(sources: list[dict], *, verified: bool = True) -> None:
    if not sources:
        return
    label = "근거 문서" if verified else "검색된 문서"
    with st.expander(f"{label} {len(sources)}건", expanded=True):
        for source in sources:
            number = source.get("number", "")
            title = source.get("title") or "제목 없음"
            organization = source.get("organization") or ""
            page = source.get("page")
            detail = " · ".join(
                item for item in (organization, f"{page}쪽" if page else "") if item
            )
            with st.container(border=True):
                st.markdown(f"**[{number}] {title}**")
                if detail:
                    st.caption(detail)
                if source.get("ocr_review_required"):
                    st.caption("OCR 자동 인식 · PDF 원문 대조 필요")
                url = str(source.get("url") or "")
                if urlparse(url).scheme in {"https", "http"}:
                    st.link_button("원문 보기 ↗", url)


def _show_message(message: dict, incidents: pd.DataFrame) -> None:
    avatar = ":material/person:" if message["role"] == "user" else ":material/auto_awesome:"
    with st.chat_message(message["role"], avatar=avatar):
        content = message["content"] if message.get("tbm") else message["content"].replace("- [ ] ", "- ")
        st.markdown(content)
        if message["role"] == "assistant":
            if chart := message.get("chart"):
                chart_data, start, end = chart_frame(incidents, chart)
                st.markdown(monthly_infographic(chart_data, start, end, chart.get("id", "chat-chart")), unsafe_allow_html=True)
            _show_sources(message.get("sources") or [], verified=message.get("status") == "answered")


def show_chatbot(incidents: pd.DataFrame, source_name: str, is_sample: bool, data_token: str) -> None:
    root = _root()
    missing = _missing_files(root)
    has_key = _has_api_key(root)
    ready = not missing
    field_plan: WorkPlan | None = st.session_state.get("field_plan")
    field_day = st.session_state.get("field_day")
    if not isinstance(field_day, date):
        field_day = today_korea()

    st.markdown(
        '<div class="chat-page-heading"><div><span>INCIDENT INTELLIGENCE / ASSISTANT</span>'
        '<h2>현장 작업과 근거 문서에 질문하기</h2><p>작업·조치·TBM 상태는 현재 계획에서 바로 답하고, '
        '오늘·내일·모레 날씨는 연결한 현장 위치의 예보로 확인합니다. 사고 사례는 SIF·사고조사보고서·KOSHA GUIDE의 근거로 답합니다.</p></div>'
        f'<div class="chat-source-mark">{"CSV + 3 SOURCES" if ready else "FIELD + CSV"}</div></div>',
        unsafe_allow_html=True,
    )
    if missing:
        st.info(
            f"현장 작업·조치·TBM 질문과 CSV 조회는 사용할 수 있습니다. "
            f"SANUP-P 문서 검색은 {root}의 필요 파일 {len(missing)}개가 없어 연결되지 않았습니다."
        )
    elif not has_key:
        st.info("OpenAI API 키가 없어 문자 검색으로 근거 문서만 보여줍니다. 답변 생성은 SANUP-P의 .env에 키를 설정하면 사용할 수 있습니다.")

    if st.session_state.get("_chat_data_token") != data_token:
        st.session_state.rag_messages = []
        st.session_state["_chat_data_token"] = data_token

    chat_col, option_col = st.columns([1.75, 1], gap="medium")
    with option_col:
        with st.container(border=True, key="chat_options"):
            st.markdown('<div class="chat-options-kicker">SEARCH SETTINGS</div><h3>검색 조건</h3>', unsafe_allow_html=True)
            with st.expander("일회성 작업계획서 첨부 (.xlsx)"):
                work_file = st.file_uploader("작업계획서", type="xlsx", key="chat_work_file")
                if work_file is not None:
                    try:
                        attached = read_work_plan(work_file.getvalue())
                    except ValueError as exc:
                        st.error(str(exc))
                    else:
                        if attached.issues:
                            st.warning(f"읽지 못한 행 {len(attached.issues)}건이 있습니다. 오늘의 작업 화면에서 원문을 확인하세요.")
                        choices = {
                            f"{item.day:%m.%d} {item.start:%H:%M} · {item.activity} ({item.work_id})": item
                            for item in attached.items
                        }
                        chosen_label = st.selectbox("질문할 작업", list(choices), key="chat_attached_item")
                        chosen = choices[chosen_label]
                        st.caption(f"{chosen.area} {chosen.location} · {chosen.equipment or '장비 미입력'} · {chosen.sheet} {chosen.row}행")
                        if st.button("이 작업으로 질문하기", key="chat_use_attached_work"):
                            st.session_state["rag_context"] = f"{attached.site} / {chosen.day:%Y.%m.%d} / {chosen.area} {chosen.location} / {chosen.activity}"
                            st.session_state["rag_equipment"] = chosen.equipment
                            st.session_state["rag_industry"] = "건설업"
                            st.rerun()
                        if st.button("오늘의 작업에 추가", key="chat_add_attached_work"):
                            existing: WorkPlan | None = st.session_state.get("field_plan")
                            if existing and existing.site != attached.site:
                                st.error("현재 대시보드와 현장명이 다릅니다. 오늘의 작업 화면에서 새 계획서로 적용하세요.")
                            elif existing and any(item.work_id == chosen.work_id for item in existing.items):
                                st.info("이 작업ID는 이미 오늘의 작업 목록에 있습니다.")
                            else:
                                if existing is None:
                                    clear_site_context(
                                        st.session_state,
                                        preserve=("chat_work_file", "chat_attached_item"),
                                    )
                                updated = WorkPlan(
                                    attached.site,
                                    tuple(sorted((*existing.items, chosen), key=lambda item: (item.day, item.start))) if existing else (chosen,),
                                    existing.issues if existing else attached.issues,
                                    existing.no_work_confirmations if existing else (),
                                )
                                st.session_state["field_plan"] = updated
                                revision = make_revision(existing, updated, work_file.name)
                                st.session_state["field_revisions"] = (*st.session_state.get("field_revisions", ()), revision)
                                st.session_state["field_plan_name"] = work_file.name
                                st.session_state.pop("field_plan_days", None)
                                st.session_state["field_day"] = chosen.day
                                st.session_state["view"] = "field"
                                st.query_params["page"] = "field"
                                st.rerun()
            source_label = st.selectbox("자료 종류", list(SOURCE_OPTIONS), key="rag_source")
            modes = list(SEARCH_OPTIONS) if has_key else ["문자 검색"]
            mode_label = st.selectbox("검색 방식", modes, key="rag_mode")
            work_context = st.text_area(
                "현재 작업",
                key="rag_context",
                placeholder="예: 건설현장 이동식 사다리 점검",
                height=86,
                max_chars=1000,
            )
            if work_context.strip():
                st.caption("선택한 작업 맥락이 아래 문서 검색 질문에 함께 적용됩니다.")
            with st.expander("검색 조건 더보기"):
                industry = st.text_input("업종", key="rag_industry", placeholder="예: 건설업", max_chars=100)
                equipment = st.text_input("장비·기인물", key="rag_equipment", placeholder="예: 사다리", max_chars=200)
            st.caption("이 조건은 근거 문서 검색에 적용됩니다. 지역·월별 질문은 현재 사고 CSV를 사용합니다.")
        with st.container(border=True, key="chat_reference"):
            st.markdown('<div class="chat-options-kicker">SOURCE POLICY</div><h3>답변 확인</h3>', unsafe_allow_html=True)
            st.markdown("현재 사고 데이터는 **" + source_name + "**입니다. 문서 답변의 인용 번호는 아래 근거 문서와 대조하세요.")
            st.caption("OCR 문장은 PDF 원문 확인이 필요합니다. 현장 위험성평가나 공식 지침을 대체하지 않습니다.")

    with chat_col:
        st.markdown('<div class="chat-conversation-head"><div><span>SAFETY ASSISTANT</span><h3>대화</h3></div></div>', unsafe_allow_html=True)
        if not st.session_state.rag_messages:
            st.markdown(
                '<div class="chat-empty"><span>✳</span><h3>무엇을 확인할까요?</h3>'
                '<p>선택일 작업과 남은 조치를 바로 확인하거나, 작업·장비를 적어 근거 사례를 찾으세요.</p></div>',
                unsafe_allow_html=True,
            )
        for message in st.session_state.rag_messages:
            _show_message(message, incidents)

        field_prompt = None
        with st.container(key="chat_field_shortcuts"):
            if field_plan is not None:
                st.caption(f"현장 요약 기준일 · {field_day:%Y.%m.%d} · 오늘 주의사항은 오늘 날짜를 기준으로 합니다.")
                attention_col, work_col, action_col = st.columns(3, gap="small")
                with attention_col:
                    if st.button("오늘 주의사항", width="stretch"):
                        field_prompt = "오늘 주의사항"
                with work_col:
                    if st.button("선택일 작업 요약", width="stretch"):
                        field_prompt = "선택일 작업 요약"
                with action_col:
                    if st.button("남은 조치", width="stretch"):
                        field_prompt = "남은 조치"
                status_col, change_col, weather_col = st.columns(3, gap="small")
                with status_col:
                    if st.button("TBM 준비 상태", width="stretch"):
                        field_prompt = "TBM 준비 상태"
                with change_col:
                    if st.button("최근 계획 변경", width="stretch"):
                        field_prompt = "최근 계획 변경"
                with weather_col:
                    if st.button("오늘 현장 날씨", width="stretch"):
                        field_prompt = "오늘 현장 날씨"
        example_col, tbm_col = st.columns(2, gap="small")
        with example_col:
            example_clicked = st.button("현재 작업 사례 묻기" if work_context.strip() else "사다리 작업 사례 묻기", disabled=not ready, width="stretch")
        with tbm_col:
            tbm_clicked = st.button(
                "현재 작업 TBM 초안",
                disabled=not ready or not has_key or not work_context.strip(),
                width="stretch",
            )
        monthly_clicked = st.button("월별 사고 그래프 보기", width="stretch")
        prompt = st.chat_input("작업·조치·TBM·날씨, 지역·월·계절별 사고나 근거 사례를 질문하세요")
        if field_prompt:
            prompt = field_prompt
        if example_clicked:
            prompt = (
                f"{work_context} 작업에서 {equipment or '사용 장비'}와 관련된 사고사례와 예방 조치를 근거와 함께 알려줘."
                if work_context.strip() else "이동식 사다리 작업에서 확인할 사고사례와 예방 조치를 알려줘."
            )
        if tbm_clicked:
            prompt = "현재 작업에 맞춰 검색된 사고사례와 안전지침에 근거한 TBM 시작 전 체크리스트를 작성해 주세요."
        if monthly_clicked:
            prompt = "전체 월별 사고 그래프 보여줘"
        if not prompt:
            return

        history = st.session_state.rag_messages[-6:]
        user_message = {"role": "user", "content": prompt}
        st.session_state.rag_messages.append(user_message)
        weather_text = ""
        weather_notes = ()
        answer_intent = field_intent(prompt)
        weather_day = None
        if field_plan and answer_intent in {"오늘주의사항", "현장날씨"}:
            location = st.session_state.get("field_weather_location")
            weather_day = requested_weather_day(prompt) if answer_intent == "현장날씨" else today_korea()
            forecast = weather_for_day(weather_day) if location else None
            if forecast is not None:
                weather_text = forecast_summary(location, forecast)
                weather_notes = work_weather_notes(
                    tuple(item.activity for item in daily_items(field_plan, weather_day)), forecast,
                )
        field_answer = field_quick_answer(
            prompt, field_plan, field_day,
            st.session_state.get("field_reviews", {}),
            tuple(st.session_state.get("field_actions", ())),
            st.session_state.get("field_tbm_records", {}),
            st.session_state.get("field_tbm_deliveries", {}),
            tuple(st.session_state.get("field_revisions", ())),
            weather_text, weather_notes, weather_day,
        )
        if field_answer is not None:
            st.session_state.rag_messages.append(field_answer)
            st.rerun()
        local_answer = answer_data_question(prompt, incidents, is_sample=is_sample, history=history)
        if local_answer is not None:
            st.session_state.rag_messages.append(local_answer)
            st.rerun()
        _show_message(user_message, incidents)
        if not ready:
            st.session_state.rag_messages.append({
                "role": "assistant",
                "status": "error",
                "content": "SANUP-P 문서 색인에 연결할 수 없습니다. 왼쪽 CSV 관리에서 지역·월별 사고 질문은 계속 사용할 수 있습니다.",
            })
            st.rerun()
        request = {
            "question": prompt,
            "source": SOURCE_OPTIONS[source_label],
            "mode": SEARCH_OPTIONS[mode_label],
            "work_context": work_context,
            "industry_major": industry,
            "equipment": equipment,
            "history": history,
            "tbm": tbm_clicked,
        }
        with st.chat_message("assistant", avatar=":material/auto_awesome:"):
            with st.spinner("근거 문서를 검색하고 인용을 확인하는 중..."):
                result = ask_sanup(root, request)
            status = result.get("status")
            if status == "answered":
                answer = result.get("answer") or "답변을 받지 못했습니다."
            elif status == "insufficient_evidence":
                answer = "제공된 근거 자료에서 답을 확인할 수 없습니다. 작업·장비·사고 유형을 더 구체적으로 적어 주세요."
            elif status == "llm_key_missing":
                answer = "관련 문서는 찾았습니다. 답변 생성을 사용하려면 SANUP-P의 OpenAI API 키를 설정해 주세요."
            elif status in {"unsupported_citation", "malformed_quantity", "empty_response"}:
                answer = "관련 문서는 찾았지만 생성된 답변의 인용을 검증하지 못했습니다. 아래 검색 문서를 직접 확인하거나 질문을 더 구체적으로 적어 주세요."
            elif status == "error":
                code = str(result.get("code") or "UnknownError")
                answer = ERROR_MESSAGES.get(code, f"검색 실행 중 오류가 발생했습니다. 오류 코드: {code}. 이 코드를 알려주시면 원인을 확인하겠습니다.")
            else:
                answer = f"답변 상태를 확인할 수 없습니다. 상태 코드: {status or 'unknown'}."
            st.markdown(answer)
            sources = (result.get("sources") or []) if status in {"answered", "llm_key_missing", "unsupported_citation", "malformed_quantity", "empty_response"} else []
            _show_sources(sources, verified=status == "answered")
        st.session_state.rag_messages.append(
            {"role": "assistant", "content": answer, "sources": sources, "tbm": tbm_clicked, "status": status}
        )
        st.rerun()
