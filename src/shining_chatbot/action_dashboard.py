"""Manager-facing follow-up register linked to planned work."""

from __future__ import annotations

from datetime import date, datetime
from html import escape

import streamlit as st

from shining_chatbot.action_data import FieldAction, finish_action, reopen_action
from shining_chatbot.business_time import now_korea, today_korea
from shining_chatbot.field_dashboard import _styles
from shining_chatbot.work_plan import WorkPlan


def _save_action(updated: FieldAction) -> None:
    st.session_state["field_actions"] = tuple(
        updated if action.action_id == updated.action_id else action
        for action in st.session_state.get("field_actions", ())
    )


def show_action_dashboard() -> None:
    _styles()
    plan: WorkPlan | None = st.session_state.get("field_plan")
    site = escape(plan.site) if plan else "현장 계획을 연결하세요"
    st.markdown(
        '<div class="field-hero"><div><div class="field-kicker">SAFETY ATLAS / ACTION REGISTER</div>'
        f'<h1>조치 현황</h1><p class="field-hero-site">{site}</p>'
        '<p>담당자와 기한을 확인하고 남은 조치를 마무리하세요.</p></div>'
        f'<span class="field-date"><small>오늘 기준</small>{today_korea():%Y.%m.%d}</span></div>',
        unsafe_allow_html=True,
    )
    if plan is None:
        st.info("작업계획을 먼저 등록하면 작업별 조치를 지정할 수 있습니다.")
        if st.button("오늘의 작업으로 이동"):
            st.session_state["view"] = "field"
            st.query_params["page"] = "field"
            st.rerun()
        return
    actions: tuple[FieldAction, ...] = tuple(st.session_state.get("field_actions", ()))
    now = now_korea()
    open_actions = [action for action in actions if action.status == "open"]
    overdue = [action for action in open_actions if action.due_at < now]
    due_today = [action for action in open_actions if action.due_at.date() == now.date()]
    completed = [action for action in actions if action.status == "done"]
    st.markdown(
        '<div class="field-metrics action-metrics">'
        f'<div class="field-metric"><span>미완료 조치</span><strong>{len(open_actions)}</strong><small>건</small></div>'
        f'<div class="field-metric"><span>기한 지남</span><strong>{len(overdue)}</strong><small>건</small></div>'
        f'<div class="field-metric"><span>오늘 기한</span><strong>{len(due_today)}</strong><small>건</small></div>'
        f'<div class="field-metric"><span>완료 기록</span><strong>{len(completed)}</strong><small>건</small></div>'
        '</div>', unsafe_allow_html=True,
    )
    if not actions:
        st.markdown(
            '<div class="field-panel"><div class="field-panel-title">등록된 조치가 없습니다</div>'
            '<p class="field-sub">오늘의 작업에서 작업을 선택해 담당자와 완료 기한이 있는 조치를 등록하세요.</p></div>',
            unsafe_allow_html=True,
        )
        return

    work_by_id = {item.work_id: item for item in plan.items}
    filter_label = st.radio("조회 상태", ["미완료", "전체", "완료"], horizontal=True, key="field_action_filter")
    visible = (
        open_actions if filter_label == "미완료" else completed if filter_label == "완료" else list(actions)
    )
    visible.sort(key=lambda action: (action.status == "done", action.due_at, action.action_id))
    if not visible:
        st.info("선택한 상태의 조치가 없습니다.")
        return
    rows = []
    for action in visible:
        work = work_by_id.get(action.work_id)
        name = work.activity if work else "계획에서 제외된 작업"
        late = action.status == "open" and action.due_at < now
        status = "재확인" if action.needs_review else "기한 지남" if late else "완료" if action.status == "done" else "대기"
        rows.append(
            '<div class="action-row">'
            f'<span class="action-due">{action.due_at:%m.%d}<small>{action.due_at:%H:%M}</small></span>'
            f'<div><div class="action-name">{escape(action.description)}</div>'
            f'<div class="action-context">{escape(name)} · {escape(action.assignee)}</div></div>'
            f'<span class="action-state {"late" if late or action.needs_review else "done" if action.status == "done" else ""}">{status}</span>'
            '</div>'
        )
    st.markdown(
        '<div class="action-list"><div class="field-panel-title">조치 목록</div>' + "".join(rows) + '</div>',
        unsafe_allow_html=True,
    )
    labels = {
        f"{action.due_at:%m.%d %H:%M} · {action.description} ({action.action_id})": action
        for action in visible
    }
    selected = st.selectbox("자세히 볼 조치", list(labels), key="field_selected_action")
    action = labels[selected]
    work = work_by_id.get(action.work_id)
    with st.container(border=True):
        st.markdown('<div class="field-kicker">ACTION DETAIL / ' + escape(action.action_id) + '</div>', unsafe_allow_html=True)
        st.subheader(action.description)
        st.caption(
            f"연결 작업: {work.activity if work else '계획에서 제외된 작업'} · "
            f"담당 {action.assignee} · 기한 {action.due_at:%Y.%m.%d %H:%M}"
        )
        if action.needs_review:
            st.warning("연결된 작업계획이 바뀌거나 제외됐습니다. 현재 조치 내용을 다시 확인하세요.")
        if action.status == "open":
            with st.form(f"complete_{action.action_id}"):
                actor = st.text_input("완료 확인자 *", max_chars=100, key=f"complete_actor_{action.action_id}")
                note = st.text_area("실제 완료 내용 *", max_chars=2000, key=f"complete_note_{action.action_id}")
                completed_click = st.form_submit_button("완료 기록", type="primary")
            if completed_click:
                try:
                    _save_action(finish_action(action, actor, note))
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.rerun()
        else:
            with st.form(f"reopen_{action.action_id}"):
                actor = st.text_input("변경자 *", max_chars=100, key=f"reopen_actor_{action.action_id}")
                reason = st.text_area("다시 연 이유 *", max_chars=2000, key=f"reopen_reason_{action.action_id}")
                reopened_click = st.form_submit_button("완료 취소 · 재개")
            if reopened_click:
                try:
                    _save_action(reopen_action(action, actor, reason))
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.rerun()
        with st.expander(f"변경 기록 {len(action.events)}건"):
            for event in reversed(action.events):
                st.text(f"{event.get('at', '')} · {event.get('actor', '')}")
                st.caption(event.get("note", ""))
    st.caption("조치와 변경 이력은 현재 브라우저 세션에 보관됩니다. 운영 기록으로 사용하려면 접근 권한이 있는 영구 저장소가 필요합니다.")
