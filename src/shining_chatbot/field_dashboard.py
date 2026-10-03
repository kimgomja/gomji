"""Today's work page for field managers."""

from __future__ import annotations

from datetime import date, datetime, time
from hashlib import sha256
from html import escape
from pathlib import Path
from uuid import uuid4

import pandas as pd
import streamlit as st

from shining_chatbot.case_summary import SIF_SOURCE_URL, local_cases_available, summarize_cases
from shining_chatbot.field_state import export_backup, import_backup
from shining_chatbot.work_plan import WorkItem, WorkPlan, compare_plans, overlapping_pairs, read_work_plan


SAMPLE = Path(__file__).parent / "static" / "sample_work_plan.xlsx"


def _styles() -> None:
    st.markdown("""<style>
.field-kicker{font:600 10px/1.4 var(--font-mono);letter-spacing:.08em;color:#638B73;margin:0 0 9px}
.field-hero{display:flex;justify-content:space-between;align-items:end;gap:18px;margin:0 0 22px}
.field-hero h1{font-size:clamp(28px,2.6vw,38px);font-weight:620;letter-spacing:-.045em;line-height:1.25;margin:0 0 7px;color:#252A27}
.field-hero p{font-size:13px;line-height:1.65;color:#748078;margin:0}
.field-date{color:#6A756C;font:11px var(--font-mono);white-space:nowrap;padding:7px 10px;border:1px solid var(--line);border-radius:7px;background:white}
.field-panel{border:1px solid #E3E8E2;border-radius:11px;background:#fff;padding:20px 22px;margin:0 0 15px}
.field-panel-title{font-size:15px;font-weight:610;letter-spacing:-.025em;color:#273029;margin:0 0 6px}
.field-sub{font-size:12px;line-height:1.6;color:#7B857D;margin:0 0 16px}
.field-metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:0 0 17px}
.field-metric{background:#fff;border:1px solid #E3E8E2;border-radius:10px;padding:16px 18px;min-height:92px}
.field-metric span{display:block;color:#838D85;font-size:11px;margin-bottom:8px}
.field-metric strong{font-size:25px;line-height:1;font-weight:590;letter-spacing:-.04em;color:#273029}
.field-metric small{font-size:11px;color:#89938B;margin-left:5px}
.field-list{display:grid;gap:9px;margin:8px 0 20px}
.field-item{border:1px solid #E5E9E4;border-radius:9px;padding:14px 16px;background:#fff;display:grid;grid-template-columns:60px minmax(0,1fr) auto;gap:13px;align-items:start;transition:border-color .18s,box-shadow .18s,transform .18s}
.field-item:hover{border-color:#A6B8A9;box-shadow:0 5px 16px #34483812;transform:translateY(-1px)}
.field-time{font:600 12px/1.5 var(--font-mono);color:#4F6B57}
.field-name{font-size:13px;font-weight:600;line-height:1.45;color:#29332C}
.field-meta{font-size:11px;line-height:1.6;color:#818A82;margin-top:3px}
.field-status{font-size:10px;line-height:1.4;color:#765D38;background:#F5F0E5;border:1px solid #ECE2D0;border-radius:5px;padding:4px 7px;white-space:nowrap}
.field-status.ok{color:#54715B;background:#EDF3ED;border-color:#DBE8DB}
.field-note{border-left:2px solid #9BAB9D;background:#F4F7F3;padding:12px 15px;font-size:12px;line-height:1.65;color:#536158;margin:0 0 18px}
.field-detail{font-size:12px;line-height:1.7;color:#57635A}
.field-detail b{font-weight:600;color:#344239}
.field-muted{font-size:11px;color:#8A948B;line-height:1.6}
.field-timeline{border:1px solid #E3E8E2;border-radius:10px;background:#fff;padding:16px 18px 17px;margin:0 0 18px}
.field-timeline-head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:17px}
.field-timeline-head span{font-size:13px;font-weight:600;color:#344238}
.field-timeline-head small{font-size:10px;color:#8A958C}
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
.field-case-kicker{font:600 9px var(--font-mono);letter-spacing:.08em;color:#72947A;margin-bottom:5px}
.field-case-title{font-size:14px;font-weight:610;color:#304035;letter-spacing:-.02em}
.field-case-sub{font-size:11px;line-height:1.55;color:#7F8980;margin-top:4px}
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
.field-case-foot{border-top:1px solid #EDF0EC;margin-top:13px;padding-top:10px;font-size:10px;line-height:1.55;color:#8B968C}
.field-case-foot a{color:#587B60;text-decoration:underline;text-underline-offset:2px}
@media(max-width:760px){.field-hero{display:block}.field-date{display:inline-block;margin-top:12px}.field-metrics{grid-template-columns:1fr}.field-item{grid-template-columns:48px minmax(0,1fr)}.field-status{grid-column:2;width:max-content}.field-panel{padding:17px}}
@media(max-width:760px){.field-timeline-axis,.field-timeline-row{grid-template-columns:92px minmax(0,1fr);gap:8px}.field-timeline-head small{display:none}.field-timeline-track,.field-timeline-axis>div{margin-right:18px}.field-timeline-tip{white-space:normal;min-width:130px}}
@media(max-width:760px){.field-attention-row{grid-template-columns:43px minmax(0,1fr)}.field-attention-owner{grid-column:2}}
</style>""", unsafe_allow_html=True)


