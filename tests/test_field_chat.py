"""Field shortcuts use local reviewed data and avoid the RAG dependency."""

from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import date, datetime
from pathlib import Path

from shining_chatbot.action_data import new_action
from shining_chatbot.field_chat import field_quick_answer
from shining_chatbot.plan_revision import make_revision
from shining_chatbot.work_plan import WorkPlan, read_work_plan


SAMPLE = Path(__file__).resolve().parents[1] / "src/shining_chatbot/static/sample_work_plan.xlsx"


class FieldChatTests(unittest.TestCase):
    def test_work_and_action_shortcuts_use_selected_day(self) -> None:
        plan = read_work_plan(SAMPLE.read_bytes())
        day = date(2026, 10, 12)
        action = new_action("WK-101", "동선 분리", "관리자 A", datetime(2026, 10, 12, 8), day)
        work = field_quick_answer("선택일 작업 요약", plan, day, {}, (action,), {}, {})
        self.assertEqual(work["status"], "field")
        self.assertIn("작업 3건", work["content"])
        self.assertIn("중복 후보 **1쌍**", work["content"])
        actions = field_quick_answer("남은 조치", plan, day, {}, (action,), {}, {})
        self.assertIn("동선 분리", actions["content"])
        revision = make_revision(None, plan, "sample.xlsx")
        changed = field_quick_answer("최근 계획 변경", plan, day, {}, (action,), {}, {}, (revision,))
        self.assertIn("추가", changed["content"])
        self.assertIsNone(field_quick_answer("비계 해체 사고 사례", plan, day, {}, (action,), {}, {}))

    def test_today_attention_uses_today_even_when_another_day_is_selected(self) -> None:
        sample = read_work_plan(SAMPLE.read_bytes())
        work = replace(sample.items[0], day=date.today(), equipment="", owner="")
        plan = WorkPlan(sample.site, (work,), ())
        answer = field_quick_answer(
            "오늘 주의사항", plan, date(2026, 10, 12), {}, (), {}, {},
            weather_summary="수원시 · 비", weather_notes=("미끄럼 확인",),
        )
        self.assertIn(f"{date.today():%Y.%m.%d}", answer["content"])
        self.assertIn("장비 미입력", answer["content"])
        self.assertIn("수원시 · 비", answer["content"])
        self.assertIn("미끄럼 확인", answer["content"])


if __name__ == "__main__":
    unittest.main()
