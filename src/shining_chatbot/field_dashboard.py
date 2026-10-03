"""Today's work page for field managers."""

from __future__ import annotations

from datetime import date, datetime, time
from hashlib import sha256
from html import escape
from pathlib import Path
from uuid import uuid4

import pandas as pd
import streamlit as st

from shining_chatbot.action_data import FieldAction, flag_changed_work, new_action
from shining_chatbot.business_time import now_korea, today_korea
from shining_chatbot.case_summary import SIF_SOURCE_URL, local_cases_available, summarize_cases
from shining_chatbot.field_state import export_backup, import_backup
from shining_chatbot.field_session import ONE_OFF_WIDGET_KEYS, clear_site_context
from shining_chatbot.plan_revision import day_revision_token, make_revision
from shining_chatbot.record_pattern import SEASONS, context_signals, season_index, summarize_records
from shining_chatbot.tbm_data import daily_actions
from shining_chatbot.work_plan import NoWorkConfirmation, WorkItem, WorkPlan, compare_plans, overlapping_pairs, read_work_plan
from shining_chatbot.weather_panel import show_weather_panel


SAMPLE = Path(__file__).parent / "static" / "sample_work_plan.xlsx"


def _styles() -> None:
    st.markdown("""<style>
.field-kicker{font:600 10px/1.4 var(--font-mono);letter-spacing:.08em;color:#638B73;margin:0 0 9px}
.field-hero{display:flex;justify-content:space-between;align-items:end;gap:18px;margin:0 0 16px;padding:26px 28px;border:1px solid #E1E7DF;border-radius:12px;background:linear-gradient(112deg,#FFFFFF 5%,#F7FAF5 70%,#EFF5EE 100%)}
.field-hero h1{font-size:clamp(29px,2.7vw,39px);font-weight:620;letter-spacing:-.045em;line-height:1.22;margin:0 0 9px;color:#252A27}
.field-hero p{font-size:12px;line-height:1.65;color:#748078;margin:0}
.field-hero .field-hero-site{font-size:13px;font-weight:560;color:#435B48;margin:0 0 3px}
.field-date{display:flex;flex-direction:column;gap:3px;color:#445E4B;font:600 12px var(--font-mono);white-space:nowrap;padding:9px 12px;border:1px solid #DCE6DB;border-radius:7px;background:#FFFFFFD9;text-align:right}
.field-date small{font:10px var(--font-ui);color:#69786D}
.st-key-field_actions{margin-bottom:18px}
.st-key-field_actions button{min-height:38px;border-radius:7px;font-size:11px;font-weight:550;letter-spacing:-.01em}
.st-key-field_actions [data-testid="stHorizontalBlock"]{gap:8px}
.field-pattern{display:flex;align-items:center;gap:14px;flex-wrap:wrap;background:#FAFBF9;border:1px solid #E2E9E0;border-radius:7px;padding:11px 15px;margin:0 0 17px;color:#667B69;font-size:11px}
.field-pattern strong{color:#31523B;font-weight:620}.field-pattern i{width:1px;height:15px;background:#DEE7DD}
.field-revision{display:flex;align-items:center;gap:13px;flex-wrap:wrap;padding:10px 14px;margin:0 0 12px;border:1px solid #E7EBE2;border-radius:7px;color:#68796C;background:#FBFCFA;font-size:11px}.field-revision strong{color:#354D3A;font-weight:610}.field-revision small{margin-left:auto;color:#6C796F;font-size:10px}
.field-no-work-confirm{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;padding:11px 14px;margin:0 0 8px;border:1px solid #DFE8DE;border-left:3px solid #7B987E;border-radius:7px;background:#F7FAF6;color:#5D705F;font-size:11px;line-height:1.5}
.field-no-work-confirm strong{color:#3B5940;font-weight:600}.field-no-work-confirm span{color:#6B796E;font-size:10px}
.field-panel{border:1px solid #E3E8E2;border-radius:11px;background:#fff;padding:20px 22px;margin:0 0 15px}
.field-panel-title{font-size:15px;font-weight:610;letter-spacing:-.025em;color:#273029;margin:0 0 6px}
.field-sub{font-size:12px;line-height:1.6;color:#7B857D;margin:0 0 16px}
.field-metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:0 0 17px}
.field-metric{background:#fff;border:1px solid #E3E8E2;border-radius:10px;padding:16px 18px;min-height:92px}
.field-metric span{display:block;color:#68746B;font-size:11px;margin-bottom:8px}
.field-metric strong{font-size:25px;line-height:1;font-weight:590;letter-spacing:-.04em;color:#273029}
.field-metric small{font-size:11px;color:#6D786F;margin-left:5px}
.field-metric .field-progress-track{height:4px;margin:10px 0 0;border-radius:4px;background:#EDF1EC;overflow:hidden}
.field-progress-track span{display:block;height:100%;margin:0!important;border-radius:4px;background:linear-gradient(90deg,#A7BBA9,#66876D);transition:width .2s ease}
.field-metric .field-progress-caption{display:block;margin:5px 0 0!important;color:#748177;font-size:10px;line-height:1.35}
.field-list{display:grid;gap:9px;margin:8px 0 20px}
.field-item{border:1px solid #E5E9E4;border-radius:9px;padding:14px 16px;background:#fff;display:grid;grid-template-columns:60px minmax(0,1fr) auto;gap:13px;align-items:start}
.field-item.selected{border-color:#94AF99;background:#F7FAF6;box-shadow:inset 3px 0 0 #75967D}
.field-time{font:600 12px/1.5 var(--font-mono);color:#4F6B57}
.field-name{font-size:13px;font-weight:600;line-height:1.45;color:#29332C}
.field-meta{font-size:11px;line-height:1.6;color:#69756C;margin-top:3px}
.field-status{font-size:10px;line-height:1.4;color:#765D38;background:#F5F0E5;border:1px solid #ECE2D0;border-radius:5px;padding:4px 7px;white-space:nowrap}
.field-status.ok{color:#54715B;background:#EDF3ED;border-color:#DBE8DB}
.field-note{border-left:2px solid #9BAB9D;background:#F4F7F3;padding:12px 15px;font-size:12px;line-height:1.65;color:#536158;margin:0 0 18px}
.field-detail{font-size:12px;line-height:1.7;color:#57635A}
.field-detail b{font-weight:600;color:#344239}
.field-muted{font-size:11px;color:#68746B;line-height:1.6}
.field-timeline{border:1px solid #E3E8E2;border-radius:10px;background:#fff;padding:16px 18px 17px;margin:0 0 18px}
.field-timeline-head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:17px}
.field-timeline-head span{font-size:13px;font-weight:600;color:#344238}
.field-timeline-head small{font-size:10px;color:#6D796F}
.field-timeline-axis,.field-timeline-row{display:grid;grid-template-columns:150px minmax(0,1fr);gap:13px;align-items:center}
.field-timeline-axis{margin-bottom:8px}.field-timeline-axis>div{position:relative;height:15px;margin-right:34px}
.field-timeline-axis span{position:absolute;top:0;transform:translateX(-50%);font:9px var(--font-mono);color:#9AA39B}
.field-timeline-row{min-height:35px;border-top:1px solid #F0F2EF}
.field-timeline-label{font-size:11px;color:#5F6A61;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.field-timeline-track{height:24px;position:relative;margin-right:34px}
.field-timeline-guide{position:absolute;top:0;bottom:0;border-left:1px solid #EFF1EE;pointer-events:none}
.field-timeline-bar{position:absolute;top:6px;height:12px;min-width:4px;border-radius:3px;background:linear-gradient(90deg,#A5B9A9,#78977D);outline-offset:3px;cursor:default;z-index:1;transition:height .18s,top .18s,filter .18s}
.field-timeline-bar.overlap{background:linear-gradient(90deg,#687F6E,#465D4C)}
.field-timeline-bar:hover,.field-timeline-bar:focus-visible{height:16px;top:4px;filter:brightness(.92)}
.field-timeline-tip{position:absolute;left:50%;bottom:calc(100% + 8px);transform:translate(-50%,4px);background:#27362B;color:white;padding:7px 9px;border-radius:6px;font-size:10px;line-height:1.4;white-space:nowrap;opacity:0;visibility:hidden;pointer-events:none;transition:opacity .15s,transform .15s;z-index:5}
.field-timeline-bar:hover .field-timeline-tip,.field-timeline-bar:focus-visible .field-timeline-tip{opacity:1;visibility:visible;transform:translate(-50%,0)}
.field-attention{border:1px solid #DDE6DC;border-radius:10px;background:#F5F8F4;padding:17px 20px;margin:0 0 17px}
.field-attention-head{font-size:13px;font-weight:610;color:#314336;margin:0 0 9px}
.field-attention-row{display:grid;grid-template-columns:48px minmax(0,1fr) auto;gap:12px;align-items:start;padding:9px 0;border-top:1px solid #E3EAE1}
.field-attention-time{font:11px var(--font-mono);color:#778E7C;margin-top:2px}
.field-attention-work{font-size:12px;font-weight:570;color:#37463A;line-height:1.5}
.field-attention-reason{font-size:11px;font-weight:400;color:#69786D;line-height:1.5;margin-top:2px}
.field-attention-owner{font-size:10px;color:#798A7D;white-space:nowrap;margin-top:2px}
.field-top-link{display:inline-flex;align-items:center;gap:5px;padding:7px 11px;border:1px solid #DAE2DA;border-radius:7px;background:#fff;color:#627968 !important;font-size:11px;text-decoration:none !important;margin:12px 0 4px}
.field-top-link:hover{background:#EEF4EE;border-color:#B6C8B8}
.field-case{border:1px solid #E2E8E1;border-radius:10px;background:#fff;padding:18px 20px;margin:0 0 17px}
.field-case-heading{display:flex;align-items:start;justify-content:space-between;gap:12px;margin-bottom:16px}
.field-case-kicker{font:600 10px var(--font-mono);letter-spacing:.08em;color:#58785F;margin-bottom:5px}
.field-case-title{font-size:14px;font-weight:610;color:#304035;letter-spacing:-.02em}
.field-case-sub{font-size:11px;line-height:1.55;color:#68746B;margin-top:4px}
.field-case-insight{font-size:11px;line-height:1.5;color:#536A59;background:#F3F7F2;border-radius:5px;padding:8px 10px;margin:-4px 0 12px}
.field-case-total{font:600 21px var(--font-mono);letter-spacing:-.035em;color:#314B36;white-space:nowrap}
.field-case-total small{font:10px var(--font-ui);color:#859187;margin-left:4px}
.field-case-row{display:grid;grid-template-columns:66px minmax(0,1fr) 36px;gap:10px;align-items:center;min-height:28px}
.field-case-label{font-size:11px;color:#626D63;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.field-case-track{height:10px;background:#F0F3EF;border-radius:3px;position:relative}
.field-case-fill{height:10px;min-width:3px;border-radius:3px;background:linear-gradient(90deg,#A6BCAA,#54765C);position:relative;transition:filter .18s,transform .18s;transform-origin:left center}
.field-case-row:hover .field-case-fill,.field-case-fill:focus-visible{filter:brightness(.86);transform:scaleY(1.3)}
.field-case-value{text-align:right;font:11px var(--font-mono);color:#405448}
.field-case-tip{position:absolute;left:0;bottom:calc(100% + 8px);padding:7px 9px;background:#28372C;color:#fff;border-radius:6px;font:10px/1.4 var(--font-ui);white-space:nowrap;opacity:0;visibility:hidden;transition:opacity .16s;z-index:4;pointer-events:none}
.field-case-row:hover .field-case-tip,.field-case-fill:focus-visible .field-case-tip{opacity:1;visibility:visible}
.field-case-foot{border-top:1px solid #EDF0EC;margin-top:13px;padding-top:10px;font-size:10px;line-height:1.55;color:#68756B}
.field-case-foot a{color:#587B60;text-decoration:underline;text-underline-offset:2px}
.action-metrics{grid-template-columns:repeat(4,1fr)}
.action-list{background:#fff;border:1px solid #E3E8E2;border-radius:10px;padding:17px 20px;margin:10px 0 18px}
.action-list .field-panel-title{margin-bottom:10px}
.action-row{display:grid;grid-template-columns:52px minmax(0,1fr) auto;gap:14px;align-items:center;border-top:1px solid #ECF0EB;padding:12px 1px}
.action-due{font:600 11px/1.35 var(--font-mono);color:#5D7462}
.action-due small{display:block;color:#718075;font-size:10px;margin-top:2px}
.action-name{font-size:12px;font-weight:580;line-height:1.45;color:#37433A}
.action-context{font-size:11px;line-height:1.5;color:#68746A;margin-top:3px}
.action-state{font-size:10px;padding:5px 8px;color:#5F7564;background:#EFF4EF;border:1px solid #DCE8DD;border-radius:5px;white-space:nowrap}
.action-state.late{color:#806642;background:#F8F3EA;border-color:#EADFCB}
.action-state.done{color:#78877B;background:#F2F5F1;border-color:#E6ECE5}
@media(max-width:760px){.field-hero{display:block;padding:20px}.field-date{display:inline-flex;margin-top:12px;text-align:left}.field-metrics{grid-template-columns:1fr}.field-item{grid-template-columns:48px minmax(0,1fr)}.field-status{grid-column:2;width:max-content}.field-panel{padding:17px}.st-key-field_actions [data-testid="stHorizontalBlock"]{flex-wrap:wrap}}
@media(max-width:900px){.action-metrics{grid-template-columns:repeat(2,1fr)}}
@media(max-width:760px){.action-row{grid-template-columns:44px minmax(0,1fr);gap:9px}.action-state{grid-column:2;width:max-content}.action-metrics{grid-template-columns:repeat(2,1fr)}}
@media(max-width:760px){.field-timeline-axis,.field-timeline-row{grid-template-columns:92px minmax(0,1fr);gap:8px}.field-timeline-head small{display:none}.field-timeline-track,.field-timeline-axis>div{margin-right:18px}.field-timeline-tip{white-space:normal;min-width:130px}}
@media(max-width:760px){.field-attention-row{grid-template-columns:43px minmax(0,1fr)}.field-attention-owner{grid-column:2}}
@media(prefers-reduced-motion:reduce){.field-timeline-bar,.field-timeline-tip,.field-case-fill,.field-case-tip{transition:none !important}}
</style>""", unsafe_allow_html=True)


