from __future__ import annotations

import json
from pathlib import Path

from diagnostics.release_readiness.generate_from_evidence import evidence, expected_outputs
from scripts.render_release_docs import FILES_END, FILES_START, README_END, README_START, render


def test_release_docs_use_version_report_status_and_file_contract(tmp_path: Path) -> None:
    (tmp_path / "VERSION.json").write_text(json.dumps({"name": "Produkt", "build": "1.2.3-rc4", "channel": "rc"}), encoding="utf-8")
    (tmp_path / "DEVELOPMENT_STATUS.json").write_text(json.dumps({"version": "1.2.3-rc4", "approved_quality_report": "report_save_.json", "stable_blockers": ["KDE offen"]}), encoding="utf-8")
    (tmp_path / "report_save_.json").write_text(json.dumps({"version": "1.2.3-rc4", "status": "passed", "tests": {"passed": 12, "line_coverage_percent": 81.2, "branch_coverage_percent": 67.3, "visual_scenarios": "3/3"}}), encoding="utf-8")
    (tmp_path / "RELEASE_FILE_STATUS.json").write_text(json.dumps({"ready": [{"path": "Guide_save_.md", "label": "Guide"}], "unfinished": [{"path": "TODO.md", "label": "Aufgaben", "reason": "offen"}]}), encoding="utf-8")
    (tmp_path / "README.md").write_text(f"{README_START}\nalt\n{README_END}\n\n{FILES_START}\nalt\n{FILES_END}\n\nNutzung\n", encoding="utf-8")
    (tmp_path / "STATUS.md").write_text("alt\n", encoding="utf-8")
    documents = render(tmp_path)
    assert {path.name for path in documents} == {"README.md", "STATUS.md"}
    status = documents[tmp_path / "STATUS.md"]
    assert "Produkt · 1.2.3-rc4" in status
    assert "12/12 automatisierte Tests" in status
    assert "Guide_save_.md" in status
    assert "TODO.md" in status
    assert documents[tmp_path / "README.md"].endswith("\n\nNutzung\n")


def test_release_evidence_generator_owns_machine_outputs_only() -> None:
    outputs = {path.name for path in expected_outputs(evidence())}
    assert outputs == {
        "DEVELOPMENT_STATUS.json",
        "QUALITY_ENVIRONMENT_STATUS.json",
        "RELEASE_FILE_STATUS.json",
        "VideoBatch_Fast_2.8.3-rc24_BUILD_REPORT_save_.json",
    }
    assert "README.md" not in outputs
    assert "STATUS.md" not in outputs
