"""Daily manager briefing assembled from the reviewed work plan."""

from __future__ import annotations

from datetime import date
from html import escape

import streamlit as st

from shining_chatbot.action_data import FieldAction
from shining_chatbot.business_time import today_korea
from shining_chatbot.field_dashboard import _styles
from shining_chatbot.plan_revision import day_revision_token
from shining_chatbot.tbm_data import TbmDelivery, TbmRecord, brief_fingerprint, briefing_html, briefing_text, confirm_brief, daily_actions, daily_items, record_delivery
from shining_chatbot.weather_data import forecast_summary, work_weather_notes
from shining_chatbot.weather_panel import weather_for_day
from shining_chatbot.work_plan import WorkPlan, overlapping_pairs


def _go_field() -> None:
    st.session_state["view"] = "field"
    st.query_params["page"] = "field"
    st.rerun()


def _brief_styles() -> None:
    st.markdown("""<style>
.tbm-intro{max-width:680px;color:#617166;font-size:13px;line-height:1.7;margin:0 0 24px}
.tbm-section{margin:26px 0 11px;display:flex;align-items:baseline;justify-content:space-between;gap:12px}
.tbm-section h2{font-size:16px;letter-spacing:-.025em;font-weight:620;margin:0;color:#293C30}
.tbm-section span{font-size:11px;color:#829287}
.tbm-work{display:grid;grid-template-columns:74px minmax(0,1fr) auto;gap:17px;align-items:start;padding:16px 4px;border-top:1px solid #E5ECE5}
.tbm-work-time{color:#50765A;font-size:12px;font-weight:620}.tbm-work-time small{display:block;color:#9AA99D;font-size:11px;font-weight:400}
.tbm-work h3{margin:0 0 5px;font-size:13px;font-weight:600;letter-spacing:-.015em;color:#29372D}
.tbm-work p{margin:0;font-size:11px;line-height:1.55;color:#728378}.tbm-work-control{margin-top:7px!important;color:#4C6152!important}
.tbm-state{font-size:10px;padding:4px 8px;border-radius:5px;background:#F8F1E5;color:#926D39;white-space:nowrap}.tbm-state.ok{background:#E9F2E9;color:#477651}
.tbm-callout{padding:15px 17px;background:#F3F7F2;border:1px solid #E2EAE0;border-radius:7px;color:#405B47;font-size:12px;line-height:1.65;margin-top:14px}
.tbm-callout strong{font-weight:600;color:#2A4632}
.tbm-callout ul{margin:7px 0 0;padding-left:18px}.tbm-callout li{margin:3px 0}
.tbm-ready{display:flex;align-items:center;gap:12px;border:1px solid #CADFCB;background:#F4F9F3;padding:14px 17px;border-radius:8px;margin:20px 0 10px}
.tbm-ready b{font-weight:620;color:#31563B}.tbm-ready span{color:#698272;font-size:11px}
.tbm-muted{font-size:11px;color:#829187;line-height:1.65}
@media(max-width:640px){.tbm-work{grid-template-columns:54px minmax(0,1fr);gap:10px}.tbm-state{grid-column:2;width:max-content}.tbm-section{display:block}.tbm-section span{display:block;margin-top:3px}}
</style>""", unsafe_allow_html=True)


