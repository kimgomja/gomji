"""Accident date summaries count records without assigning risk scores."""

from __future__ import annotations

import unittest
from datetime import date

import pandas as pd

from shining_chatbot.record_pattern import RecordPattern, context_signals, read_pattern_csv, summarize_records


class RecordPatternTests(unittest.TestCase):
    def test_weekday_and_month_counts(self) -> None:
        frame = pd.DataFrame({
            "발생일": pd.to_datetime(["2026-10-05", "2026-10-06", "2026-11-02"]),
            "사고유형": ["넘어짐", "부딪힘", "넘어짐"],
        })
        summary = summarize_records(frame)
        self.assertEqual(summary.total, 3)
        self.assertEqual(summary.weekdays, (2, 1, 0, 0, 0, 0, 0))
        self.assertEqual(summary.months[9:11], (2, 1))
        self.assertEqual(summary.accident_types[0], ("넘어짐", 2))

    def test_two_column_field_log_with_common_headers(self) -> None:
        frame = read_pattern_csv("사고일자,재해유형,메모\n2026-10-05,넘어짐,현장 기록\n".encode("utf-8-sig"))
        self.assertEqual(frame.columns.tolist(), ["발생일", "사고유형"])
        self.assertEqual(summarize_records(frame).total, 1)

    def test_context_message_requires_enough_records_and_time_coverage(self) -> None:
        sparse = RecordPattern(12, date(2026, 10, 1), date(2026, 10, 31), (10, 1, 1, 0, 0, 0, 0),
                               (0, 0, 0, 0, 0, 0, 0, 0, 0, 12, 0, 0), ())
        self.assertEqual(context_signals(sparse, date(2026, 10, 5)), ())
        supported = RecordPattern(100, date(2023, 1, 1), date(2026, 1, 1), (35, 11, 11, 11, 11, 11, 10),
                                  (5, 5, 5, 5, 5, 5, 5, 5, 5, 30, 5, 20), ())
        self.assertEqual(len(context_signals(supported, date(2026, 10, 5))), 2)


if __name__ == "__main__":
    unittest.main()