def _load_upload(content: bytes) -> WorkPlan | None:
    token = sha256(content).hexdigest()
    if st.session_state.get("field_upload_token") != token:
        st.session_state["field_upload_token"] = token
        st.session_state.pop("field_candidate", None)
        try:
            st.session_state["field_candidate"] = read_work_plan(content)
            candidate = st.session_state["field_candidate"]
            st.session_state["field_candidate_site"] = (
                candidate.site if candidate.site != "현장명 미입력"
                else (st.session_state.get("field_plan").site if st.session_state.get("field_plan") else "")
            )
        except ValueError as exc:
            st.error(str(exc))
    return st.session_state.get("field_candidate")


def _preview(plan: WorkPlan) -> None:
    st.markdown('<div class="field-panel-title">업로드 내용 확인</div>', unsafe_allow_html=True)
    st.caption(f"작업 {len(plan.items)}건 · 제외·확인 항목 {len(plan.issues)}건")
    site_name = st.text_input("현장명 확인 *", key="field_candidate_site", max_chars=200).strip()
    if not site_name:
        st.warning("현장명을 입력해야 계획을 적용할 수 있습니다.")
    current: WorkPlan | None = st.session_state.get("field_plan")
    confirmations = current.no_work_confirmations if current is not None and current.site == site_name else ()
    plan = WorkPlan(site_name, plan.items, plan.issues, confirmations)
    same_site = current is not None and current.site == plan.site
    manual_items = (
        tuple(item for item in current.items if item.sheet == "화면 입력" and item.work_id not in {new.work_id for new in plan.items})
        if same_site else ()
    )
    effective = WorkPlan(
        plan.site,
        tuple(sorted((*plan.items, *manual_items), key=lambda item: (item.day, item.start, item.work_id))),
        plan.issues,
        plan.no_work_confirmations,
    )
    changes = compare_plans(current, effective) if same_site else None
    if current and site_name and not same_site:
        st.warning("현장명이 다릅니다. 적용하면 현재 현장의 계획과 확인 기록을 새 현장으로 교체합니다.")
    if changes is not None:
        st.markdown(
            f"**수정본 비교** · 추가 {len(changes.added)}건 · 변경 {len(changes.changed)}건 · "
            f"제외 {len(changes.removed)}건 · 동일 {len(changes.unchanged)}건"
        )
        if changes.added or changes.changed or changes.removed:
            st.caption(
                "추가: " + (", ".join(changes.added) or "없음") + " · "
                "변경: " + (", ".join(changes.changed) or "없음") + " · "
                "제외: " + (", ".join(changes.removed) or "없음")
            )
            st.warning("변경된 작업의 현장 확인 기록은 다시 미확인 상태가 됩니다. 내용이 같은 작업의 기록은 유지됩니다.")
        if changes.changed:
            old_items = {item.work_id: item for item in current.items}
            new_items = {item.work_id: item for item in effective.items}
            labels = {
                "day": "작업일", "start": "시작", "end": "종료", "area": "동/구역",
                "location": "세부 위치", "trade": "공종", "activity": "작업 내용",
                "equipment": "주요 장비", "people": "인원", "contractor": "협력업체",
                "owner": "작업책임자", "planned_controls": "계획된 안전조치",
                "follow_up": "추가 확인", "review_status": "검토 상태", "change_note": "변경 사항",
            }
            def shown(value: object) -> str:
                return "—" if value is None or value == "" else str(value)
            differences = [
                {"작업ID": work_id, "항목": label, "이전": shown(getattr(old_items[work_id], field)),
                 "수정본": shown(getattr(new_items[work_id], field))}
                for work_id in changes.changed
                for field, label in labels.items()
                if getattr(old_items[work_id], field) != getattr(new_items[work_id], field)
            ]
            with st.expander(f"변경 상세 {len(differences)}개 필드"):
                st.dataframe(pd.DataFrame(differences), hide_index=True, width="stretch")
        if manual_items:
            st.caption(f"화면에서 추가한 일회성 작업 {len(manual_items)}건은 계속 유지합니다.")
    if plan.issues:
        for issue in plan.issues:
            st.warning(issue)
    preview = pd.DataFrame([
        {
            "날짜": item.day.isoformat(), "시간": f"{item.start:%H:%M}–{item.end:%H:%M}",
            "작업": item.activity, "구역": item.area, "위치": item.location,
            "장비": item.equipment or "미입력", "검토 상태": item.review_status or "미입력",
            "원문": f"{item.sheet} {item.row}행",
        }
        for item in plan.items
    ])
    st.dataframe(preview, hide_index=True, width="stretch", height=min(360, 39 * len(preview) + 42))
    st.caption("원문에 적힌 계획을 가져옵니다. ‘검토필요’ 작업도 일정에 표시되며 현장 확인 전 완료 처리되지 않습니다.")
    if st.button("이 계획 적용", type="primary", key="apply_field_plan", disabled=not site_name):
        prior_reviews = st.session_state.get("field_reviews", {})
        source_name = st.session_state.get("field_candidate_name", "작업계획서")
        revision = make_revision(current, effective, source_name)
        prior_revisions = tuple(st.session_state.get("field_revisions", ())) if same_site else ()
        if not same_site:
            clear_site_context(st.session_state)
            st.session_state["field_day"] = today_korea()
        st.session_state.pop("field_plan_days", None)
        st.session_state["field_revisions"] = (*prior_revisions, revision) if revision.entries else prior_revisions
        st.session_state["field_plan"] = effective
        st.session_state["field_reviews"] = (
            {work_id: review for work_id, review in prior_reviews.items() if work_id in changes.unchanged}
            if changes and same_site else {}
        )
        if changes and same_site:
            st.session_state["field_actions"] = flag_changed_work(
                tuple(st.session_state.get("field_actions", ())),
                set(changes.changed) | set(changes.removed),
            )
        elif current is not None:
            st.session_state["field_actions"] = ()
        st.session_state["field_applied_token"] = st.session_state.get("field_upload_token")
        st.session_state["field_plan_applied_at"] = now_korea().strftime("%Y.%m.%d %H:%M")
        st.session_state["field_plan_name"] = source_name
        st.session_state["field_panel_mode"] = None
        st.rerun()


