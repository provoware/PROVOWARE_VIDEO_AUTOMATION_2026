from __future__ import annotations

import json
from pathlib import Path

from scripts.render_release_docs import (\n    FILES_END,\n    FILES_START,\n    README_END,\n    README_START,\n    release_status_block,\n    render,\n)


def test_release_docs_use_canonical_evidence_and_keep_marker_api(tmp_path: Path) -> None:
    evidence_dir = tmp_path / "diagnostics" / "release_readiness"
    evidence_dir.mkdir(parents=True)
    evidence = {
        "schema_version": 1,
        "product": {
            "name": "Produkt",
            "version": "1.2.3-rc4",
            "channel": "rc",
        },
        "tests": {
            "passed": 12,
            "failed": 0,
            "skipped": 0,
            "line_coverage_percent": 81.2,
            "branch_coverage_percent": 67.3,
            "visual_scenarios": "3/3",
        },
        "manifest": {"file_count": 2},
        "matrix": {"passed_targets": 4, "total_targets": 4},
        "progress": {"completed": 1, "open": 1, "total": 2},
        "release_files": {
            "ready_suffix": "_save_",
            "policy": "Nur geprüfte Dateien sind releasefertig.",
            "ready": [
                {
                    "path": "Guide_save_.md",
                    "label": "Guide",
                    "evidence": "geprüft",
                }
            ],
            "unfinished": [
                {
                    "path": "TODO.md",
                    "label": "Aufgaben",
                    "reason": "offen",
                }
            ],
        },
        "stable_gates": [
            {
                "id": "kde",
                "label": "KDE",
                "status": "open",
                "reason": "offen",
            }
        ],
        "stable_ready": False,
        "approved_quality_report": "report_save_.json",
    }
    (evidence_dir / "RELEASE_EVIDENCE.json").write_text(
        json.dumps(evidence),
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text(
        f"{README_START}\nalt\n{README_END}\n\n"
        f"{FILES_START}\nalt\n{FILES_END}\n\nNutzung\n",
        encoding="utf-8",
    )
    (tmp_path / "STATUS.md").write_text("alt\n", encoding="utf-8")

    documents = render(tmp_path)
    status = documents[tmp_path / "STATUS.md"]

    assert "1.2.3-rc4" in status
    assert "12/12 automatisierte Tests" in status
    assert "Guide_save_.md" in status
    assert "TODO.md" in status
    assert documents[tmp_path / "README.md"].endswith("\n\nNutzung\n")

def test_release_status_block_reports_stable_ready_without_empty_open_section() -> None:
    evidence = {
        "product": {"version": "1.2.3", "channel": "stable"},
        "tests": {
            "passed": 12,
            "line_coverage_percent": 81.2,
            "branch_coverage_percent": 67.3,
            "visual_scenarios": "3/3",
        },
        "manifest": {"file_count": 2},
        "matrix": {"passed_targets": 4, "total_targets": 4},
        "stable_gates": [
            {
                "id": "kde",
                "label": "KDE",
                "status": "passed",
                "reason": "bestanden",
            }
        ],
        "approved_quality_report": "report_save_.json",
    }

    status = release_status_block(evidence)

    assert "### Stable-Status" in status
    assert "Alle Stable-Gates bestanden" in status
    assert "### Offene Stable-Gates" not in status

