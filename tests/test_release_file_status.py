from __future__ import annotations

import json
from pathlib import Path

from scripts.validate_release_file_status import validate

ROOT = Path(__file__).resolve().parents[1]


def test_release_file_contract_is_complete_and_consistent() -> None:
    contract = validate(ROOT)
    assert contract["scope"] == "standalone_release_deliverables"
    assert contract["ready_suffix"] == "_save_"

    ready = {item["path"] for item in contract["ready"]}
    unfinished = {item["path"] for item in contract["unfinished"]}
    assert ready
    assert unfinished
    assert ready.isdisjoint(unfinished)

    assert "START_HIER_save_.md" in ready
    assert "RELEASE_NOTES_save_.md" in ready
    assert "VideoBatch_Fast_2.8.3-rc24_BUILD_REPORT_save_.json" in ready
    assert "TODO.md" in unfinished
    assert "docs/STABLE_ACCEPTANCE_EVIDENCE.md" in unfinished
    assert "VISUAL_INSPECTION_MANIFEST.json" in unfinished


def test_ready_files_use_save_marker_and_unfinished_files_do_not() -> None:
    contract = json.loads((ROOT / "RELEASE_FILE_STATUS.json").read_text(encoding="utf-8"))
    assert all("_save_" in Path(item["path"]).stem for item in contract["ready"])
    assert all("_save_" not in Path(item["path"]).stem for item in contract["unfinished"])


def test_historical_reports_are_archived_and_duplicate_visual_tree_is_removed() -> None:
    archive = ROOT / "docs/archive/release-history"
    assert archive.is_dir()
    assert any(archive.glob("CODE_QUALITY_REPORT_*.md"))
    assert not (ROOT / "tests/baselines/visual").exists()