def _add_one_off(plan: WorkPlan | None) -> None:
    with st.container(border=True):
        with st.form("one_off_form", clear_on_submit=True):
            if plan is None:
                site = st.text_input("현장명", placeholder="예: 가상 온누리 아파트 신축공사", max_chars=200, key="one_off_site")
            else:
                site = plan.site
            activity = st.text_input("작업 내용 *", placeholder="예: 지하 1층 배수 배관 보수", max_chars=300, key="one_off_activity")
            first, second = st.columns(2)
            with first:
                day = st.date_input("작업일 *", value=today_korea(), key="one_off_day")
                start = st.time_input("시작 시간 *", value=time(9, 0), key="one_off_start")
            with second:
                area = st.text_input("동/구역 *", placeholder="예: B동", max_chars=150, key="one_off_area")
                end = st.time_input("종료 시간 *", value=time(10, 0), key="one_off_end")
            with st.expander("세부 정보 (선택) · 장비, 담당자, 계획 조치"):
                left, right = st.columns(2)
                with left:
                    location = st.text_input("세부 위치", placeholder="예: 지하 1층 펌프실", max_chars=300, key="one_off_location")
                    equipment = st.text_input("주요 장비", placeholder="미정이면 비워 두세요", max_chars=200, key="one_off_equipment")
                    contractor = st.text_input("협력업체", placeholder="해당 시 입력", max_chars=150, key="one_off_contractor")
                with right:
                    owner = st.text_input("작업책임자", placeholder="확인할 담당자", max_chars=100, key="one_off_owner")
                    people_text = st.text_input("작업 인원", placeholder="예: 4명 · 모르면 비워 두세요", max_chars=5, key="one_off_people")
                planned_controls = st.text_area("계획된 안전조치", placeholder="계획 또는 작업허가서에 적힌 조치를 입력하세요.", max_chars=2000, key="one_off_controls")
                follow_up = st.text_area("시작 전 확인", placeholder="작업구역·장비·보호구 등 현장에서 확인할 항목", max_chars=2000, key="one_off_follow_up")
            submitted = st.form_submit_button("작업 목록에 추가", type="primary")
        if submitted:
            limits = (
                ("현장명", site if plan is None else plan.site, 200),
                ("작업 내용", activity, 300), ("동/구역", area, 150),
                ("세부 위치", location, 300), ("주요 장비", equipment, 200),
                ("협력업체", contractor, 150), ("작업책임자", owner, 100),
                ("계획된 안전조치", planned_controls, 2000), ("시작 전 확인", follow_up, 2000),
            )
            too_long = next(((label, maximum) for label, value, maximum in limits if len(value.strip()) > maximum), None)
            if not activity.strip() or not area.strip() or (plan is None and not site.strip()):
                st.error("현장명, 작업 내용, 동/구역을 입력하세요.")
            elif end <= start:
                st.error("종료 시간은 시작 시간보다 늦어야 합니다.")
            elif too_long:
                st.error(f"{too_long[0]}은 {too_long[1]}자 이내로 입력하세요.")
            elif people_text.strip() and (
                not people_text.strip().isdigit() or len(people_text.strip()) > 5
                or not 1 <= int(people_text.strip()) <= 10000
            ):
                st.error("작업 인원은 1~10,000 사이의 정수로 입력하세요.")
            else:
                if plan is None:
                    clear_site_context(st.session_state, preserve=ONE_OFF_WIDGET_KEYS)
                item = WorkItem(
                    f"ADHOC-{uuid4().hex[:7].upper()}", day, start, end, area.strip(),
                    location.strip(), "일회성", activity.strip(), equipment.strip(),
                    int(people_text.strip()) if people_text.strip() else None,
                    contractor.strip(), owner.strip(), planned_controls.strip(),
                    follow_up.strip() or "작업 구역·장비·보호구와 작업 조건을 현장에서 확인하세요.",
                    "검토필요", "빠른 등록", "화면 입력", 0,
                )
                updated = WorkPlan(
                    site.strip(),
                    tuple(sorted((*plan.items, item), key=lambda work: (work.day, work.start))) if plan else (item,),
                    plan.issues if plan else (),
                    plan.no_work_confirmations if plan else (),
                )
                st.session_state["field_plan"] = updated
                revision = make_revision(plan, updated, "일회성 작업 입력")
                st.session_state["field_revisions"] = (*st.session_state.get("field_revisions", ()), revision)
                if plan is None:
                    st.session_state["field_plan_name"] = "화면에서 추가한 작업"
                st.session_state["field_panel_mode"] = None
                st.session_state.pop("field_plan_days", None)
                st.session_state["field_day"] = day
                st.rerun()


