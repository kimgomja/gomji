"""Deterministic TBM briefing snapshots built from reviewed work and actions."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date, datetime
from hashlib import sha256
from html import escape

from shining_chatbot.action_data import FieldAction
from shining_chatbot.business_time import now_korea
from shining_chatbot.work_plan import WorkItem, WorkPlan, overlapping_pairs


@dataclass(frozen=True)
class TbmRecord:
    day: date
    fingerprint: str
    confirmed_by: str
    audience: str
    confirmed_at: datetime
    note: str
    weather_summary: str = ""


@dataclass(frozen=True)
class TbmDelivery:
    day: date
    fingerprint: str
    confirmation_at: datetime
    delivered_by: str
    attendee_count: int
    delivered_at: datetime
    note: str


def record_delivery(record: TbmRecord, delivered_by: str, attendee_count: int, note: str) -> TbmDelivery:
    if not delivered_by.strip() or attendee_count < 1 or attendee_count > 10000:
        raise ValueError("TBM 진행자와 참석 인원을 확인하세요.")
    return TbmDelivery(
        record.day, record.fingerprint, record.confirmed_at,
        delivered_by.strip(), attendee_count, now_korea(), note.strip(),
    )


def daily_items(plan: WorkPlan, day: date) -> tuple[WorkItem, ...]:
    return tuple(item for item in plan.items if item.day == day)


def daily_actions(plan: WorkPlan, day: date, actions: tuple[FieldAction, ...]) -> tuple[FieldAction, ...]:
    ids = {item.work_id for item in daily_items(plan, day)}
    all_ids = {item.work_id for item in plan.items}
    return tuple(
        action for action in actions
        if action.work_id in ids or (
            action.needs_review and action.work_id not in all_ids
            and (action.work_day == day or action.work_day is None)
        )
    )


def brief_fingerprint(
    plan: WorkPlan, day: date, actions: tuple[FieldAction, ...], reviews: dict,
    weather_summary: str = "", revision_token: str = "",
) -> str:
    items = daily_items(plan, day)
    ids = {item.work_id for item in items}
    payload = {
        "site": plan.site,
        "day": day,
        "items": [asdict(item) for item in items],
        "actions": [asdict(action) for action in daily_actions(plan, day, actions)],
        "reviews": {work_id: reviews.get(work_id, {}) for work_id in sorted(ids)},
        "weather": weather_summary,
        "revision": revision_token,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=lambda value: value.isoformat()).encode("utf-8")
    return sha256(encoded).hexdigest()


def confirm_brief(
    plan: WorkPlan, day: date, actions: tuple[FieldAction, ...], reviews: dict,
    confirmed_by: str, audience: str, note: str, weather_summary: str = "",
    revision_token: str = "",
) -> TbmRecord:
    if not daily_items(plan, day):
        raise ValueError("선택한 날짜에 등록된 작업이 없습니다.")
    if not confirmed_by.strip() or not audience.strip():
        raise ValueError("진행자와 공유 대상을 입력하세요.")
    pending = [item for item in daily_items(plan, day) if reviews.get(item.work_id, {}).get("status") != "확인 완료"]
    if pending:
        raise ValueError(f"현장 확인이 끝나지 않은 작업 {len(pending)}건을 먼저 확인하세요.")
    if any(action.needs_review for action in daily_actions(plan, day, actions)):
        raise ValueError("계획 변경으로 재확인이 필요한 조치를 먼저 확인하세요.")
    return TbmRecord(
        day, brief_fingerprint(plan, day, actions, reviews, weather_summary, revision_token),
        confirmed_by.strip(), audience.strip(), now_korea(), note.strip(), weather_summary,
    )


def briefing_text(
    plan: WorkPlan, day: date, actions: tuple[FieldAction, ...],
    record: TbmRecord | None, reviews: dict, weather_summary: str = "",
    delivery: TbmDelivery | None = None,
) -> str:
    """Plain text that a manager can paste into the team's existing channel."""
    items = daily_items(plan, day)
    shown_weather = (record.weather_summary if record else weather_summary) or "미연결 · 현장 기상과 기상청 특보 확인"
    lines = [
        f"[{'TBM 확인본' if record else 'TBM 초안 · 현장 확인 전'}] {plan.site}",
        f"작업일 {day:%Y.%m.%d} · 예정 작업 {len(items)}건",
        f"현장 예보: {shown_weather}",
        "",
        "■ 오늘의 작업",
    ]
    for item in items:
        lines.append(f"{item.start:%H:%M}–{item.end:%H:%M} · {item.area} · {item.activity}")
        lines.append(f"  계획 조치: {item.planned_controls or '미입력 · 현장 확인 필요'}")
        if item.follow_up:
            lines.append(f"  시작 전 확인: {item.follow_up}")
        review = reviews.get(item.work_id, {})
        if review.get("status") == "확인 완료" and review.get("note"):
            lines.append(f"  현장 확인: {review['note']}")
    pairs = overlapping_pairs(plan.items, day)
    lines.extend(("", f"■ 같은 구역·시간 중복 후보 {len(pairs)}쌍"))
    lines.extend(f"- {a.activity} / {b.activity} · {a.area} · 동선·간섭 확인" for a, b in pairs)
    open_actions = sorted((action for action in daily_actions(plan, day, actions) if action.status == "open"), key=lambda action: action.due_at)
    lines.extend(("", f"■ 미완료 조치 {len(open_actions)}건"))
    lines.extend(f"- {action.description} · {action.assignee} · {action.due_at:%m.%d %H:%M}" for action in open_actions)
    if record:
        lines.extend(("", f"관리자 확인: {record.confirmed_by} · {record.confirmed_at:%Y.%m.%d %H:%M}", f"공유 대상: {record.audience}"))
        if record.note:
            lines.append(f"전달 사항: {record.note}")
    if record and delivery and delivery.fingerprint == record.fingerprint and delivery.confirmation_at == record.confirmed_at:
        lines.append(f"TBM 진행: {delivery.delivered_by} · 참석 {delivery.attendee_count}명 · {delivery.delivered_at:%Y.%m.%d %H:%M}")
        if delivery.note:
            lines.append(f"질문·변경: {delivery.note}")
    lines.extend(("", "계획서와 모델 예보를 정리한 자료입니다. 작업 조건과 조치는 현장에서 확인하세요."))
    return "\n".join(lines)


