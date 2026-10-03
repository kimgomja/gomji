"""Portable session backup for the single-user field dashboard pilot."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date, time

from shining_chatbot.work_plan import WorkItem, WorkPlan


BACKUP_VERSION = 1
REVIEW_STATUSES = {"확인 중", "조치 필요", "확인 완료"}


def export_backup(plan: WorkPlan, reviews: dict, plan_name: str, applied_at: str) -> bytes:
    work_ids = {item.work_id for item in plan.items}
    payload = {
        "version": BACKUP_VERSION,
        "site": plan.site,
        "plan_name": plan_name,
        "applied_at": applied_at,
        "items": [asdict(item) for item in plan.items],
        "issues": list(plan.issues),
        "reviews": {key: value for key, value in reviews.items() if key in work_ids},
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, default=lambda value: value.isoformat()).encode("utf-8-sig")


def import_backup(content: bytes) -> tuple[WorkPlan, dict, str, str]:
    if len(content) > 2 * 1024 * 1024:
        raise ValueError("백업 파일은 2MB 이하여야 합니다.")
    try:
        payload = json.loads(content.decode("utf-8-sig"))
        if not isinstance(payload, dict) or payload.get("version") != BACKUP_VERSION:
            raise ValueError("지원하지 않는 백업 버전입니다.")
        site = payload["site"]
        raw_items = payload["items"]
        if not isinstance(site, str) or not site.strip() or not isinstance(raw_items, list) or not 1 <= len(raw_items) <= 500:
            raise ValueError("현장명 또는 작업 목록을 확인하세요.")
        items = []
        seen = set()
        for raw in raw_items:
            if not isinstance(raw, dict):
                raise ValueError("작업 형식을 확인하세요.")
            item = WorkItem(
                **{**raw, "day": date.fromisoformat(raw["day"]),
                   "start": time.fromisoformat(raw["start"]), "end": time.fromisoformat(raw["end"])}
            )
            text_fields = (
                "work_id", "area", "location", "trade", "activity", "equipment", "contractor",
                "owner", "planned_controls", "follow_up", "review_status", "change_note", "sheet",
            )
            if not all(isinstance(getattr(item, key), str) for key in text_fields):
                raise ValueError("작업 텍스트 형식을 확인하세요.")
            if item.people is not None and (not isinstance(item.people, int) or isinstance(item.people, bool) or item.people < 0):
                raise ValueError("인원 형식을 확인하세요.")
            if not isinstance(item.row, int) or item.row < 0:
                raise ValueError("원문 행 번호를 확인하세요.")
            if not item.work_id or item.work_id in seen or not item.area or not item.activity or item.end <= item.start:
                raise ValueError("작업ID·날짜·시간·장소를 확인하세요.")
            seen.add(item.work_id)
            items.append(item)
        issues = payload.get("issues", [])
        if not isinstance(issues, list) or any(not isinstance(issue, str) for issue in issues):
            raise ValueError("검토 항목 형식을 확인하세요.")
        raw_reviews = payload.get("reviews", {})
        if not isinstance(raw_reviews, dict):
            raise ValueError("현장 확인 기록 형식을 확인하세요.")
        reviews = {}
        for work_id, review in raw_reviews.items():
            if work_id not in seen or not isinstance(review, dict):
                continue
            status, reviewer, note, at = (review.get(key) for key in ("status", "reviewer", "note", "at"))
            if status in REVIEW_STATUSES and all(isinstance(value, str) for value in (reviewer, note, at)):
                reviews[work_id] = {"status": status, "reviewer": reviewer[:100], "note": note[:2000], "at": at[:30]}
        plan_name = str(payload.get("plan_name") or "복원한 작업계획")[:200]
        applied_at = str(payload.get("applied_at") or "")[:30]
    except (KeyError, TypeError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
        if isinstance(exc, ValueError) and str(exc).endswith("합니다."):
            raise
        raise ValueError("백업 파일 형식을 확인하세요.") from exc
    return WorkPlan(site.strip(), tuple(sorted(items, key=lambda item: (item.day, item.start, item.work_id))), tuple(issues)), reviews, plan_name, applied_at