def _backup_tools(plan: WorkPlan | None) -> None:
    with st.container(border=True):
        st.caption("계획·작업 없음 확인·조치·TBM 기록과 예보 위치를 JSON 파일로 보관합니다. 사고 경향에 연결한 CSV 원본은 별도로 보관하세요. 파일에는 업체명·담당자 등 현장 정보가 들어 있습니다.")
        if plan is not None:
            try:
                data = export_backup(
                    plan, st.session_state.get("field_reviews", {}),
                    st.session_state.get("field_plan_name", "작업계획서"),
                    st.session_state.get("field_plan_applied_at", ""),
                    tuple(st.session_state.get("field_actions", ())),
                    st.session_state.get("field_tbm_records", {}),
                    st.session_state.get("field_weather_location"),
                    st.session_state.get("field_tbm_deliveries", {}),
                    tuple(st.session_state.get("field_revisions", ())),
                )
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.download_button(
                    "현재 작업과 확인 기록 백업", data=data,
                    file_name=f"현장작업_백업_{today_korea():%Y%m%d}.json", mime="application/json",
                    key="field_backup_download",
                )
        backup = st.file_uploader("이전에 내려받은 백업 복원 (.json)", type="json", key="field_backup_upload")
        if backup is not None:
            token = sha256(backup.getvalue()).hexdigest()
            if token != st.session_state.get("field_restored_token"):
                try:
                    restored, reviews, actions, tbm_records, tbm_deliveries, revisions, weather_location, name, applied_at = import_backup(backup.getvalue())
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.caption(f"{restored.site} · 작업 {len(restored.items)}건 · 작업 없음 확인 {len(restored.no_work_confirmations)}건 · 확인 기록 {len(reviews)}건 · 조치 {len(actions)}건 · TBM 확인 {sum(map(len, tbm_records.values()))}건 · 진행 {sum(map(len, tbm_deliveries.values()))}건 · 계획 변경 {len(revisions)}건")
                    if st.button("이 백업 복원", key="field_restore_button"):
                        clear_site_context(st.session_state, preserve=("field_backup_upload",))
                        st.session_state["field_plan"] = restored
                        st.session_state["field_reviews"] = reviews
                        st.session_state["field_actions"] = actions
                        st.session_state["field_tbm_records"] = tbm_records
                        st.session_state["field_tbm_deliveries"] = tbm_deliveries
                        st.session_state["field_revisions"] = revisions
                        st.session_state["field_weather_location"] = weather_location
                        st.session_state["field_plan_name"] = name
                        st.session_state["field_plan_applied_at"] = applied_at
                        st.session_state["field_restored_token"] = token
                        st.session_state["field_applied_token"] = st.session_state.get("field_upload_token")
                        st.session_state["field_panel_mode"] = None
                        st.session_state.pop("field_plan_days", None)
                        st.session_state["field_day"] = today_korea()
                        st.rerun()


