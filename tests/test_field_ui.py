"""A selected work item must drive its detail and follow-up controls."""

from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from streamlit.testing.v1 import AppTest

from shining_chatbot.action_data import new_action
from shining_chatbot.incident_data import sample_incidents
from shining_chatbot.work_plan import WorkPlan, read_work_plan


SAMPLE = Path(__file__).resolve().parents[1] / "src/shining_chatbot/static/sample_work_plan.xlsx"
APP = Path(__file__).resolve().parents[1] / "src/shining_chatbot/app.py"


class FieldScreenTests(unittest.TestCase):
    def test_work_selection_updates_detail_and_chat_target(self) -> None:
        app = AppTest.from_file(str(APP))
        app.session_state["field_plan"] = read_work_plan(SAMPLE.read_bytes())
        app.session_state["field_panel_mode"] = None
        app.session_state["field_day"] = date(2026, 10, 12)
        app.run(timeout=30)
        selector = app.selectbox(key="field_item_choice")
        selector.set_value(selector.options[1]).run(timeout=30)
        self.assertFalse(app.exception)
        self.assertTrue(any("WORK DETAIL / WK-102" in markdown.value for markdown in app.markdown))
        self.assertTrue(any(button.key == "field_chat_WK-102" for button in app.button))

    def test_tbm_page_shows_daily_work_and_draft(self) -> None:
        app = AppTest.from_file(str(APP))
        app.session_state["field_plan"] = read_work_plan(SAMPLE.read_bytes())
        app.session_state["view"] = "tbm"
        app.run(timeout=30)
        self.assertFalse(app.exception)
        self.assertTrue(any("TBM 브리핑" in markdown.value for markdown in app.markdown))
        self.assertTrue(any("WK-101" in markdown.value or "비계" in markdown.value for markdown in app.markdown))
        self.assertTrue(any(button.label == "현재 내용 확인 완료" for button in app.button))

    def test_pattern_page_labels_the_record_scope(self) -> None:
        app = AppTest.from_file(str(APP))
        app.session_state["view"] = "patterns"
        app.session_state["field_incident_frame"] = sample_incidents()
        app.session_state["field_incident_scope"] = "가상 시연 기록"
        app.session_state["field_incident_name"] = "sample.csv"
        app.run(timeout=30)
        self.assertFalse(app.exception)
        self.assertTrue(any("가상 시연 기록" in markdown.value for markdown in app.markdown))
        self.assertTrue(any("요일별 발생 기록" in markdown.value for markdown in app.markdown))

    def test_today_without_scheduled_work_is_not_replaced_by_another_day(self) -> None:
        sample = read_work_plan(SAMPLE.read_bytes())
        plan = WorkPlan(sample.site, (
            replace(sample.items[0], day=date.today() - timedelta(days=1)),
            replace(sample.items[1], day=date.today() + timedelta(days=1)),
        ), ())
        app = AppTest.from_file(str(APP))
        app.session_state["field_plan"] = plan
        app.session_state["field_panel_mode"] = None
        app.run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["field_day"], date.today())
        self.assertTrue(any("계획에 등록된 이 날짜의 작업이 없습니다" in item.value for item in app.info))

    def test_future_plan_opens_on_today_with_next_work_hint(self) -> None:
        sample = read_work_plan(SAMPLE.read_bytes())
        next_day = date.today() + timedelta(days=3)
        plan = WorkPlan(sample.site, (replace(sample.items[0], day=next_day),), ())
        app = AppTest.from_file(str(APP))
        app.session_state["field_plan"] = plan
        app.session_state["field_panel_mode"] = None
        app.run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["field_day"], date.today())
        self.assertTrue(any("가장 가까운 등록 작업일" in item.value for item in app.get("caption")))
        app.button(key="field_next_work").click().run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["field_day"], next_day)

    def test_chat_attention_button_answers_from_field_plan(self) -> None:
        sample = read_work_plan(SAMPLE.read_bytes())
        plan = WorkPlan(sample.site, (replace(sample.items[0], day=date.today()),), ())
        app = AppTest.from_file(str(APP))
        app.session_state["field_plan"] = plan
        app.session_state["view"] = "chat"
        app.run(timeout=30)
        self.assertFalse(app.exception)
        next(button for button in app.button if button.label == "오늘 주의사항").click().run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["rag_messages"][-1]["status"], "field")
        self.assertIn("작업 전 확인", app.session_state["rag_messages"][-1]["content"])

    def test_field_attention_keeps_both_due_and_plan_change_flags(self) -> None:
        sample = read_work_plan(SAMPLE.read_bytes())
        day = date.today()
        work = replace(sample.items[0], day=day)
        plan = WorkPlan(sample.site, (work,), ())
        overdue = new_action(
            work.work_id,
            "현장 조치 재확인",
            "현장 관리자",
            datetime.now(ZoneInfo("Asia/Seoul")) - timedelta(hours=1),
            day,
        )
        action = replace(overdue, needs_review=True)
        self.assertIsNotNone(action.due_at.tzinfo)
        app = AppTest.from_file(str(APP))
        app.session_state["field_plan"] = plan
        app.session_state["field_actions"] = (action,)
        self.assertIsNotNone(app.session_state["field_actions"][0].due_at.tzinfo)
        app.session_state["field_reviews"] = {}
        app.session_state["field_panel_mode"] = None
        app.session_state["field_day"] = day
        app.run(timeout=30)
        self.assertFalse(app.exception)
        self.assertTrue(any("계획 변경 재확인 · 기한 지남" in item.value for item in app.markdown))

    def test_action_register_accepts_legacy_naive_kst_deadline(self) -> None:
        sample = read_work_plan(SAMPLE.read_bytes())
        day = date.today()
        work = replace(sample.items[0], day=day)
        plan = WorkPlan(sample.site, (work,), ())
        due_at = datetime.now(ZoneInfo("Asia/Seoul")).replace(tzinfo=None) - timedelta(hours=1)
        action = new_action(work.work_id, "현장 조치", "현장 관리자", due_at, day)
        app = AppTest.from_file(str(APP))
        app.session_state["field_plan"] = plan
        app.session_state["field_actions"] = (action,)
        app.session_state["view"] = "actions"
        app.run(timeout=30)
        self.assertFalse(app.exception)
        self.assertTrue(any("기한 지남" in item.value for item in app.markdown))
        app.radio(key="field_action_filter").set_value("기한 지남").run(timeout=30)
        self.assertFalse(app.exception)
        self.assertTrue(any("현장 조치" in item.value for item in app.markdown))


if __name__ == "__main__":
    unittest.main()
