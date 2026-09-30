from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_stable_promotion_renames_all_release_reports_and_updates_status() -> None:
    source = (ROOT / "scripts/promote_stable_workspace.py").read_text(encoding="utf-8")
    assert "FINAL_AUDIT_{old_build}_save_.md" in source
    assert "VideoBatch_Fast_{old_build}_BUILD_REPORT_save_.json" in source
    assert 'status["approved_quality_report"]' in source
    assert '"archive"' in source


def test_stable_promotion_is_source_pinned_and_gui_roundtrip_is_bounded() -> None:
    workflow = (ROOT / ".github/workflows/stable-promotion.yml").read_text(encoding="utf-8")
    test_script = (ROOT / "test.sh").read_text(encoding="utf-8")
    assert 'paths:\n      - ".release/stable-2.8.3.json"' in workflow
    assert 'git checkout --detach "$SOURCE_SHA"' in workflow
    assert 'test "$AUTH_PARENT" = "$SOURCE_SHA"' in workflow
    assert '"source_commit": os.environ["SOURCE_SHA"]' in workflow
    assert 'GUI_TIMEOUT_SECONDS="${VIDEOBATCH_GUI_TIMEOUT_SECONDS:-180}"' in test_script
    assert 'timeout --foreground "${GUI_TIMEOUT_SECONDS}s"' in test_script
    assert 'if [[ -n "${DISPLAY:-}" ]]' in test_script