def _timeline(daily: list[WorkItem], pairs: tuple[tuple[WorkItem, WorkItem], ...]) -> None:
    if not daily:
        return
    start_hour = min(item.start.hour for item in daily)
    end_hour = max(item.end.hour + (item.end.minute > 0) for item in daily)
    end_hour = max(end_hour, start_hour + 2)
    span = (end_hour - start_hour) * 60
    overlapping = {item.work_id for pair in pairs for item in pair}
    hours = list(range(start_hour, end_hour + 1, 2))
    if hours[-1] != end_hour:
        hours.append(end_hour)
    ticks = "".join(
        f'<span style="left:{(hour - start_hour) / (end_hour - start_hour) * 100:.2f}%">{hour:02d}:00</span>'
        for hour in hours
    )
    guides = "".join(
        f'<span class="field-timeline-guide" style="left:{(hour - start_hour) / (end_hour - start_hour) * 100:.2f}%"></span>'
        for hour in hours
    )
    rows = []
    for item in daily:
        offset = ((item.start.hour - start_hour) * 60 + item.start.minute) / span * 100
        duration = ((item.end.hour - item.start.hour) * 60 + item.end.minute - item.start.minute) / span * 100
        title = f"{item.activity} · {item.start:%H:%M}–{item.end:%H:%M} · {item.area}"
        rows.append(
            '<div class="field-timeline-row">'
            f'<span class="field-timeline-label">{escape(item.activity)}</span>'
            f'<div class="field-timeline-track">{guides}'
            f'<span class="field-timeline-bar {"overlap" if item.work_id in overlapping else ""}" '
            f'style="left:{offset:.2f}%;width:{duration:.2f}%" tabindex="0" role="img" aria-label="{escape(title, quote=True)}">'
            f'<span class="field-timeline-tip">{escape(title)}</span></span></div></div>'
        )
    st.markdown(
        '<div class="field-timeline"><div class="field-timeline-head"><span>작업 시간대</span>'
        '<small>진한 막대 · 같은 구역의 시간 중복 후보</small></div>'
        '<div class="field-timeline-axis"><span></span><div>' + ticks + '</div></div>'
        + "".join(rows) + '</div>', unsafe_allow_html=True,
    )


def _attention(
    plan: WorkPlan, daily: list[WorkItem], pairs: tuple[tuple[WorkItem, WorkItem], ...],
    reviews: dict, actions: tuple[FieldAction, ...],
) -> None:
    overlapping = {item.work_id for pair in pairs for item in pair}
    rows = []
    for item in daily:
        if reviews.get(item.work_id, {}).get("status") == "확인 완료":
            continue
        reasons = []
        if item.follow_up:
            reasons.append(item.follow_up)
        if not item.equipment:
            reasons.append("장비 미입력")
        if item.work_id in overlapping:
            reasons.append("같은 구역의 작업 시간 중복")
        if not item.owner:
            reasons.append("책임자 미입력")
        if not reasons:
            reasons.append("현장 확인 미완료")
        rows.append(
            '<div class="field-attention-row">'
            f'<span class="field-attention-time">{item.start:%H:%M}</span>'
            f'<div><div class="field-attention-work">{escape(item.activity)} · {escape(item.area)}</div>'
            f'<div class="field-attention-reason">{escape(" · ".join(reasons))}</div></div>'
            f'<span class="field-attention-owner">{escape(item.owner or "담당 미입력")}</span></div>'
        )
    selected_day = daily[0].day
    visible_actions = daily_actions(plan, selected_day, actions)
    visible_actions += tuple(
        action for action in actions
        if action.status == "open" and action.due_at.date() <= selected_day
        and action not in visible_actions
    )
    for action in sorted(
        (action for action in visible_actions if action.status == "open"),
        key=lambda action: action.due_at,
    ):
        late = action.due_at < now_korea()
        state = "계획 변경 · 재확인" if action.needs_review else "기한 지남" if late else "조치 대기"
        rows.append(
            '<div class="field-attention-row">'
            f'<span class="field-attention-time">{action.due_at:%H:%M}</span>'
            f'<div><div class="field-attention-work">{escape(action.description)}</div>'
            f'<div class="field-attention-reason">{state} · 기한 {action.due_at:%m.%d %H:%M}</div></div>'
            f'<span class="field-attention-owner">{escape(action.assignee)}</span></div>'
        )
    if rows:
        st.markdown(
            '<div class="field-attention"><div class="field-attention-head">지금 확인할 일</div>'
            + "".join(rows[:6]) + '</div>', unsafe_allow_html=True,
        )
        if len(rows) > 6:
            with st.expander(f"추가 확인 항목 {len(rows) - 6}건"):
                st.markdown('<div class="field-attention">' + "".join(rows[6:]) + '</div>', unsafe_allow_html=True)
    else:
        st.success("이 날짜의 현장 확인과 지정된 조치가 모두 완료로 기록됐습니다. 작업 조건이 바뀌면 다시 확인하세요.")