def _load_upload(content: bytes) -> WorkPlan | None:
    token = sha256(content).hexdigest()
    if st.session_state.get("field_upload_token") != token:
        st.session_state["field_upload_token"] = token
        st.session_state.pop("field_candidate", None)
        try:
            st.session_state["field_candidate"] = read_work_plan(content)
        except ValueError as exc:
            st.error(str(exc))
    return st.session_state.get("field_candidate")


def _preview(plan: WorkPlan) -> None:
    st.markdown('<div class="field-panel-title">업로드 내용 확인</div>', unsafe_allow_html=True)
    st.caption(f"{plan.site} · 작업 {len(plan.items)}건 · 오류 {len(plan.issues)}건")
    current: WorkPlan | None = st.session_state.get("field_plan")
    same_site = current is not None and current.site == plan.site
    manual_items = (
        tuple(item for item in current.items if item.sheet == "화면 입력" and item.work_id not in {new.work_id for new in plan.items})
        if same_site else ()
    )
    effective = WorkPlan(
        plan.site,
        tuple(sorted((*plan.items, *manual_items), key=lambda item: (item.day, item.start, item.work_id))),
        plan.issues,
    )
    changes = compare_plans(current, effective) if same_site else None
    if current and not same_site:
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
    if st.button("이 계획 적용", type="primary", key="apply_field_plan"):
        prior_reviews = st.session_state.get("field_reviews", {})
        st.session_state["field_plan"] = effective
        st.session_state["field_reviews"] = (
            {work_id: review for work_id, review in prior_reviews.items() if work_id in changes.unchanged}
            if changes and same_site else {}
        )
        st.session_state["field_applied_token"] = st.session_state.get("field_upload_token")
        st.session_state["field_plan_applied_at"] = datetime.now().strftime("%Y.%m.%d %H:%M")
        st.session_state["field_plan_name"] = st.session_state.get("field_candidate_name", "작업계획서")
        st.rerun()


def _add_one_off(plan: WorkPlan | None) -> None:
    with st.expander("일회성 작업 빠르게 추가", expanded=False):
        with st.form("one_off_form", clear_on_submit=True):
            if plan is None:
                site = st.text_input("현장명", placeholder="예: 가상 온누리 아파트 신축공사")
            else:
                site = plan.site
            activity = st.text_input("작업 내용 *", placeholder="예: 지하 1층 배수 배관 보수")
            first, second = st.columns(2)
            with first:
                day = st.date_input("작업일 *", value=date.today(), key="one_off_day")
                start = st.time_input("시작 시간 *", value=time(9, 0), key="one_off_start")
            with second:
                area = st.text_input("동/구역 *", placeholder="예: B동")
                end = st.time_input("종료 시간 *", value=time(10, 0), key="one_off_end")
            location = st.text_input("세부 위치", placeholder="예: 지하 1층 펌프실")
            equipment = st.text_input("주요 장비", placeholder="미정이면 비워 두세요")
            owner = st.text_input("작업책임자", placeholder="확인할 담당자")
            submitted = st.form_submit_button("오늘 작업 목록에 추가", type="primary")
        if submitted:
            if not activity.strip() or not area.strip() or (plan is None and not site.strip()):
                st.error("현장명, 작업 내용, 동/구역을 입력하세요.")
            elif end <= start:
                st.error("종료 시간은 시작 시간보다 늦어야 합니다.")
            else:
                item = WorkItem(
                    f"ADHOC-{uuid4().hex[:7].upper()}", day, start, end, area.strip(),
                    location.strip(), "일회성", activity.strip(), equipment.strip(), None,
                    "", owner.strip(), "", "현장 위험요인과 필요한 조치를 확인하세요.",
                    "검토필요", "빠른 등록", "화면 입력", 0,
                )
                st.session_state["field_plan"] = WorkPlan(
                    site.strip(),
                    tuple(sorted((*plan.items, item), key=lambda work: (work.day, work.start))) if plan else (item,),
                    plan.issues if plan else (),
                )
                if plan is None:
                    st.session_state["field_plan_name"] = "화면에서 추가한 작업"
                st.session_state.pop("field_plan_days", None)
                st.session_state["field_day"] = day
                st.rerun()


