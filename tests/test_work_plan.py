"""Checks that affect the manager's daily work list."""

from __future__ import annotations

import unittest
import json
from dataclasses import replace
from datetime import date, datetime, time
from io import BytesIO
from pathlib import Path

from openpyxl import Workbook

from shining_chatbot.action_data import finish_action, flag_changed_work, new_action
from shining_chatbot.field_state import export_backup, import_backup
from shining_chatbot.plan_revision import make_revision
from shining_chatbot.tbm_data import brief_fingerprint, briefing_html, briefing_text, confirm_brief, daily_actions, record_delivery
from shining_chatbot.weather_data import WeatherLocation
from shining_chatbot.work_plan import WorkPlan, _day, _time, compare_plans, overlapping_pairs, read_work_plan


SAMPLE = Path(__file__).resolve().parents[1] / "src/shining_chatbot/static/sample_work_plan.xlsx"


class WorkPlanTests(unittest.TestCase):
    def test_sample_schedule_and_overlap(self) -> None:
        plan = read_work_plan(SAMPLE.read_bytes())
        self.assertEqual(plan.site, "가상 온누리 아파트 신축공사")
        self.assertEqual(len(plan.items), 11)
        self.assertEqual(len([item for item in plan.items if item.day == date(2026, 10, 12)]), 3)
        self.assertEqual(
            [(a.work_id, b.work_id) for a, b in overlapping_pairs(plan.items, date(2026, 10, 12))],
            [("WK-101", "WK-102")],
        )
        self.assertEqual(plan.issues, ())

    def test_invalid_rows_are_not_silently_included(self) -> None:
        book = Workbook()
        sheet = book.active
        sheet.title = "주간작업계획"
        sheet.append(["작업ID", "작업일", "시작", "종료", "동/구역", "작업 내용", "인원(명)"])
        sheet.append(["A-1", date(2026, 10, 12), time(9), time(11), "B동", "비계 해체", 4])
        sheet.append(["A-1", date(2026, 10, 13), time(9), time(11), "B동", "중복 ID", 4])
        sheet.append(["A-2", date(2026, 10, 13), time(11), time(9), "B동", "잘못된 시간", 4])
        sheet.append(["A-3", None, time(9), time(11), "B동", "날짜 없음", 4])
        sheet.append(["A-4", date(2026, 10, 14), time(9), time(11), "B동", "인원 오류", 3.5])
        data = BytesIO()
        book.save(data)
        plan = read_work_plan(data.getvalue())
        self.assertEqual([item.work_id for item in plan.items], ["A-1"])
        self.assertEqual(len(plan.issues), 4)
        self.assertTrue(all("행" in issue and "제외" in issue for issue in plan.issues))

    def test_common_column_names_and_missing_id_are_supported(self) -> None:
        book = Workbook()
        sheet = book.active
        sheet.title = "작업일정"
        sheet.append(["현장명", "가상 새 현장"])
        sheet.append(["작업일자", "시작 시간", "종료 시간", "작업장소", "작업명", "담당자"])
        sheet.append([date(2026, 10, 12), time(9), time(11), "B동", "비계 해체", "관리자 A"])
        data = BytesIO()
        book.save(data)
        first = read_work_plan(data.getvalue())
        self.assertEqual(first.site, "가상 새 현장")
        self.assertEqual(len(first.items), 1)
        self.assertTrue(first.items[0].work_id.startswith("AUTO-"))
        self.assertEqual(first.items[0].owner, "관리자 A")
        sheet.insert_rows(3)
        data = BytesIO()
        book.save(data)
        second = read_work_plan(data.getvalue())
        self.assertEqual(first.items[0].work_id, second.items[0].work_id)

    def test_common_date_and_time_cells(self) -> None:
        self.assertEqual(_day("2026년 10월 12일"), date(2026, 10, 12))
        self.assertEqual(_day(20261012), date(2026, 10, 12))
        self.assertEqual(_time("오후 3시 30분"), time(15, 30))
        self.assertEqual(_time(930), time(9, 30))

    def test_revision_detects_equipment_change_but_ignores_row_move(self) -> None:
        original = read_work_plan(SAMPLE.read_bytes())
        first, second = original.items[:2]
        revised = WorkPlan(
            original.site,
            (replace(first, row=21), replace(second, equipment="다른 장비")),
            (),
        )
        changes = compare_plans(WorkPlan(original.site, (first, second), ()), revised)
        self.assertEqual(changes.unchanged, (first.work_id,))
        self.assertEqual(changes.changed, (second.work_id,))

    def test_backup_restores_review_with_schedule(self) -> None:
        original = read_work_plan(SAMPLE.read_bytes())
        reviews = {"WK-101": {"status": "확인 완료", "reviewer": "관리자 A", "note": "작업구역 확인", "at": "2026.10.12 07:50"}}
        action = new_action("WK-101", "동선 분리", "관리자 A", datetime(2026, 10, 12, 8))
        day = date(2026, 10, 12)
        daily_reviews = {
            item.work_id: {"status": "확인 완료", "reviewer": "관리자 A", "note": "작업구역 확인", "at": "2026.10.12 07:50"}
            for item in original.items if item.day == day
        }
        record = confirm_brief(original, day, (action,), daily_reviews, "관리자 A", "오전 작업자", "동선 분리", "수원시 · 비")
        history = {day.isoformat(): (record,)}
        delivery = record_delivery(record, "관리자 A", 12, "질문 없음")
        deliveries = {day.isoformat(): (delivery,)}
        revision = make_revision(None, original, "sample.xlsx")
        location = WeatherLocation("수원시", "경기도", 37.2636, 127.0286)
        content = export_backup(original, daily_reviews, "sample.xlsx", "2026.10.03 21:00", (action,), history, location, deliveries, (revision,))
        restored, restored_reviews, restored_actions, restored_tbm, restored_deliveries, restored_revisions, restored_location, name, applied_at = import_backup(content)
        self.assertEqual(restored, original)
        self.assertEqual(restored_reviews, daily_reviews)
        self.assertEqual(restored_actions, (action,))
        self.assertEqual(restored_tbm, history)
        self.assertEqual(restored_deliveries, deliveries)
        self.assertEqual(restored_revisions, (revision,))
        self.assertEqual(restored_location, location)
        self.assertEqual(name, "sample.xlsx")
        self.assertEqual(applied_at, "2026.10.03 21:00")

    def test_plan_change_reopens_completed_action_with_history(self) -> None:
        action = new_action("WK-101", "동선 분리", "관리자 A", datetime(2026, 10, 12, 8))
        completed = finish_action(action, "관리자 A", "동선 분리 확인")
        reopened, = flag_changed_work((completed,), {"WK-101"})
        self.assertEqual(reopened.status, "open")
        self.assertTrue(reopened.needs_review)
        self.assertEqual([event["type"] for event in reopened.events], ["created", "completed", "plan_changed"])

    def test_older_backup_still_opens(self) -> None:
        plan = read_work_plan(SAMPLE.read_bytes())
        payload = json.loads(export_backup(plan, {}, "old.xlsx", "").decode("utf-8-sig"))
        payload["version"] = 2
        payload.pop("tbm_records")
        payload.pop("weather_location")
        payload.pop("tbm_deliveries")
        payload.pop("revisions")
        restored, reviews, actions, tbm, deliveries, revisions, location, name, _ = import_backup(json.dumps(payload).encode("utf-8"))
        self.assertEqual(restored, plan)
        self.assertEqual((reviews, actions, tbm, deliveries, revisions, location, name), ({}, (), {}, {}, (), None, "old.xlsx"))

    def test_incomplete_restored_review_does_not_confirm_work(self) -> None:
        plan = read_work_plan(SAMPLE.read_bytes())
        payload = json.loads(export_backup(plan, {}, "plan.xlsx", "").decode("utf-8-sig"))
        payload["reviews"] = {
            plan.items[0].work_id: {"status": "확인 완료", "reviewer": "", "note": "", "at": "2026.10.12 08:00"}
        }
        _, reviews, *_ = import_backup(json.dumps(payload).encode("utf-8"))
        self.assertEqual(reviews, {})

    def test_brief_requires_review_and_changes_invalidate_confirmation(self) -> None:
        plan = read_work_plan(SAMPLE.read_bytes())
        day = date(2026, 10, 12)
        with self.assertRaisesRegex(ValueError, "현장 확인"):
            confirm_brief(plan, day, (), {}, "관리자", "오전조", "")
        reviews = {item.work_id: {"status": "확인 완료"} for item in plan.items if item.day == day}
        action = new_action("WK-101", "동선 분리", "관리자", datetime(2026, 10, 12, 8))
        record = confirm_brief(plan, day, (action,), reviews, "관리자", "오전조", "전달", "수원시 · 비")
        self.assertEqual(record.fingerprint, brief_fingerprint(plan, day, (action,), reviews, "수원시 · 비"))
        completed = finish_action(action, "관리자", "확인")
        self.assertNotEqual(record.fingerprint, brief_fingerprint(plan, day, (completed,), reviews, "수원시 · 비"))
        self.assertNotEqual(record.fingerprint, brief_fingerprint(plan, day, (action,), reviews, "수원시 · 맑음"))

    def test_plan_revision_invalidates_tbm_even_if_content_is_reverted(self) -> None:
        plan = read_work_plan(SAMPLE.read_bytes())
        day = date(2026, 10, 12)
        reviews = {item.work_id: {"status": "확인 완료"} for item in plan.items if item.day == day}
        before = confirm_brief(plan, day, (), reviews, "관리자", "오전조", "", revision_token="revision-1")
        self.assertNotEqual(before.fingerprint, brief_fingerprint(plan, day, (), reviews, revision_token="revision-2"))

    def test_brief_html_escapes_user_content(self) -> None:
        plan = read_work_plan(SAMPLE.read_bytes())
        day = date(2026, 10, 12)
        reviews = {item.work_id: {"status": "확인 완료"} for item in plan.items if item.day == day}
        record = confirm_brief(plan, day, (), reviews, "관리자", "오전조", "<script>alert(1)</script>", "<img src=x>")
        html = briefing_html(plan, day, (), record, reviews).decode("utf-8-sig")
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;img src=x&gt;", html)
        delivery = record_delivery(record, "관리자", 5, "질문 없음")
        delivered_html = briefing_html(plan, day, (), record, reviews, delivery=delivery).decode("utf-8-sig")
        self.assertIn("참석 5명", delivered_html)

    def test_share_text_marks_draft_and_confirmed_copy(self) -> None:
        plan = read_work_plan(SAMPLE.read_bytes())
        day = date(2026, 10, 12)
        reviews = {item.work_id: {"status": "확인 완료", "note": "동선 분리 확인"} for item in plan.items if item.day == day}
        draft = briefing_text(plan, day, (), None, reviews)
        self.assertIn("TBM 초안 · 현장 확인 전", draft)
        confirmed = confirm_brief(plan, day, (), reviews, "관리자", "오전조", "질문 받기")
        shared = briefing_text(plan, day, (), confirmed, reviews)
        self.assertIn("TBM 확인본", shared)
        self.assertIn("관리자 확인: 관리자", shared)
        self.assertIn("현장 확인: 동선 분리 확인", shared)

    def test_removed_work_action_blocks_old_day_brief(self) -> None:
        original = read_work_plan(SAMPLE.read_bytes())
        day = date(2026, 10, 12)
        removed = original.items[0]
        plan = WorkPlan(original.site, tuple(item for item in original.items if item.work_id != removed.work_id), ())
        action = new_action(removed.work_id, "동선 분리", "관리자", datetime(2026, 10, 12, 8), day)
        flagged, = flag_changed_work((action,), {removed.work_id})
        self.assertEqual(daily_actions(plan, day, (flagged,)), (flagged,))
        reviews = {item.work_id: {"status": "확인 완료"} for item in plan.items if item.day == day}
        with self.assertRaisesRegex(ValueError, "재확인"):
            confirm_brief(plan, day, (flagged,), reviews, "관리자", "오전조", "")


if __name__ == "__main__":
    unittest.main()