def show_tbm_dashboard() -> None:
    _styles()
    _brief_styles()
    plan: WorkPlan | None = st.session_state.get("field_plan")
    st.markdown(
        '<div class="field-hero"><div><div class="field-kicker">SAFETY ATLAS / TOOLBOX MEETING</div>'
        '<h1>TBM 브리핑</h1>'
        f'<p class="field-hero-site">{escape(plan.site) if plan else "현장 계획을 연결하세요"}</p>'
        '<p>확인한 작업과 남은 조치를 한 장으로 정리해 작업자에게 전달하세요.</p></div>'
        f'<span class="field-date"><small>오늘 기준</small>{today_korea():%Y.%m.%d}</span></div>',
        unsafe_allow_html=True,
    )
    if plan is None:
        st.info("작업계획을 등록하면 날짜별 브리핑 초안이 자동으로 생성됩니다.")
        if st.button("오늘의 작업에서 계획 등록", type="primary", key="tbm_open_plan"):
            _go_field()
        return

    days = sorted({item.day for item in plan.items})
    if st.session_state.get("tbm_available_days") != tuple(days):
        st.session_state["tbm_available_days"] = tuple(days)
        if st.session_state.get("tbm_day") not in days:
            today = today_korea()
            st.session_state["tbm_day"] = st.session_state.get("field_day") if st.session_state.get("field_day") in days else (today if today in days else days[0])
    day = st.selectbox("브리핑 날짜", days, format_func=lambda value: f"{value:%Y.%m.%d} ({'월화수목금토일'[value.weekday()]})", key="tbm_day")
    items = daily_items(plan, day)
    actions: tuple[FieldAction, ...] = tuple(st.session_state.get("field_actions", ()))
    reviews: dict = st.session_state.get("field_reviews", {})
    related = daily_actions(plan, day, actions)
    open_actions = sorted(
        (action for action in related if action.status == "open"),
        key=lambda action: action.due_at,
    )
    pending = [item for item in items if reviews.get(item.work_id, {}).get("status") != "확인 완료"]
    changed = [action for action in related if action.needs_review]
    overlaps = overlapping_pairs(plan.items, day)
    weather_location = st.session_state.get("field_weather_location")
    forecast = weather_for_day(day) if weather_location else None
    weather_text = ""
    if forecast is not None:
        weather_text = forecast_summary(weather_location, forecast)
        weather_notes = work_weather_notes(tuple(item.activity for item in items), forecast)
        if weather_notes:
            weather_text += " · 확인: " + " / ".join(weather_notes)
    elif weather_location:
        weather_text = (
            f"{weather_location.region} {weather_location.name} · {day:%m.%d} 예보 확인 불가 · "
            "현장 기상과 기상청 특보 직접 확인"
        )
    else:
        weather_text = "예보 위치 미연결 · 현장 기상과 기상청 특보 직접 확인"
    records: dict[str, tuple[TbmRecord, ...]] = st.session_state.setdefault("field_tbm_records", {})
    history = records.get(day.isoformat(), ())
    deliveries: dict[str, tuple[TbmDelivery, ...]] = st.session_state.setdefault("field_tbm_deliveries", {})
    delivery_history = deliveries.get(day.isoformat(), ())
    revisions = tuple(st.session_state.get("field_revisions", ()))
    revision_token = day_revision_token(revisions, day)
    fingerprint = brief_fingerprint(plan, day, actions, reviews, weather_text, revision_token)
    current = history[-1] if history and history[-1].fingerprint == fingerprint else None
    current_delivery = next((entry for entry in reversed(delivery_history) if current and entry.confirmation_at == current.confirmed_at and entry.fingerprint == current.fingerprint), None)
    stale = bool(history and current is None)

    st.markdown(
        '<div class="field-metrics action-metrics">'
        f'<div class="field-metric"><span>예정 작업</span><strong>{len(items)}</strong><small>건</small></div>'
        f'<div class="field-metric"><span>현장 확인 필요</span><strong>{len(pending)}</strong><small>건</small></div>'
        f'<div class="field-metric"><span>동시 작업</span><strong>{len(overlaps)}</strong><small>쌍</small></div>'
        f'<div class="field-metric"><span>미완료 조치</span><strong>{len(open_actions)}</strong><small>건</small></div>'
        '</div>', unsafe_allow_html=True,
    )
    if current:
        st.markdown(
            f'<div class="tbm-ready"><b>{"TBM 진행 기록 완료" if current_delivery else "관리자 확인 완료"}</b>'
            f'<span>{escape(current.confirmed_by)} · {current.confirmed_at:%Y.%m.%d %H:%M} · 공유 대상 {escape(current.audience)}</span></div>',
            unsafe_allow_html=True,
        )
    elif stale:
        st.warning("확인 이후 계획·조치·검토 기록이 바뀌었습니다. 현재 내용을 다시 확인하고 브리핑을 갱신하세요.")
    else:
        st.caption("현재 상태: 확인 전 초안 · 작업별 현장 확인을 마치면 브리핑을 확정할 수 있습니다.")
    st.markdown(f'<div class="tbm-callout"><strong>현장 기상 확인</strong><br>{escape(weather_text)}</div>', unsafe_allow_html=True)

    st.markdown('<div class="tbm-section"><h2>작업 순서와 시작 전 확인</h2><span>PLAN / REVIEW</span></div>', unsafe_allow_html=True)
    work_rows = []
    for item in items:
        review = reviews.get(item.work_id, {})
        done = review.get("status") == "확인 완료"
        work_rows.append(
            '<div class="tbm-work">'
            f'<div class="tbm-work-time">{item.start:%H:%M}<small>{item.end:%H:%M}</small></div>'
            f'<div><h3>{escape(item.activity)}</h3>'
            f'<p>{escape(item.area)} · {escape(item.location or "세부 위치 미입력")} · {escape(item.contractor or "업체 미입력")}</p>'
            f'<p class="tbm-work-control">{escape(item.follow_up or item.planned_controls or "작업 시작 전 현장 조건 확인")}</p></div>'
            f'<span class="tbm-state {"ok" if done else ""}">{"확인 완료" if done else "현장 확인 필요"}</span>'
            '</div>'
        )
    st.markdown("".join(work_rows), unsafe_allow_html=True)

    left, right = st.columns(2, gap="medium")
    with left:
        st.markdown('<div class="tbm-section"><h2>동시 작업 조정</h2><span>INTERFACES</span></div>', unsafe_allow_html=True)
        if overlaps:
            lines = "".join(
                f'<li>{escape(a.activity)} / {escape(b.activity)} · {escape(a.area)}</li>'
                for a, b in overlaps
            )
            st.markdown(f'<div class="tbm-callout"><strong>작업 시간과 구역이 겹칩니다</strong><ul>{lines}</ul><div>동선과 간섭 여부를 현장에서 확인하세요.</div></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="tbm-callout">같은 구역의 시간 중복 후보가 없습니다.</div>', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="tbm-section"><h2>남은 조치</h2><span>OPEN ACTIONS</span></div>', unsafe_allow_html=True)
        if open_actions:
            lines = "".join(
                f'<li>{escape(action.description)}{(" · 계획 변경 재확인" if action.needs_review else "")} · {escape(action.assignee)} · {action.due_at:%m.%d %H:%M}</li>'
                for action in open_actions
            )
            st.markdown(f'<div class="tbm-callout"><strong>담당자와 기한 확인</strong><ul>{lines}</ul></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="tbm-callout">등록된 미완료 조치가 없습니다.</div>', unsafe_allow_html=True)

    st.markdown('<div class="tbm-section"><h2>관리자 확인과 공유</h2><span>CONFIRM / EXPORT</span></div>', unsafe_allow_html=True)
    if pending or changed:
        reasons = []
        if pending:
            reasons.append(f"현장 확인이 끝나지 않은 작업 {len(pending)}건")
        if changed:
            reasons.append(f"계획 변경으로 재확인이 필요한 조치 {len(changed)}건")
        st.info(" · ".join(reasons) + "을 확인한 뒤 브리핑을 확정하세요.")
        if st.button("오늘의 작업에서 확인", key="tbm_review_work"):
            st.session_state["field_day"] = day
            _go_field()
    with st.form("tbm_confirm_form"):
        form_left, form_right = st.columns(2)
        with form_left:
            confirmed_by = st.text_input("진행자 *", value=current.confirmed_by if current else "", max_chars=100)
        with form_right:
            audience = st.text_input("공유 대상 *", value=current.audience if current else "", placeholder="예: A동 오전 작업자", max_chars=200)
        note = st.text_area("전달 사항", value=current.note if current else "", placeholder="현장에서 추가로 확인한 사항을 적으세요.", max_chars=2000)
        submitted = st.form_submit_button("현재 내용 확인 완료", type="primary", disabled=bool(pending or changed))
    if submitted:
        try:
            record = confirm_brief(plan, day, actions, reviews, confirmed_by, audience, note, weather_text, revision_token)
        except ValueError as exc:
            st.error(str(exc))
        else:
            records[day.isoformat()] = (*history, record)
            st.rerun()

    if current:
        with st.expander("TBM 진행 기록 남기기", expanded=current_delivery is None):
            if current_delivery:
                st.caption(f"진행 {current_delivery.delivered_by} · 참석 {current_delivery.attendee_count}명 · {current_delivery.delivered_at:%Y.%m.%d %H:%M}")
            with st.form(f"tbm_delivery_{current.confirmed_at.isoformat()}"):
                delivered_by = st.text_input("실제 진행자 *", value=current.confirmed_by, max_chars=100)
                attendee_count = st.number_input("참석 인원 *", min_value=1, max_value=10000, value=1, step=1)
                delivery_note = st.text_area("질문·변경 사항", placeholder="없으면 비워둘 수 있습니다.", max_chars=2000)
                acknowledged = st.checkbox("작업자에게 확인 사항을 전달하고 질문을 확인했습니다.")
                delivery_submitted = st.form_submit_button("TBM 진행 기록 저장", type="primary")
            if delivery_submitted:
                if not acknowledged:
                    st.error("전달과 질문 확인 후 기록하세요.")
                else:
                    try:
                        delivery = record_delivery(current, delivered_by, int(attendee_count), delivery_note)
                    except ValueError as exc:
                        st.error(str(exc))
                    else:
                        deliveries[day.isoformat()] = (*delivery_history, delivery)
                        st.rerun()

    st.download_button(
        "확인본 내려받기 (.html)" if current else "확인 전 초안 내려받기 (.html)",
        data=briefing_html(plan, day, actions, current, reviews, weather_text, current_delivery),
        file_name=f"TBM_{'확인본' if current else '초안'}_{day:%Y%m%d}.html",
        mime="text/html",
        key="tbm_download",
        width="stretch",
    )
    share_text = briefing_text(plan, day, actions, current, reviews, weather_text, current_delivery)
    with st.expander("작업자 공유용 텍스트", expanded=False):
        st.caption("확인본인지 초안인지 첫 줄에 표시됩니다. 현장 확인 후 필요한 내용을 복사해 공유하세요.")
        st.code(share_text, language=None)
        st.download_button(
            "텍스트 파일 받기", share_text.encode("utf-8-sig"),
            file_name=f"TBM_{'확인본' if current else '초안'}_{day:%Y%m%d}.txt",
            mime="text/plain", key="tbm_download_text",
        )
    st.markdown('<div class="tbm-muted">HTML 파일을 열어 인쇄하거나 PDF로 저장할 수 있습니다. 공유 전 실제 작업 조건을 다시 확인하세요.</div>', unsafe_allow_html=True)
    if history:
        with st.expander(f"이 날짜의 확인 기록 {len(history)}건"):
            for record in reversed(history):
                label = "현재 확인" if current and record.confirmed_at == current.confirmed_at else "이전 확인 내용"
                delivered = any(entry.confirmation_at == record.confirmed_at and entry.fingerprint == record.fingerprint for entry in delivery_history)
                st.text(f"{record.confirmed_at:%Y.%m.%d %H:%M} · {record.confirmed_by} · {label} · {'전달 기록 있음' if delivered else '전달 기록 없음'}")
                st.caption(f"공유 대상 {record.audience}" + (f" · {record.note}" if record.note else ""))
    st.caption("브리핑 확인 기록은 현재 브라우저 세션에 보관됩니다. 기록 백업에서 JSON 파일로 내려받을 수 있습니다.")