def _backup_tools(plan: WorkPlan | None) -> None:
    with st.expander("세션 백업 · 복원"):
        st.caption("계획과 확인 기록을 JSON 파일로 직접 보관할 수 있습니다. 업체명·담당자 등 현장 정보가 들어 있으니 파일 접근을 관리하세요.")
        if plan is not None:
            data = export_backup(
                plan, st.session_state.get("field_reviews", {}),
                st.session_state.get("field_plan_name", "작업계획서"),
                st.session_state.get("field_plan_applied_at", ""),
            )
            st.download_button(
                "현재 작업과 확인 기록 백업", data=data,
                file_name=f"현장작업_백업_{date.today():%Y%m%d}.json", mime="application/json",
                key="field_backup_download",
            )
        backup = st.file_uploader("이전에 내려받은 백업 복원 (.json)", type="json", key="field_backup_upload")
        if backup is not None:
            token = sha256(backup.getvalue()).hexdigest()
            if token != st.session_state.get("field_restored_token"):
                try:
                    restored, reviews, name, applied_at = import_backup(backup.getvalue())
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.caption(f"{restored.site} · 작업 {len(restored.items)}건 · 확인 기록 {len(reviews)}건")
                    if st.button("이 백업 복원", key="field_restore_button"):
                        st.session_state["field_plan"] = restored
                        st.session_state["field_reviews"] = reviews
                        st.session_state["field_plan_name"] = name
                        st.session_state["field_plan_applied_at"] = applied_at
                        st.session_state["field_restored_token"] = token
                        st.session_state["field_applied_token"] = st.session_state.get("field_upload_token")
                        st.session_state.pop("field_plan_days", None)
                        st.session_state["field_day"] = date.today() if date.today() in {item.day for item in restored.items} else restored.items[0].day
                        st.rerun()


def _tbm_text(plan: WorkPlan, day: date, daily: list[WorkItem]) -> str:
    lines = [
        "TBM 작업 공유 초안 — 관리자 확인 전", f"현장: {plan.site}", f"작업일: {day:%Y.%m.%d}",
        "", "오늘의 작업",
    ]
    for item in daily:
        lines.extend([
            f"• {item.start:%H:%M}–{item.end:%H:%M} | {item.area} {item.location} | {item.activity}",
            f"  계획서에 적힌 조치: {item.planned_controls or '미입력 — 현장 확인 필요'}",
            f"  시작 전 확인: {item.follow_up or '현장 상태 확인 필요'}",
        ])
    pairs = overlapping_pairs(plan.items, day)
    if pairs:
        lines.extend(["", "동시 작업 조정 확인"])
        lines.extend(f"• {a.work_id} / {b.work_id}: 같은 구역의 작업 시간 중복, 동선·간섭 확인" for a, b in pairs)
    lines.extend(["", "작업 시작 전 현장 관리자가 실제 상태와 조치를 확인하고, 필요한 내용을 수정해 공유하세요."])
    return "\n".join(lines)


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
            f'style="left:{offset:.2f}%;width:{duration:.2f}%" tabindex="0" aria-label="{escape(title, quote=True)}">'
            f'<span class="field-timeline-tip">{escape(title)}</span></span></div></div>'
        )
    st.markdown(
        '<div class="field-timeline"><div class="field-timeline-head"><span>작업 시간대</span>'
        '<small>진한 막대 · 같은 구역의 시간 중복 후보</small></div>'
        '<div class="field-timeline-axis"><span></span><div>' + ticks + '</div></div>'
        + "".join(rows) + '</div>', unsafe_allow_html=True,
    )