def _case_chart(item: WorkItem) -> None:
    if not local_cases_available():
        st.info("과거 사고사례 자료가 연결되지 않았습니다. 작업 일정과 현장 확인 내용은 계속 사용할 수 있습니다.")
        return
    try:
        summary = summarize_cases(item)
    except (OSError, ValueError, ImportError):
        st.warning("로컬 SIF 사례 파일을 읽지 못했습니다. SANUP-P 전처리 파일을 확인하세요.")
        return
    if summary is None:
        st.info("이 작업명·장비 키워드로 연결할 수 있는 건설업 SIF 사례가 없습니다. 사례 0건이나 안전함을 뜻하지 않습니다.")
        return
    maximum = max((count for _, count in summary.counts), default=1)
    rows = []
    for kind, count in summary.counts:
        rows.append(
            '<div class="field-case-row">'
            f'<span class="field-case-label">{escape(kind)}</span><div class="field-case-track">'
            f'<div class="field-case-fill" style="width:{count / maximum * 100:.1f}%" tabindex="0" '
            f'role="img" aria-label="{escape(kind, quote=True)} {count}건">'
            f'<span class="field-case-tip">{escape(kind)} · {count}건 / 키워드 {escape(summary.keyword)}</span>'
            f'</div></div><span class="field-case-value">{count}</span></div>'
        )
    insight = (
        f'<div class="field-case-insight">이 키워드 사례에서 가장 많이 기록된 유형: '
        f'{escape(summary.counts[0][0])} {summary.counts[0][1]}건</div>'
        if summary.counts else ""
    )
    st.markdown(
        '<div class="field-case"><div class="field-case-heading"><div>'
        '<div class="field-case-kicker">LOCAL SIF ARCHIVE / KEYWORD MATCH</div>'
        '<div class="field-case-title">작업 키워드가 포함된 사고사례 유형</div>'
        f'<div class="field-case-sub">{escape(item.activity)} · 검색어 “{escape(summary.keyword)}” · {escape(summary.field)}</div>'
        f'</div><div class="field-case-total">{summary.total:,}<small>기록 건수</small></div></div>'
        + insight + "".join(rows)
        + '<div class="field-case-foot">건설업 SIF 아카이브의 작업명 또는 기인물에 같은 단어가 들어간 기록입니다. '
        '유사도 평가나 오늘 사고 확률이 아닙니다. 사고유형 상위 5개만 표시합니다. · '
        f'<a href="{SIF_SOURCE_URL}" target="_blank" rel="noopener noreferrer">자료 출처 ↗</a></div></div>',
        unsafe_allow_html=True,
    )


def _select_field_day(day: date) -> None:
    st.session_state["field_day"] = day


def _show_record_context(day: date) -> None:
    incident_frame = st.session_state.get("field_incident_frame")
    if incident_frame is None:
        return
    pattern = summarize_records(incident_frame)
    weekday_label = "월화수목금토일"[day.weekday()]
    st.markdown(
        '<div class="field-pattern"><strong>연결한 사고 기록</strong>'
        f'<span>{escape(st.session_state.get("field_incident_scope", "범위 미입력"))}</span><i></i>'
        f'<span>{weekday_label}요일 기록 <strong>{pattern.weekdays[day.weekday()]}건</strong></span>'
        f'<span>{day.month}월 기록 <strong>{pattern.months[day.month - 1]}건</strong></span>'
        f'<span>{SEASONS[season_index(day.month)]} 기록 <strong>{pattern.seasons[season_index(day.month)]}건</strong></span>'
        '<span>작업별 사고 확률 아님</span></div>',
        unsafe_allow_html=True,
    )
    for signal in context_signals(pattern, day):
        st.markdown(
            f'<div class="field-note">기록 검토 · {escape(signal)} '
            '<span class="field-muted">사고 확률을 뜻하지 않습니다.</span></div>',
            unsafe_allow_html=True,
        )


