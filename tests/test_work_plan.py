"""Checks that affect the manager's daily work list."""

from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import date, time
from io import BytesIO
from pathlib import Path

from openpyxl import Workbook

from shining_chatbot.field_state import export_backup, import_backup
from shining_chatbot.work_plan import WorkPlan, compare_plans, overlapping_pairs, read_work_plan


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
        content = export_backup(original, reviews, "sample.xlsx", "2026.10.03 21:00")
        restored, restored_reviews, name, applied_at = import_backup(content)
        self.assertEqual(restored, original)
        self.assertEqual(restored_reviews, reviews)
        self.assertEqual(name, "sample.xlsx")
        self.assertEqual(applied_at, "2026.10.03 21:00")


if __name__ == "__main__":
    unittest.main()