def _attention(daily: list[WorkItem], pairs: tuple[tuple[WorkItem, WorkItem], ...], reviews: dict) -> None:
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
    if rows:
        st.markdown(
            '<div class="field-attention"><div class="field-attention-head">시작 전 확인할 일</div>'
            + "".join(rows) + '</div>', unsafe_allow_html=True,
        )
    else:
        st.success("이 날짜의 작업은 모두 현장 확인 완료로 기록됐습니다. 작업 조건이 바뀌면 다시 확인하세요.")


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
    st.markdown(
        '<div class="field-case"><div class="field-case-heading"><div>'
        '<div class="field-case-kicker">LOCAL SIF ARCHIVE / KEYWORD MATCH</div>'
        '<div class="field-case-title">작업 키워드가 포함된 사고사례 유형</div>'
        f'<div class="field-case-sub">{escape(item.activity)} · 검색어 “{escape(summary.keyword)}” · {escape(summary.field)}</div>'
        f'</div><div class="field-case-total">{summary.total:,}<small>기록 건수</small></div></div>'
        + "".join(rows)
        + '<div class="field-case-foot">건설업 SIF 아카이브의 작업명 또는 기인물에 같은 단어가 들어간 기록입니다. '
        '유사도 평가나 오늘 사고 확률이 아닙니다. 사고유형 상위 5개만 표시합니다. · '
        f'<a href="{SIF_SOURCE_URL}" target="_blank" rel="noopener noreferrer">자료 출처 ↗</a></div></div>',
        unsafe_allow_html=True,
    )


def _daily(plan: WorkPlan) -> None:
    days = sorted({item.day for item in plan.items})
    default = date.today() if date.today() in days else days[0]
    if st.session_state.get("field_plan_days") != tuple(days):
        st.session_state["field_plan_days"] = tuple(days)
        if st.session_state.get("field_day") not in days:
            st.session_state["field_day"] = default
    left, right = st.columns([1, 2.1], vertical_alignment="bottom")
    with left:
        selected = st.date_input("조회할 작업일", min_value=days[0], max_value=days[-1], key="field_day")
    with right:
        at = st.session_state.get("field_plan_applied_at")
        st.caption(
            f"계획 기간 {days[0]:%Y.%m.%d}–{days[-1]:%Y.%m.%d} · "
            f"{st.session_state.get('field_plan_name', '작업계획서')}"
            + (f" · 적용 {at}" if at else "")
        )
    if selected != date.today():
        st.caption(f"오늘은 {date.today():%Y.%m.%d}입니다. 선택한 {selected:%Y.%m.%d} 계획을 보고 있습니다.")
    daily = [item for item in plan.items if item.day == selected]
    reviews = st.session_state.get("field_reviews", {})
    pending = [item for item in daily if reviews.get(item.work_id, {}).get("status") != "확인 완료"]
    pairs = overlapping_pairs(plan.items, selected)
    st.markdown(
        '<div class="field-metrics">'
        f'<div class="field-metric"><span>예정 작업</span><strong>{len(daily)}</strong><small>건</small></div>'
        f'<div class="field-metric"><span>시작 전 확인</span><strong>{len(pending)}</strong><small>건</small></div>'
        f'<div class="field-metric"><span>같은 구역 · 시간 중복</span><strong>{len(pairs)}</strong><small>쌍</small></div>'
        '</div>', unsafe_allow_html=True,
    )
    if not daily:
        st.info("계획에 등록된 이 날짜의 작업이 없습니다. 계획서 누락이나 일정 변경 여부를 확인하세요.")
        return
    _attention(daily, pairs, reviews)
    if pairs:
        names = ", ".join(f"{a.work_id} ↔ {b.work_id}" for a, b in pairs)
        st.markdown(
            f'<div class="field-note"><b>동시 작업 조정 확인</b> · {escape(names)}<br>'
            '같은 동/구역의 작업 시간이 겹칩니다. 실제 동선과 작업 간섭 여부를 현장에서 확인하세요.</div>',
            unsafe_allow_html=True,
        )
    options = {f"{item.start:%H:%M}  {item.activity} · {item.area} ({item.work_id})": item for item in daily}
    choice = st.selectbox("사례와 조치를 살펴볼 작업", list(options), key="field_item_choice")
    item = options[choice]
    _case_chart(item)
    _timeline(daily, pairs)
    st.markdown('<div class="field-panel-title">작업 일정</div>', unsafe_allow_html=True)
    cards = []
    for item in daily:
        status = reviews.get(item.work_id, {}).get("status", "미확인")
        cards.append(
            '<div class="field-item">'
            f'<div class="field-time">{item.start:%H:%M}<br>— {item.end:%H:%M}</div>'
            f'<div><div class="field-name">{escape(item.activity)}</div>'
            f'<div class="field-meta">{escape(item.area)} · {escape(item.location or "위치 미입력")} · '
            f'{escape(item.contractor or "업체 미입력")}</div></div>'
            f'<span class="field-status {"ok" if status == "확인 완료" else ""}">{escape(status)}</span></div>'
        )
    st.markdown('<div class="field-list">' + "".join(cards) + '</div>', unsafe_allow_html=True)

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
        st.markdown('**현장 확인 기록**')
        current_review = reviews.get(item.work_id, {})
        if current_review:
            st.caption(f"{current_review['status']} · {current_review['reviewer']} · {current_review['at']}")
            if current_review.get("note"):
                st.write(current_review["note"])
        with st.form(f"field_review_{item.work_id}"):
            review_status = st.selectbox("확인 상태", ["확인 중", "조치 필요", "확인 완료"], key=f"review_status_{item.work_id}")
            reviewer = st.text_input("확인자 *", key=f"reviewer_{item.work_id}")
            note = st.text_area("현장 확인 내용", placeholder="확인한 설비·조치 또는 남은 문제를 적으세요.", key=f"review_note_{item.work_id}")
            saved = st.form_submit_button("이 세션에 확인 기록 저장")
        if saved:
            if not reviewer.strip() or (review_status != "확인 중" and not note.strip()):
                st.error("확인자를 입력하고, ‘조치 필요’ 또는 ‘확인 완료’에는 현장 확인 내용을 적어 주세요.")
            else:
                st.session_state.setdefault("field_reviews", {})[item.work_id] = {
                    "status": review_status, "reviewer": reviewer.strip(), "note": note.strip(),
                    "at": datetime.now().strftime("%Y.%m.%d %H:%M"),
                }
                st.rerun()
        if st.button("이 작업을 챗봇에서 질문", key=f"field_chat_{item.work_id}"):
            st.session_state["rag_context"] = f"{plan.site} / {item.day:%Y.%m.%d} / {item.area} {item.location} / {item.activity}"
            st.session_state["rag_equipment"] = item.equipment
            st.session_state["rag_industry"] = "건설업"
            st.session_state["view"] = "chat"
            st.query_params["page"] = "chat"
            st.rerun()
    with st.expander("TBM 공유 문안", expanded=False):
        st.caption("계획서 내용을 정리한 초안입니다. 현장 관리자가 실제 조치와 동시 작업을 확인한 뒤 수정해 공유하세요.")
        draft = _tbm_text(plan, selected, daily)
        draft_token = sha256(draft.encode()).hexdigest()[:8]
        edited = st.text_area("복사해 수정할 문안", value=draft, height=240, key=f"tbm_{selected}_{draft_token}")
        st.download_button("문안 내려받기 (.txt)", data=edited.encode("utf-8-sig"), file_name=f"TBM_초안_{selected:%Y%m%d}.txt", mime="text/plain")
    st.markdown('<a class="field-top-link" href="#field-top">↑ 맨 위로</a>', unsafe_allow_html=True)
    st.caption("이 화면은 업로드한 계획을 정리한 것입니다. 사고 통계와 날씨는 아직 연결되지 않았으며, 계획서의 안전조치는 현장 확인 전 확정 조치가 아닙니다.")


