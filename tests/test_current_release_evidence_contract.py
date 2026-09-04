from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "diagnostics/release_readiness/RELEASE_EVIDENCE.json"


def _evidence() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_current_full_regression_is_canonical_release_evidence() -> None:
    data = _evidence()
    tests = data["tests"]
    assert tests["collected"] == 468
    assert tests["passed"] == 466
    assert tests["failed"] == 0
    assert tests["skipped"] == 2
    assert tests["line_coverage_percent"] == 73.38
    assert tests["branch_coverage_percent"] == 59.01
    assert data["provenance"]["full_regression_run_id"] == 33805992774
    assert data["provenance"]["full_regression_verified_commit"] == "2e7d4350b0ccb0a5d0a69fa1033f0b1aded54e02"


def test_coverage_policy_is_an_explicit_stable_blocker() -> None:
    data = _evidence()
    gate = next(item for item in data["stable_gates"] if item["id"] == "coverage_80_65")
    assert gate["status"] == "failed"
    assert data["stable_ready"] is False
    assert data["progress"] == {
        "percent": 90,
        "completed": 27,
        "open": 3,
        "total": 30,
        "current_todo": "Coverage-Vertrag 80/65 schließen; danach physische KDE-Abnahme und Large-Media-Soak auf demselben finalen Kandidaten.",
    }

def test_readme_does_not_fall_back_to_superseded_325_test_claim() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "466/468 automatisierte Tests bestanden; 2 übersprungen" in readme
    assert "73,38 % Zeilenabdeckung" in readme
    assert "59,01 % Zweigabdeckung" in readme
    assert "Coverage-Vertrag 80/65" in readme
    assert "325/325 automatisierte Tests bestanden" not in readme
