from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_generated_quality_report_is_ignored_and_not_tracked() -> None:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "/diagnostics/internal_quality_latest.json" in gitignore
    if (ROOT / ".git").exists():
        result = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files", "--error-unmatch", "diagnostics/internal_quality_latest.json"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        assert result.returncode != 0


def test_git_archive_excludes_historical_and_generated_evidence() -> None:
    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "diagnostics export-ignore" in attributes
    assert "docs/archive export-ignore" in attributes


def test_historical_root_artifacts_are_archived_not_shipped() -> None:
    assert not (ROOT / "BOOTSTRAP_VALIDATION.json").exists()
    assert (
        ROOT
        / "docs"
        / "archive"
        / "release-history"
        / "BOOTSTRAP_VALIDATION_2026-08-04.json"
    ).is_file()

    for name in (
        "mustervorlage_orientierung_design_layout.png",
        "muster_orientierungsvorlage_design_jayout.png",
    ):
        assert not (ROOT / name).exists()
        assert (ROOT / "docs" / "archive" / "reference-layouts" / name).is_file()
