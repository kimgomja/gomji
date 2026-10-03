"""Fast answers from the current field session, without external generation."""

from __future__ import annotations

from datetime import date, timedelta
import re

from shining_chatbot.action_data import FieldAction
from shining_chatbot.business_time import today_korea
from shining_chatbot.plan_revision import PlanRevision, day_revision_token
from shining_chatbot.tbm_data import TbmDelivery, TbmRecord, daily_actions, daily_items
from shining_chatbot.work_plan import WorkPlan, overlapping_pairs


def _safe(value: str) -> str:
    return re.sub(r"([\\`*_{}\[\]()#+!|>])", r"\\\1", value)


def field_intent(prompt: str) -> str | None:
    compact = re.sub(r"\s+", "", prompt).lower()
    exact = {
        "선택일작업요약": "선택일작업요약", "오늘작업요약": "오늘작업요약",
        "오늘주의사항": "오늘주의사항", "오늘날씨": "현장날씨", "현장날씨": "현장날씨",
        "남은조치": "남은조치",
        "TBM준비상태": "TBM준비상태", "최근계획변경": "최근계획변경",
        "오늘달라진점": "오늘달라진점",
    }
    if compact in exact:
        return exact[compact]
    if any(term in compact for term in ("주의사항", "주의할점", "유의사항", "유의할점")) and "오늘" in compact:
        return "오늘주의사항"
    weather_terms = (
        "날씨", "기상", "기온", "강수", "풍속", "바람", "폭염", "한파",
        "강풍", "호우", "장마", "비와", "비오", "비예보", "눈와", "눈오", "눈올", "눈예보",
        "춥", "덥",
    )
    historical_terms = ("사고", "기록", "통계", "월별", "경향", "과거")
    if any(term in compact for term in weather_terms) and not any(term in compact for term in historical_terms):
        return "현장날씨"
    if any(term in compact for term in ("남은조치", "미완료조치", "미처리조치")):
        return "남은조치"
    if "tbm" in compact and any(term in compact for term in ("준비", "상태", "완료")):
        return "TBM준비상태"
    if any(term in compact for term in ("최근계획변경", "계획변경", "달라진점")):
        return "최근계획변경"
    if "작업" in compact and any(term in compact for term in ("요약", "목록", "몇건")) and not any(
        term in compact for term in ("사고", "위험", "예방", "사례", "안전수칙")
    ):
        return "오늘작업요약" if "오늘" in compact else "선택일작업요약"
    return None


def requested_weather_day(prompt: str) -> date:
    compact = re.sub(r"\s+", "", prompt).lower()
    today = today_korea()
    if "모레" in compact:
        return today + timedelta(days=2)
    if "내일" in compact:
        return today + timedelta(days=1)
    return today