def _daily(plan: WorkPlan) -> None:
    days = sorted({item.day for item in plan.items})
    today = today_korea()
    lower = min(days[0], today)
    upper = max(days[-1], today)
    default = today
    if st.session_state.get("field_plan_days") != tuple(days):
        st.session_state["field_plan_days"] = tuple(days)
        current_day = st.session_state.get("field_day")
        if not isinstance(current_day, date) or not lower <= current_day <= upper:
            st.session_state["field_day"] = default
    left, right = st.columns([1, 2.1], vertical_alignment="bottom")
    with left:
        selected = st.date_input("조회할 작업일", min_value=lower, max_value=upper, key="field_day")
    with right:
        at = st.session_state.get("field_plan_applied_at")
        st.caption(
            f"계획 기간 {days[0]:%Y.%m.%d}–{days[-1]:%Y.%m.%d} · "
            f"{st.session_state.get('field_plan_name', '작업계획서')}"
            + (f" · 적용 {at}" if at else "")
        )
    if selected != today:
        st.caption(f"오늘은 {today:%Y.%m.%d}입니다. 선택한 {selected:%Y.%m.%d} 계획을 보고 있습니다.")
    if today > days[-1]:
        st.warning(f"현재 계획은 {days[-1]:%Y.%m.%d}에 끝났습니다. 새 작업계획이나 일회성 작업을 등록하세요.")
    daily = [item for item in plan.items if item.day == selected]
    reviews = st.session_state.get("field_reviews", {})
    pending = [item for item in daily if reviews.get(item.work_id, {}).get("status") != "확인 완료"]
    actions: tuple[FieldAction, ...] = tuple(st.session_state.get("field_actions", ()))
    day_ids = {item.work_id for item in daily}
    relevant_actions = [
        action for action in actions if action.status == "open"
        if action.work_id in day_ids or action.due_at.date() <= selected
        or (action.needs_review and (action.work_day is None or action.work_day <= selected))
    ]
    pairs = overlapping_pairs(plan.items, selected)
    revisions = tuple(st.session_state.get("field_revisions", ()))
    checked = len(daily) - len(pending)
    checked_percent = round(checked / len(daily) * 100) if daily else 0
    progress = (
        f'<div class="field-progress-track" role="progressbar" aria-label="현장 확인 기록 완료" '
        f'aria-valuemin="0" aria-valuemax="{len(daily)}" aria-valuenow="{checked}">'
        f'<span style="width:{checked_percent}%"></span></div>'
        f'<small class="field-progress-caption">확인 완료 {checked}/{len(daily)}건 · 기록 기준</small>'
        if daily else '<small class="field-progress-caption">계획 작업 없음</small>'
    )
    st.markdown(
        '<div class="field-metrics action-metrics">'
        f'<div class="field-metric"><span>예정 작업</span><strong>{len(daily)}</strong><small>건</small></div>'
        f'<div class="field-metric"><span>시작 전 확인 대기</span><strong>{len(pending)}</strong><small>건</small>{progress}</div>'
        f'<div class="field-metric"><span>같은 구역 · 시간 중복</span><strong>{len(pairs)}</strong><small>쌍</small></div>'
        f'<div class="field-metric"><span>연관 미완료 조치</span><strong>{len(relevant_actions)}</strong><small>건</small></div>'
        '</div>', unsafe_allow_html=True,
    )
    relevant_revisions = [
        (revision, tuple(entry for entry in revision.entries if entry.day == selected))
        for revision in revisions
    ]
    relevant_revisions = [(revision, entries) for revision, entries in relevant_revisions if entries]
    if relevant_revisions:
        latest, entries = relevant_revisions[-1]
        counts = {kind: sum(entry.kind == kind for entry in entries) for kind in ("added", "changed", "removed")}
        st.markdown(
            '<div class="field-revision"><strong>선택일 계획 반영</strong>'
            f'<span>추가 {counts["added"]} · 변경 {counts["changed"]} · 제외 {counts["removed"]}</span>'
            f'<small>{latest.at:%m.%d %H:%M} · {escape(latest.source)}</small></div>',
            unsafe_allow_html=True,
        )
    show_weather_panel(selected, daily)
    _show_record_context(selected)
    if not daily:
        st.info("계획에 등록된 이 날짜의 작업이 없습니다. 계획 누락·일정 변경 여부를 확인하거나 일회성 작업을 추가하세요.")
        confirmation = next(
            (entry for entry in reversed(plan.no_work_confirmations) if entry.day == selected),
            None,
        )
        revision_token = day_revision_token(revisions, selected)
        confirmation_current = confirmation is not None and confirmation.revision_token == revision_token
        if confirmation_current:
            st.markdown(
                '<div class="field-no-work-confirm"><strong>계획표에서 작업 없음 확인</strong>'
                f'<span>{escape(confirmation.confirmed_by)} · {confirmation.at:%Y.%m.%d %H:%M} KST</span></div>',
                unsafe_allow_html=True,
            )
            if confirmation.note:
                st.caption(f"확인 메모 · {escape(confirmation.note)}")
        elif confirmation is not None:
            st.warning("이 확인 뒤 선택일의 계획 내용이 바뀌었습니다. 기존 기록은 현재 계획 상태를 뜻하지 않으므로 다시 확인하세요.")
        st.caption("저장 내용은 계획표에 해당 날짜의 작업이 등록되지 않았음을 확인한 관리자 기록입니다. 현장에 실제 작업이 없다는 안전 승인은 아닙니다.")
        token_key = revision_token or "initial"
        with st.expander("계획표에서 작업 없음 확인 기록", expanded=not confirmation_current):
            with st.form(f"field_no_work_{selected.isoformat()}_{token_key}"):
                confirmer = st.text_input(
                    "계획표 확인자 *",
                    value=confirmation.confirmed_by if confirmation_current else "",
                    max_chars=100,
                    key=f"field_no_work_by_{selected.isoformat()}_{token_key}",
                )
                note = st.text_area(
                    "확인 메모 (선택)",
                    value=confirmation.note if confirmation_current else "",
                    max_chars=1000,
                    placeholder="예: 일일 작업표와 교대 일정을 대조함",
                    key=f"field_no_work_note_{selected.isoformat()}_{token_key}",
                )
                acknowledged = st.checkbox(
                    "선택일 계획표와 현장 일정을 대조했고, 등록된 작업이 없음을 확인했습니다.",
                    key=f"field_no_work_ack_{selected.isoformat()}_{token_key}",
                )
                submitted = st.form_submit_button("계획표 확인 기록 저장", type="primary")
            if submitted:
                if not confirmer.strip():
                    st.error("확인자 이름을 입력하세요.")
                elif not acknowledged:
                    st.error("계획표와 현장 일정 대조를 확인한 뒤 저장하세요.")
                else:
                    saved = NoWorkConfirmation(
                        selected, confirmer.strip(), note.strip(), now_korea(), revision_token,
                    )
                    saved_confirmations = tuple(
                        entry for entry in plan.no_work_confirmations if entry.day != selected
                    ) + (saved,)
                    st.session_state["field_plan"] = WorkPlan(
                        plan.site, plan.items, plan.issues, saved_confirmations,
                    )
                    st.rerun()
        if selected < days[0]:
            st.caption(f"가장 가까운 등록 작업일은 {days[0]:%Y.%m.%d}입니다. 날짜를 바꾸면 그날의 작업을 미리 볼 수 있습니다.")
        next_work = next((day for day in days if day > selected), None)
        if next_work:
            st.button(
                f"다음 작업일 보기 · {next_work:%m.%d}", key="field_next_work",
                on_click=_select_field_day, args=(next_work,),
            )
        if relevant_actions:
            st.warning(f"이 날짜까지 기한이 되었거나 재확인이 필요한 미완료 조치 {len(relevant_actions)}건이 남아 있습니다.")
            if st.button("남은 조치 확인", key="field_empty_actions"):
                st.session_state["view"] = "actions"
                st.query_params["page"] = "actions"
                st.rerun()
        return
    _attention(plan, daily, pairs, reviews, actions)
    options = {f"{item.start:%H:%M}  {item.activity} · {item.area} ({item.work_id})": item for item in daily}
    choice = st.selectbox("사례와 조치를 살펴볼 작업", list(options), key="field_item_choice")
    selected_item = options[choice]
    _timeline(daily, pairs)
    st.markdown('<div class="field-panel-title">작업 일정</div>', unsafe_allow_html=True)
    cards = []
    for item in daily:
        status = reviews.get(item.work_id, {}).get("status", "미확인")
        cards.append(
            f'<div class="field-item {"selected" if item.work_id == selected_item.work_id else ""}">'
            f'<div class="field-time">{item.start:%H:%M}<br>— {item.end:%H:%M}</div>'
            f'<div><div class="field-name">{escape(item.activity)}</div>'
            f'<div class="field-meta">{escape(item.area)} · {escape(item.location or "위치 미입력")} · '
            f'{escape(item.contractor or "업체 미입력")}</div></div>'
            f'<span class="field-status {"ok" if status == "확인 완료" else ""}">{escape(status)}</span></div>'
        )
    st.markdown('<div class="field-list">' + "".join(cards) + '</div>', unsafe_allow_html=True)

    item = selected_item
    with st.container(border=True):
        st.markdown(f'<div class="field-kicker">WORK DETAIL / {escape(item.work_id)}</div><div class="field-panel-title">{escape(item.activity)}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="field-detail"><b>장소</b> {escape(item.area)} · {escape(item.location or "세부 위치 미입력")} &nbsp; '
            f'<b>시간</b> {item.start:%H:%M}–{item.end:%H:%M}<br>'
            f'<b>장비</b> {escape(item.equipment or "미입력 · 확인 필요")} &nbsp; '
            f'<b>인원</b> {item.people if item.people is not None else "미입력"}명 &nbsp; '
            f'<b>책임자</b> {escape(item.owner or "미입력")}</div>',
            unsafe_allow_html=True,
        )
        st.markdown('**계획서에 적힌 안전조치**')
        st.write(item.planned_controls or "입력된 내용이 없습니다.")
        st.markdown('**시작 전 확인할 내용**')
        st.write(item.follow_up or "추가 확인 내용이 없습니다. 현장 상태는 별도로 확인하세요.")
        st.markdown(f'<div class="field-muted">출처 · {escape(item.sheet)} {item.row}행 · 원문 검토 상태: {escape(item.review_status or "미입력")}</div>', unsafe_allow_html=True)
        if not item.equipment:
            st.warning("주요 장비가 입력되지 않았습니다. 작업 시작 전 확인하세요.")
        linked_actions = [action for action in actions if action.work_id == item.work_id]
        st.markdown('**담당 조치**')
        if linked_actions:
            for action in sorted(linked_actions, key=lambda action: action.due_at):
                status = "완료" if action.status == "done" else "재확인" if action.needs_review else "미완료"
                st.caption(f"{status} · {action.description} · {action.assignee} · {action.due_at:%m.%d %H:%M}")
        else:
            st.caption("이 작업에 지정된 조치가 없습니다.")
        with st.expander("담당자와 기한이 있는 조치 추가"):
            with st.form(f"field_action_form_{item.work_id}"):
                description = st.text_input("조치 내용 *", placeholder="실제 현장에서 확인하거나 처리할 항목", max_chars=300, key=f"action_description_{item.work_id}")
                assignee = st.text_input("담당자 *", value=item.owner, max_chars=100, key=f"action_assignee_{item.work_id}")
                due_day = st.date_input("완료 기한 날짜", value=item.day, key=f"action_due_day_{item.work_id}")
                due_time = st.time_input("완료 기한 시간", value=item.start, key=f"action_due_time_{item.work_id}")
                add_action = st.form_submit_button("조치 등록")
            if add_action:
                try:
                    created = new_action(item.work_id, description, assignee, datetime.combine(due_day, due_time), item.day)
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.session_state["field_actions"] = (*actions, created)
                    st.rerun()
        st.markdown('**현장 확인 기록**')
        current_review = reviews.get(item.work_id, {})
        if current_review:
            st.caption(f"{current_review['status']} · {current_review['reviewer']} · {current_review['at']}")
            if current_review.get("note"):
                st.write(current_review["note"])
        with st.form(f"field_review_{item.work_id}"):
            review_status = st.selectbox("확인 상태", ["확인 중", "조치 필요", "확인 완료"], key=f"review_status_{item.work_id}")
            reviewer = st.text_input("확인자 *", max_chars=100, key=f"reviewer_{item.work_id}")
            note = st.text_area("현장 확인 내용", placeholder="확인한 설비·조치 또는 남은 문제를 적으세요.", max_chars=2000, key=f"review_note_{item.work_id}")
            saved = st.form_submit_button("이 세션에 확인 기록 저장")
        if saved:
            if not reviewer.strip() or (review_status != "확인 중" and not note.strip()):
                st.error("확인자를 입력하고, ‘조치 필요’ 또는 ‘확인 완료’에는 현장 확인 내용을 적어 주세요.")
            else:
                st.session_state.setdefault("field_reviews", {})[item.work_id] = {
                    "status": review_status, "reviewer": reviewer.strip(), "note": note.strip(),
                    "at": now_korea().strftime("%Y.%m.%d %H:%M"),
                }
                st.rerun()
        if st.button("이 작업을 챗봇에서 질문", key=f"field_chat_{item.work_id}"):
            st.session_state["rag_context"] = f"{plan.site} / {item.day:%Y.%m.%d} / {item.area} {item.location} / {item.activity}"
            st.session_state["rag_equipment"] = item.equipment
            st.session_state["rag_industry"] = "건설업"
            st.session_state["view"] = "chat"
            st.query_params["page"] = "chat"
            st.rerun()
    with st.expander("선택 작업의 과거 사고사례", expanded=False):
        _case_chart(item)
    if st.button("이 날짜의 TBM 브리핑 만들기", icon=":material/description:", key="field_open_tbm"):
        st.session_state["tbm_day"] = selected
        st.session_state["view"] = "tbm"
        st.query_params["page"] = "tbm"
        st.rerun()
    st.caption("계획서 내용, 연결한 사고 기록과 모델 예보는 각각의 출처와 범위에 따라 표시됩니다. 작업별 안전조치는 현장에서 확인해 기록하세요.")


