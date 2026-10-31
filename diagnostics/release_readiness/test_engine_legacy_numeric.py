#!/usr/bin/env python3
"""Regression tests for malformed numeric release evidence."""
from __future__ import annotations

import json
import unittest

from engine_legacy import integer


class NumericEvidenceTests(unittest.TestCase):
    def test_json_overflow_does_not_crash_dashboard_validation(self) -> None:
        for raw in ('{"passed": 1e999}', '{"passed": -1e999}'):
            with self.subTest(raw=raw):
                self.assertIsNone(integer(json.loads(raw), "passed"))

    def test_invalid_numeric_values_are_not_accepted(self) -> None:
        for value in (float("inf"), float("-inf"), float("nan"), True, {}, []):
            with self.subTest(value=repr(value)):
                self.assertIsNone(integer({"passed": value}, "passed"))

    def test_valid_numbers_keep_existing_behavior(self) -> None:
        for value, expected in ((0, 0), (17, 17), ("42", 42)):
            with self.subTest(value=value):
                self.assertEqual(integer({"passed": value}, "passed"), expected)
        self.assertIsNone(integer({}, "passed"))


if __name__ == "__main__":
    unittest.main()