def show_field_dashboard() -> None:
    _styles()
    st.markdown(
        '<div id="field-top"></div><div class="field-kicker">SAFETY ATLAS / FIELD OPERATIONS</div>'
        '<div class="field-hero"><div><h1>오늘의 작업</h1>'
        '<p>작업계획을 확인하고, 시작 전 점검할 작업과 동시 작업을 한눈에 살펴보세요.</p></div>'
        f'<span class="field-date">{date.today():%Y.%m.%d}</span></div>',
        unsafe_allow_html=True,
    )
    plan: WorkPlan | None = st.session_state.get("field_plan")
    with st.expander("작업계획서 업로드" if plan else "작업계획서를 올려 시작하세요", expanded=plan is None):
        st.caption("현재는 샘플과 같은 .xlsx 열 구성을 지원합니다. 계획은 이 브라우저 세션 동안만 보관됩니다.")
        uploaded = st.file_uploader("주간·일회성 작업계획서 (.xlsx)", type="xlsx", key="field_uploader")
        if SAMPLE.exists():
            st.download_button("샘플 계획서 받기", SAMPLE.read_bytes(), file_name="가상_아파트_주간작업계획서.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        if uploaded is not None:
            st.session_state["field_candidate_name"] = uploaded.name
            candidate = _load_upload(uploaded.getvalue())
            if candidate is not None and st.session_state.get("field_applied_token") != st.session_state.get("field_upload_token"):
                _preview(candidate)
    if plan is None:
        st.markdown('<div class="field-panel"><div class="field-panel-title">계획서를 올리면 날짜별 작업이 나타납니다</div><p class="field-sub">샘플 파일을 내려받아 업로드하면 작업 목록, 검토할 항목, 같은 구역의 동시 작업을 확인할 수 있습니다.</p></div>', unsafe_allow_html=True)
        _add_one_off(None)
        _backup_tools(None)
        return
    _add_one_off(plan)
    _backup_tools(plan)
    _daily(plan)
