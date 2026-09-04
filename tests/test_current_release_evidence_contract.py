from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "diagnostics/release_readiness/RELEASE_EVIDENCE.json"
RC25_REPORT = "VideoBatch_Fast_2.8.3-rc25_BUILD_REPORT_save_.json"


def _object(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _evidence() -> dict:
    return _object(EVIDENCE)


def _assert_test_metrics(tests: dict) -> None:
    assert tests["failed"] == 0
    assert tests["collected"] == tests["passed"] + tests["failed"] + tests["skipped"]
    assert tests["passed"] > 0
    assert tests["line_coverage_percent"] >= 80.0
    assert tests["branch_coverage_percent"] >= 65.0
    assert tests["combined_coverage_percent"] > 0.0
    assert "full_regression_groups" not in tests


def _assert_manifest_contract(data: dict) -> None:
    manifest = _object(ROOT / "RELEASE_MANIFEST.json")
    assert data["manifest"] == {
        "path": "RELEASE_MANIFEST.json",
        "file_count": manifest["file_count"],
        "status": "passed",
    }
    assert manifest["file_count"] > 0


def _assert_provenance_contract(provenance: dict) -> None:
    assert int(provenance["full_regression_run_id"]) > 0
    assert len(str(provenance["full_regression_verified_commit"])) == 40
    assert int(provenance["evidence_normalization_run_id"]) > 0
    assert provenance["legacy_a32_full_regression"]["status"] == "historical_superseded"
    assert "full_regression_artifact_name" not in provenance
    assert "full_regression_artifact_id" not in provenance
    assert "full_regression_artifact_sha256" not in provenance


def _assert_architecture_contract(architecture: dict) -> None:
    integer_keys = (
        "modules_checked",
        "function_count",
        "class_count",
        "largest_python_file_lines",
        "architecture_findings",
    )
    for key in integer_keys:
        assert isinstance(architecture[key], int)
        assert architecture[key] >= 0
    assert architecture["architecture_findings"] == 0
    assert architecture["modules_checked"] > 0
    assert architecture["function_count"] > 0
    assert architecture["largest_python_file"]


def _assert_quality_contract(quality: dict) -> None:
    integer_keys = (
        "architecture_findings",
        "internal_files_checked",
        "internal_findings",
        "internal_function_count",
        "largest_python_file_lines",
        "maximum_complexity",
    )
    for key in integer_keys:
        assert isinstance(quality[key], int)
        assert quality[key] >= 0
    assert quality["internal_findings"] == 0
    assert quality["maximum_complexity"] <= 30
    assert quality["measurement_source"] == "scripts/internal_quality_gate.py"
    assert quality["measurement_scope"] == "src+scripts+tests"
    _assert_architecture_contract(quality["current_architecture"])


def test_current_full_regression_is_canonical_release_evidence() -> None:
    data = _evidence()
    _assert_test_metrics(data["tests"])
    _assert_manifest_contract(data)
    _assert_provenance_contract(data["provenance"])
    _assert_quality_contract(data["internal_quality"])


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
    data = _evidence()
    tests = data["tests"]
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    development = _object(ROOT / "DEVELOPMENT_STATUS.json")
    line_coverage = f"{tests['line_coverage_percent']:.2f}".replace(".", ",")
    branch_coverage = f"{tests['branch_coverage_percent']:.2f}".replace(".", ",")
    assert f"{tests['passed']}/{tests['collected']} automatisierte Tests bestanden; {tests['skipped']} übersprungen" in readme
    assert f"{line_coverage} % Zeilenabdeckung" in readme
    assert f"{branch_coverage} % Zweigabdeckung" in readme
    assert development["approved_quality_report"] == RC25_REPORT
    assert development["generated_from"] == "diagnostics/release_readiness/RELEASE_EVIDENCE.json"
    report = ROOT / RC25_REPORT
    assert report.is_file()
    payload = _object(report)
    assert payload["version"] == "2.8.3-rc25"
    assert payload["status"] == "passed"
    assert payload["tests"]["passed"] == tests["passed"]
    assert payload["tests"]["collected"] == tests["collected"]
    assert payload["release_manifest_files"] == data["manifest"]["file_count"]
    assert RC25_REPORT in readme
    assert "325/325 automatisierte Tests bestanden" not in readme