def briefing_html(
    plan: WorkPlan, day: date, actions: tuple[FieldAction, ...],
    record: TbmRecord | None, reviews: dict, weather_summary: str = "",
    delivery: TbmDelivery | None = None,
) -> bytes:
    items = daily_items(plan, day)
    related_actions = sorted(
        (action for action in daily_actions(plan, day, actions) if action.status == "open"),
        key=lambda action: action.due_at,
    )
    work_rows = "".join(
        '<section class="work"><div class="time">'
        f'{item.start:%H:%M}<span>– {item.end:%H:%M}</span></div>'
        f'<div><h2>{escape(item.activity)}</h2><p class="meta">{escape(item.area)} · '
        f'{escape(item.location or "세부 위치 미입력")} · {escape(item.contractor or "업체 미입력")}</p>'
        f'<p><b>계획된 조치</b> {escape(item.planned_controls or "미입력 · 현장 확인 필요")}</p>'
        f'<p><b>시작 전 확인</b> {escape(item.follow_up or "현장 상태 확인")}</p>'
        + (f'<p><b>현장 확인</b> {escape(reviews[item.work_id]["note"])}</p>'
           if reviews.get(item.work_id, {}).get("note") else '')
        + '</div></section>'
        for item in items
    )
    pairs = overlapping_pairs(plan.items, day)
    overlap_rows = "".join(
        f'<li>{escape(a.activity)} / {escape(b.activity)} · {escape(a.area)} · 작업 시간 중복, 동선과 간섭 확인</li>'
        for a, b in pairs
    ) or '<li>같은 구역의 시간 중복 후보 없음</li>'
    action_rows = "".join(
        f'<li>{escape(action.description)}{(" · 계획 변경 재확인" if action.needs_review else "")} '
        f'<span>{escape(action.assignee)} · {action.due_at:%m.%d %H:%M}</span></li>'
        for action in related_actions
    ) or '<li>등록된 미완료 조치 없음</li>'
    state = "관리자 확인본" if record else "확인 전 초안"
    footer = (
        f'진행자 {escape(record.confirmed_by)} · 공유 대상 {escape(record.audience)} · '
        f'확인 시각 {record.confirmed_at:%Y.%m.%d %H:%M}'
        + (f'<div class="manager-note">관리자 전달 사항 · {escape(record.note)}</div>' if record.note else '')
        if record else "현장 관리자가 작업 내용과 실제 조치를 확인한 뒤 공유하세요."
    )
    if record and delivery and delivery.fingerprint == record.fingerprint and delivery.confirmation_at == record.confirmed_at:
        footer += (
            f'<div class="manager-note">TBM 진행 · {escape(delivery.delivered_by)} · '
            f'참석 {delivery.attendee_count}명 · {delivery.delivered_at:%Y.%m.%d %H:%M}'
            + (f'<br>질문·변경 기록 · {escape(delivery.note)}' if delivery.note else '')
            + '</div>'
        )
    shown_weather = record.weather_summary if record else weather_summary
    weather_row = (
        f'<h3>현장 예보</h3><div class="weather">{escape(shown_weather)}<small>모델 예보 · Open-Meteo. 현장 측정과 기상청 특보를 별도로 확인 · '
        '<a href="https://www.kosha.or.kr/safety1team/tr/reference.do?articleNo=456837&attachNo=263892&mode=download">안전보건공단 폭염 예방수칙</a> · '
        '<a href="https://www.moel.go.kr/news/cardinfo/view.do?bbs_seq=20251200063">고용노동부 한파 안전 안내</a></small></div>'
        if shown_weather else '<h3>현장 예보</h3><div class="weather">예보 미연결 · 현장 기상과 기상청 특보를 별도로 확인</div>'
    )
    html = f'''<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>TBM 브리핑 · {escape(plan.site)}</title>
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css');
*{{box-sizing:border-box}}body{{margin:0;background:#E7ECE7;color:#253129;font-family:'Pretendard Variable','Malgun Gothic',sans-serif;font-size:13px;line-height:1.65}}
main{{width:min(840px,calc(100% - 32px));margin:32px auto;background:#fff;border:1px solid #D9E2D9;border-radius:12px;padding:36px 42px;box-shadow:0 16px 42px #273E2C16}}
.top{{display:flex;justify-content:space-between;gap:18px;border-bottom:1px solid #E4EAE3;padding-bottom:20px;margin-bottom:24px}}
.kicker{{font-size:10px;letter-spacing:.12em;color:#638B73;font-weight:650}}h1{{font-size:30px;letter-spacing:-.04em;line-height:1.2;margin:8px 0}}.site{{color:#5D6F61;margin:0}}
.badge{{border:1px solid #C9D9CB;border-radius:6px;padding:5px 9px;color:#46674F;font-size:11px;height:max-content;white-space:nowrap}}
.summary{{display:flex;gap:20px;flex-wrap:wrap;padding:14px 17px;background:#F5F8F4;border-radius:7px;margin-bottom:28px;color:#48604D}}
h2{{font-size:15px;letter-spacing:-.02em;margin:0 0 3px}}h3{{font-size:13px;margin:27px 0 10px}}.work{{display:grid;grid-template-columns:80px 1fr;gap:18px;border-top:1px solid #E8EEE8;padding:17px 0}}.time{{color:#4F7257;font-weight:650}}.time span{{display:block;font-weight:400;color:#9BA79C}}
.work p{{margin:5px 0;color:#536057}}.work p.meta{{font-size:11px;color:#89968B;margin-bottom:10px}}b{{color:#354B3A;font-weight:600}}
ul{{margin:0;padding:0;list-style:none}}li{{border-top:1px solid #E8EEE8;padding:9px 0}}li span{{float:right;color:#748B79;font-size:11px}}
footer{{border-top:1px solid #DFE7DF;margin-top:30px;padding-top:14px;color:#6F8173;font-size:11px}}.note{{margin-top:7px;color:#99A49B}}
.manager-note{{margin-top:8px;color:#354B3A;font-size:13px;white-space:pre-wrap}}
.weather{{padding:12px 15px;border-radius:6px;background:#F5F8F4;color:#3F5945;font-size:12px}}
.weather a{{color:#456A4E;text-decoration:underline;text-underline-offset:2px}}
.weather small{{display:block;color:#859687;font-size:10px;margin-top:4px}}
@media(max-width:600px){{main{{margin:0;width:100%;border:0;border-radius:0;padding:25px 20px}}.work{{grid-template-columns:60px 1fr;gap:10px}}li span{{float:none;display:block}}}}
@media print{{body{{background:#fff}}main{{width:100%;margin:0;border:0;border-radius:0;box-shadow:none;padding:18mm 15mm}}.work{{break-inside:avoid}}}}
</style></head><body><main><header class="top"><div><div class="kicker">SAFETY ATLAS / TOOLBOX MEETING</div><h1>작업 전 TBM 브리핑</h1><p class="site">{escape(plan.site)} · {day:%Y.%m.%d}</p></div><span class="badge">{state}</span></header>
<div class="summary"><span>예정 작업 <b>{len(items)}건</b></span><span>동시 작업 확인 <b>{len(pairs)}쌍</b></span><span>미완료 조치 <b>{len(related_actions)}건</b></span></div>
{weather_row}<h3>오늘의 작업과 계획된 조치</h3>{work_rows}<h3>동시 작업 조정</h3><ul>{overlap_rows}</ul><h3>남은 조치</h3><ul>{action_rows}</ul>
<footer>{footer}<div class="note">계획서 내용을 정리한 자료입니다. 실제 작업 조건과 조치 내용을 현장에서 확인하세요.</div></footer></main></body></html>'''
    return html.encode("utf-8-sig")
