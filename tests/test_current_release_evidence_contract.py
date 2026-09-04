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
    assert tests["collected"] == 505
    assert tests["passed"] == 503
    assert tests["failed"] == 0
    assert tests["skipped"] == 2
    assert tests["line_coverage_percent"] == 81.06
    assert tests["branch_coverage_percent"] == 65.79
    assert tests["combined_coverage_percent"] == 78.04
    assert "full_regression_groups" not in tests
    assert data["manifest"]["file_count"] == 465
    assert data["provenance"]["full_regression_run_id"] == 33845125393
    assert data["provenance"]["full_regression_verified_commit"] == "58a8a06b5eae6992a6dd6e20ed3d4d0a982c7d4c"


def test_coverage_policy_is_closed_but_stable_remains_fail_closed() -> None:
    data = _evidence()
    gate = next(item for item in data["stable_gates"] if item["id"] == "coverage_80_65")
    assert gate["status"] == "passed"
    assert data["stable_ready"] is False
    assert data["progress"] == {
        "percent": 93,
        "completed": 28,
        "open": 2,
        "total": 30,
        "current_todo": "Physische KDE-X11-/Wayland-Abnahme und Large-Media-Soak auf demselben finalen Kandidaten durchführen.",
    }
    assert [item["id"] for item in data["stable_gates"] if item["status"] == "open"] == [
        "physical_kde_x11_wayland",
        "large_media_soak",
    ]


def test_active_status_uses_existing_approved_report_and_current_40d_numbers() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    development = json.loads((ROOT / "DEVELOPMENT_STATUS.json").read_text(encoding="utf-8"))
    assert "503/505 automatisierte Tests bestanden; 2 übersprungen" in readme
    assert "81,06 % Zeilenabdeckung" in readme
    assert "65,79 % Zweigabdeckung" in readme
    assert "Coverage-Vertrag 80/65: **BESTANDEN**" in readme
    assert development["approved_quality_report"] == "VideoBatch_Fast_2.8.3-rc24_BUILD_REPORT_save_.json"
    assert (ROOT / development["approved_quality_report"]).is_file()
    assert "VideoBatch_Fast_2.8.3-rc25_BUILD_REPORT_save_.json" not in readme
    assert "325/325 automatisierte Tests bestanden" not in readme
