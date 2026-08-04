from __future__ import annotations

import json
from pathlib import Path

from scripts.render_release_docs import README_END, README_START, render


def test_release_docs_use_version_report_and_status(tmp_path: Path) -> None:
    (tmp_path / "VERSION.json").write_text(
        json.dumps({"name": "Produkt", "build": "1.2.3-rc4", "channel": "rc"}), encoding="utf-8"
    )
    (tmp_path / "DEVELOPMENT_STATUS.json").write_text(
        json.dumps({"version": "1.2.3-rc4", "approved_quality_report": "report.json", "stable_blockers": ["KDE offen"]}),
        encoding="utf-8",
    )
    (tmp_path / "report.json").write_text(
        json.dumps({"version": "1.2.3-rc4", "status": "passed", "tests": {"passed": 12, "line_coverage_percent": 81.2, "branch_coverage_percent": 67.3, "visual_scenarios": "3/3"}}),
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text(f"{README_START}\nalt\n{README_END}\n\nNutzung\n", encoding="utf-8")
    (tmp_path / "STATUS.md").write_text("alt\n", encoding="utf-8")

    documents = render(tmp_path)

    assert "Produkt · 1.2.3-rc4" in documents[tmp_path / "README.md"]
    assert "12/12 automatisierte Tests" in documents[tmp_path / "STATUS.md"]
    assert "KDE offen" in documents[tmp_path / "STATUS.md"]
    assert documents[tmp_path / "README.md"].endswith("\n\nNutzung\n")
