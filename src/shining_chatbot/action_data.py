"""Auditable, session-scoped follow-up actions for a field work plan."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime
from uuid import uuid4

from shining_chatbot.business_time import now_korea


@dataclass(frozen=True)
class FieldAction:
    action_id: str
    work_id: str
    description: str
    assignee: str
    due_at: datetime
    created_at: datetime
    status: str = "open"
    needs_review: bool = False
    events: tuple[dict[str, str], ...] = ()
    work_day: date | None = None


def new_action(work_id: str, description: str, assignee: str, due_at: datetime, work_day: date | None = None) -> FieldAction:
    if not work_id.strip() or not description.strip() or not assignee.strip():
        raise ValueError("작업, 조치 내용, 담당자를 입력하세요.")
    if len(work_id) > 100 or len(description.strip()) > 300 or len(assignee.strip()) > 100:
        raise ValueError("작업ID·조치 내용·담당자 이름이 입력 한도를 넘었습니다.")
    now = now_korea()
    return FieldAction(
        f"ACT-{uuid4().hex[:8].upper()}", work_id.strip(), description.strip(),
        assignee.strip(), due_at, now,
        events=({"type": "created", "at": now.isoformat(timespec="minutes"), "actor": assignee.strip(), "note": "조치 등록"},),
        work_day=work_day,
    )


def finish_action(action: FieldAction, actor: str, note: str) -> FieldAction:
    if not actor.strip() or not note.strip():
        raise ValueError("확인자와 완료 내용을 입력하세요.")
    if len(actor.strip()) > 100 or len(note.strip()) > 2000:
        raise ValueError("확인자는 100자, 완료 내용은 2,000자 이내로 입력하세요.")
    if action.status == "done":
        return action
    now = now_korea()
    event = {"type": "completed", "at": now.isoformat(timespec="minutes"), "actor": actor.strip(), "note": note.strip()}
    return replace(action, status="done", needs_review=False, events=(*action.events, event))


def reopen_action(action: FieldAction, actor: str, reason: str) -> FieldAction:
    if not actor.strip() or not reason.strip():
        raise ValueError("변경자와 다시 연 이유를 입력하세요.")
    if len(actor.strip()) > 100 or len(reason.strip()) > 2000:
        raise ValueError("변경자는 100자, 다시 연 이유는 2,000자 이내로 입력하세요.")
    now = now_korea()
    event = {"type": "reopened", "at": now.isoformat(timespec="minutes"), "actor": actor.strip(), "note": reason.strip()}
    return replace(action, status="open", events=(*action.events, event))


def flag_changed_work(actions: tuple[FieldAction, ...], work_ids: set[str]) -> tuple[FieldAction, ...]:
    """Reopen work-dependent actions while preserving their event history."""
    now = now_korea().isoformat(timespec="minutes")
    result = []
    for action in actions:
        if action.work_id not in work_ids:
            result.append(action)
            continue
        event = {"type": "plan_changed", "at": now, "actor": "시스템", "note": "연결된 작업계획이 변경 또는 제외됨"}
        result.append(replace(action, status="open", needs_review=True, events=(*action.events, event)))
    return tuple(result)
