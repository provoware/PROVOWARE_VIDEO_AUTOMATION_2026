from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "diagnostics/release_readiness/RELEASE_EVIDENCE.json"
RC25_REPORT = "VideoBatch_Fast_2.8.3-rc25_BUILD_REPORT_save_.json"


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
    assert data["manifest"] == {
        "path": "RELEASE_MANIFEST.json",
        "file_count": 466,
        "status": "passed",
    }
    provenance = data["provenance"]
    assert int(provenance["full_regression_run_id"]) > 0
    assert len(str(provenance["full_regression_verified_commit"])) == 40
    assert int(provenance["evidence_normalization_run_id"]) > 0
    assert provenance["legacy_a32_full_regression"]["status"] == "historical_superseded"
    assert "full_regression_artifact_name" not in provenance
    assert "full_regression_artifact_id" not in provenance
    assert "full_regression_artifact_sha256" not in provenance


def test_internal_quality_keeps_generator_schema_and_current_architecture_separate() -> None:
    quality = _evidence()["internal_quality"]
    for key in (
        "architecture_findings",
        "internal_files_checked",
        "internal_findings",
        "internal_function_count",
        "largest_python_file_lines",
        "maximum_complexity",
    ):
        assert isinstance(quality[key], int)
        assert quality[key] >= 0
    assert quality["internal_findings"] == 0
    assert quality["measurement_source"] == "scripts/internal_quality_gate.py"
    assert quality["measurement_scope"] == "src+scripts+tests"
    assert quality["current_architecture"] == {
        "modules_checked": 115,
        "function_count": 1140,
        "class_count": 140,
        "largest_python_file": "ui_workspace_grid_mixin.py",
        "largest_python_file_lines": 699,
        "architecture_findings": 0,
    }


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


def test_active_status_uses_real_rc25_report_and_current_40d_numbers() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    development = json.loads((ROOT / "DEVELOPMENT_STATUS.json").read_text(encoding="utf-8"))
    assert "503/505 automatisierte Tests bestanden; 2 übersprungen" in readme
    assert "81,06 % Zeilenabdeckung" in readme
    assert "65,79 % Zweigabdeckung" in readme
    assert development["approved_quality_report"] == RC25_REPORT
    report = ROOT / RC25_REPORT
    assert report.is_file()
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["version"] == "2.8.3-rc25"
    assert payload["status"] == "passed"
    assert payload["tests"]["passed"] == 503
    assert RC25_REPORT in readme
    assert "325/325 automatisierte Tests bestanden" not in readme
