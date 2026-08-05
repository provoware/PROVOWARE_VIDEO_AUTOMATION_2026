from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_stable_promotion_renames_all_release_reports_and_updates_status() -> None:
    source = (ROOT / "scripts/promote_stable_workspace.py").read_text(encoding="utf-8")
    assert "FINAL_AUDIT_{old_build}_save_.md" in source
    assert "VideoBatch_Fast_{old_build}_BUILD_REPORT_save_.json" in source
    assert 'status["approved_quality_report"]' in source
    assert '"archive"' in source