def show_field_dashboard() -> None:
    _styles()
    plan: WorkPlan | None = st.session_state.get("field_plan")
    site_line = escape(plan.site) if plan else "현장 계획을 연결하세요"
    st.markdown(
        '<div id="field-top"></div><div class="field-hero"><div>'
        '<div class="field-kicker">SAFETY ATLAS / FIELD OPERATIONS</div>'
        '<h1>오늘의 작업</h1>'
        f'<p class="field-hero-site">{site_line}</p>'
        '<p>작업 일정과 시작 전 확인 사항을 한 화면에서 살펴보세요.</p></div>'
        f'<span class="field-date"><small>오늘 기준</small>{today_korea():%Y.%m.%d}</span></div>',
        unsafe_allow_html=True,
    )
    mode = st.session_state.get("field_panel_mode", "upload" if plan is None else None)
    with st.container(key="field_actions"):
        upload_col, add_col, backup_col = st.columns([1.2, 1, 1], gap="small")
        with upload_col:
            if st.button("계획서 업로드" if plan is None else "계획서 교체", icon=":material/upload_file:", key="field_action_upload", type="primary" if plan is None else "secondary", width="stretch"):
                mode = None if mode == "upload" and plan is not None else "upload"
        with add_col:
            if st.button("일회성 작업 추가", icon=":material/add_circle_outline:", key="field_action_oneoff", width="stretch"):
                if mode == "oneoff":
                    mode = None
                else:
                    mode = "oneoff"
                    selected_day = st.session_state.get("field_day")
                    st.session_state["one_off_day"] = (
                        selected_day if plan is not None and isinstance(selected_day, date)
                        else today_korea()
                    )
        with backup_col:
            if st.button("기록 백업 · 복원", icon=":material/save:", key="field_action_backup", width="stretch"):
                mode = None if mode == "backup" else "backup"
    st.session_state["field_panel_mode"] = mode
    if mode == "upload":
        with st.container(border=True):
            st.markdown('<div class="field-panel-title">작업계획서 등록</div>', unsafe_allow_html=True)
            st.caption("샘플과 같은 .xlsx 열 구성을 지원합니다. 추출된 작업을 확인한 뒤 적용하세요.")
            uploaded = st.file_uploader("주간·일회성 작업계획서 (.xlsx)", type="xlsx", key="field_uploader")
            if SAMPLE.exists():
                st.download_button("샘플 계획서 받기", SAMPLE.read_bytes(), file_name="가상_아파트_주간작업계획서.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            if uploaded is not None:
                st.session_state["field_candidate_name"] = uploaded.name
                candidate = _load_upload(uploaded.getvalue())
                if candidate is not None and st.session_state.get("field_applied_token") != st.session_state.get("field_upload_token"):
                    _preview(candidate)
    elif mode == "oneoff":
        _add_one_off(plan)
    elif mode == "backup":
        _backup_tools(plan)
    if plan is None:
        st.markdown('<div class="field-panel"><div class="field-panel-title">계획서를 올리면 오늘의 작업이 구성됩니다</div><p class="field-sub">업로드 → 추출 내용 확인 → 계획 적용. 일회성 작업은 위 버튼에서 바로 추가할 수 있습니다.</p></div>', unsafe_allow_html=True)
        return
    _daily(plan)