def field_quick_answer(
    prompt: str,
    plan: WorkPlan | None,
    day: date,
    reviews: dict,
    actions: tuple[FieldAction, ...],
    tbm_records: dict[str, tuple[TbmRecord, ...]],
    tbm_deliveries: dict[str, tuple[TbmDelivery, ...]],
    revisions: tuple[PlanRevision, ...] = (),
    weather_summary: str = "",
    weather_notes: tuple[str, ...] = (),
    weather_day: date | None = None,
) -> dict | None:
    command = field_intent(prompt)
    if command is None:
        return None
    if plan is None:
        return {"role": "assistant", "status": "field", "content": "연결된 작업계획이 없습니다. **오늘의 작업**에서 계획서를 올리거나 일회성 작업을 추가해 주세요."}
    if command in {"오늘작업요약", "오늘주의사항"}:
        day = today_korea()
    if command == "현장날씨":
        day = weather_day or today_korea()
    if command == "오늘달라진점":
        day = today_korea()
    if command in {"최근계획변경", "오늘달라진점"}:
        if not revisions:
            content = "아직 적용된 계획 변경 기록이 없습니다. 새 계획서를 적용하거나 일회성 작업을 추가하면 변경 내용을 볼 수 있습니다."
        else:
            relevant = [
                (revision, tuple(entry for entry in revision.entries if entry.day == day))
                for revision in revisions
            ]
            relevant = [(revision, entries) for revision, entries in relevant if entries]
            if relevant:
                latest, entries = relevant[-1]
                lines = [f"**{day:%Y.%m.%d} 최근 계획 반영 · {latest.at:%Y.%m.%d %H:%M} · {_safe(latest.source)}**"]
                labels = {"added": "추가", "changed": "변경", "removed": "제외"}
                lines.extend(f"- {labels[entry.kind]} · {_safe(entry.activity)} ({_safe(entry.work_id)})" for entry in entries)
            else:
                lines = [f"**{day:%Y.%m.%d} 작업의 계획 변경 기록이 없습니다.**"]
            lines.append("출처: 적용한 계획의 작업ID와 내용 비교. 현장 확인 기록은 변경된 작업에서 다시 확인하세요.")
            content = "\n".join(lines)
        return {"role": "assistant", "status": "field", "content": content}
    items = daily_items(plan, day)
    related = daily_actions(plan, day, actions)
    visible = {action.action_id: action for action in related}
    for action in actions:
        if action.status == "open" and action.due_at.date() <= day:
            visible[action.action_id] = action
    open_actions = sorted((action for action in visible.values() if action.status == "open"), key=lambda action: action.due_at)
    if not items:
        lines = [f"**{day:%Y.%m.%d}에 등록된 작업이 없습니다.** 계획 누락이나 일정 변경 여부를 확인해 주세요."]
        confirmation = next(
            (entry for entry in reversed(plan.no_work_confirmations) if entry.day == day),
            None,
        )
        if confirmation is not None and confirmation.revision_token == day_revision_token(revisions, day):
            lines.append(
                f"계획표 작업 없음 확인: {_safe(confirmation.confirmed_by)} · "
                f"{confirmation.at:%Y.%m.%d %H:%M} KST · 실제 현장에 작업이 없다는 안전 승인은 아닙니다."
            )
        elif confirmation is not None:
            lines.append("작업 없음 확인은 있지만 이 날짜의 계획 변경 뒤 다시 확인하지 않았습니다.")
        else:
            lines.append("이 날짜의 계획표 작업 없음 확인 기록은 없습니다.")
        if open_actions:
            lines.append(f"기한이 되었거나 재확인이 필요한 미완료 조치 {len(open_actions)}건:")
            lines.extend(f"- {_safe(action.description)} · {_safe(action.assignee)} · {action.due_at:%m.%d %H:%M}" for action in open_actions[:5])
        else:
            lines.append("기한이 된 미완료 조치는 없습니다.")
        if command in {"오늘주의사항", "현장날씨"}:
            lines.append(f"현장 예보: {_safe(weather_summary) if weather_summary else '예보 확인 불가 · 오늘의 작업에서 현장 위치를 연결하거나 기상청 특보를 직접 확인'}")
            lines.extend(f"예보 관련 확인: {_safe(note)}" for note in weather_notes)
        lines.append("출처: 현재 적용한 작업계획·조치 기록·연결한 모델 예보. 작업 조건은 현장에서 확인하세요.")
        return {"role": "assistant", "status": "field", "content": "\n".join(lines)}
    if command == "현장날씨":
        lines = [f"**오늘 현장 예보 · {day:%Y.%m.%d}**"]
        lines.append(_safe(weather_summary) if weather_summary else "예보 위치가 연결되지 않았거나 예보를 불러오지 못했습니다. 오늘의 작업에서 현장 위치를 연결하거나 기상청 특보를 직접 확인하세요.")
        lines.extend(f"작업 관련 확인: {_safe(note)}" for note in weather_notes)
        lines.append("모델 예보는 현장 측정이나 작업 허가 기준을 대신하지 않습니다.")
        return {"role": "assistant", "status": "field", "content": "\n".join(lines)}
    if command == "오늘주의사항":
        pending = [item for item in items if reviews.get(item.work_id, {}).get("status") != "확인 완료"]
        pairs = overlapping_pairs(plan.items, day)
        lines = [f"**{day:%Y.%m.%d} 작업 전 확인 · {len(items)}건**"]
        lines.append(f"- 현장 확인 대기 **{len(pending)}건** · 같은 구역·시간 중복 후보 **{len(pairs)}쌍** · 연결된 미완료 조치 **{len(open_actions)}건**")
        for item in pending[:4]:
            details = [item.follow_up] if item.follow_up else []
            if not item.equipment:
                details.append("장비 미입력")
            if not item.owner:
                details.append("책임자 미입력")
            lines.append(f"- {_safe(item.activity)}: {_safe(' / '.join(details) if details else '현장 조건 확인 대기')}")
        if len(pending) > 4:
            lines.append(f"- 그 밖의 확인 대기 작업 {len(pending) - 4}건은 오늘의 작업 화면에서 확인하세요.")
        lines.append(f"- 현장 예보: {_safe(weather_summary) if weather_summary else '예보 확인 불가 · 오늘의 작업에서 현장 위치를 연결하거나 기상청 특보를 직접 확인'}")
        lines.extend(f"- 예보 관련 확인: {_safe(note)}" for note in weather_notes)
        lines.append("출처: 현재 적용한 작업계획·현장 확인·조치 기록 및 연결한 모델 예보. 작업 허가나 중지 판단은 현장 기준에 따르세요.")
    elif command in {"선택일작업요약", "오늘작업요약"}:
        lines = [f"**{_safe(plan.site)} · {day:%Y.%m.%d} 작업 {len(items)}건**"]
        lines.extend(f"- {item.start:%H:%M}–{item.end:%H:%M} · {_safe(item.area)} · {_safe(item.activity)}" for item in items)
        pairs = overlapping_pairs(plan.items, day)
        lines.append(f"같은 구역·시간 중복 후보 **{len(pairs)}쌍**, 미완료 조치 **{len(open_actions)}건**입니다.")
        lines.append("출처: 현재 적용한 작업계획서와 조치 기록. 작업 전 현장 상태를 확인하세요.")
    elif command == "남은조치":
        lines = [f"**{day:%Y.%m.%d} 연결 조치 · 미완료 {len(open_actions)}건**"]
        if open_actions:
            lines.extend(
                f"- {_safe(action.description)} · {_safe(action.assignee)} · 기한 {action.due_at:%m.%d %H:%M}"
                + (" · 계획 변경 재확인" if action.needs_review else "")
                for action in open_actions
            )
        else:
            lines.append("등록된 미완료 조치가 없습니다.")
        lines.append("출처: 현재 적용한 조치 현황. 완료 판단은 담당자가 기록합니다.")
    else:
        pending = [item for item in items if reviews.get(item.work_id, {}).get("status") != "확인 완료"]
        changed = [action for action in related if action.needs_review]
        history = tbm_records.get(day.isoformat(), ())
        deliveries = tbm_deliveries.get(day.isoformat(), ())
        lines = [f"**{day:%Y.%m.%d} TBM 준비 상태**"]
        lines.append(f"- 현장 확인 필요: **{len(pending)}건**")
        lines.append(f"- 계획 변경 조치 재확인: **{len(changed)}건**")
        lines.append(f"- 관리자 확인 기록: **{len(history)}건**, 진행 기록: **{len(deliveries)}건**")
        lines.append("계획·조치·예보가 바뀌었는지 TBM 브리핑 화면에서 최종 확인하세요.")
    return {"role": "assistant", "status": "field", "content": "\n".join(lines)}
