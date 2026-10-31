"""Regression: only explicit JSON booleans may signal Stable readiness."""
from __future__ import annotations

import unittest

from generate_from_evidence import EvidenceContractError, validate


def _evidence(*, ready: object, gate_status: str = "passed") -> dict:
    return {
        "schema_version": 1,
        "product": {"version": "2.8.3"},
        "tests": {"passed": 1, "failed": 0},
        "manifest": {"file_count": 1},
        "matrix": {"passed_targets": 1, "total_targets": 1},
        "progress": {"completed": 1, "open": 0, "total": 1},
        "release_files": {"ready": [], "unfinished": []},
        "stable_gates": [{"id": "gate", "label": "Prüfung", "status": gate_status, "reason": ""}],
        "stable_ready": ready,
    }


class EvidenceStableReadyTest(unittest.TestCase):
    def test_real_boolean_matches_gate_status(self) -> None:
        for ready, status in ((True, "passed"), (False, "open")):
            with self.subTest(ready=ready, status=status):
                validate(_evidence(ready=ready, gate_status=status))

    def test_non_boolean_values_are_rejected(self) -> None:
        for value, status in (("false", "passed"), (1, "passed"), (0, "open"), (None, "open")):
            with self.subTest(value=value, status=status):
                with self.assertRaisesRegex(EvidenceContractError, "stable_ready"):
                    validate(_evidence(ready=value, gate_status=status))

    def test_boolean_must_agree_with_gate_status(self) -> None:
        for ready, status in ((False, "passed"), (True, "open")):
            with self.subTest(ready=ready, status=status):
                with self.assertRaisesRegex(EvidenceContractError, "stable_ready"):
                    validate(_evidence(ready=ready, gate_status=status))


if __name__ == "__main__":
    unittest.main()
