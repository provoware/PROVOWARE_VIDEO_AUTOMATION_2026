from __future__ import annotations

from pathlib import Path
from unittest import mock

from videobatch_fast.media_import_dialog import preview_candidate
from videobatch_fast.permission_service import create_writable_subdirectory
from videobatch_fast.selection_summary import build_selection_summary
from videobatch_fast.slideshow import SLIDESHOW_MODE_ALL_IMAGES
from videobatch_fast.validation import validate_output_dir

ROOT = Path(__file__).resolve().parents[1]


def test_multiselect_preview_follows_focused_row() -> None:
    selected = ("/tmp/first.png", "/tmp/second.png", "/tmp/third.png")
    assert preview_candidate(selected, "/tmp/second.png") == "/tmp/second.png"
    assert preview_candidate(selected, "") == "/tmp/third.png"
    assert preview_candidate((), "") is None


def test_media_dialog_can_collect_and_continue() -> None:
    source = (ROOT / "src/videobatch_fast/media_import_dialog.py").read_text(encoding="utf-8")
    assert "Auswahl übernehmen + im Ordner bleiben" in source
    assert "self.collected" in source
    assert "_collect_and_continue" in source
    assert "preview_candidate(selected, self.tree.focus())" in source
    assert "Auswahlstatus" in source
    assert "Übernommen" in source


def test_new_output_folder_is_created_without_overwriting_file(tmp_path: Path) -> None:
    base = tmp_path / "base"
    base.mkdir()
    (base / "VideoBatch_Ausgabe").write_text("conflict", encoding="utf-8")
    result = create_writable_subdirectory(base, "VideoBatch_Ausgabe")
    assert result.writable
    assert result.path.name == "VideoBatch_Ausgabe_2"
    assert result.path.is_dir()


def test_output_permission_issue_offers_direct_solutions(tmp_path: Path) -> None:
    target = tmp_path / "blocked"
    with mock.patch("pathlib.Path.mkdir", side_effect=PermissionError("blocked")):
        issues = validate_output_dir(target)
    assert issues
    assert issues[0].code == "OUTPUT_CREATE_FAILED"
    assert "create_output_folder" in issues[0].actions
    assert "choose_output" in issues[0].actions
    assert "use_safe_output" in issues[0].actions


def test_header_summary_contains_counts_and_settings(tmp_path: Path) -> None:
    audios = [tmp_path / "a.wav", tmp_path / "b.mp3"]
    media = [tmp_path / "one.png", tmp_path / "two.jpg", tmp_path / "clip.mp4"]
    summary = build_selection_summary(
        audios,
        media,
        job_count=2,
        assignment_mode=SLIDESHOW_MODE_ALL_IMAGES,
        transition="soft",
        scene_sync=True,
        quick_mode_label="Smart Auto",
    )
    assert "2 Audio" in summary
    assert "2 Bilder" in summary
    assert "1 Video" in summary
    assert "2 Aufträge" in summary
    assert "Diashow" in summary
    assert "Szenen an" in summary


def test_solution_dialog_has_action_grid_and_new_repairs() -> None:
    source = (ROOT / "src/videobatch_fast/ui_components.py").read_text(encoding="utf-8")
    assert "ui.solutions.actions_heading" in source
    assert '"create_output_folder"' in source
    assert '"create_project_folder"' in source
    assert '"switch_to_slideshow"' in source


def test_start_flow_autorepairs_and_prompts_missing_parts() -> None:
    source = (ROOT / "src/videobatch_fast/ui_resolution_mixin.py").read_text(encoding="utf-8")
    assert "_prepare_start_intelligently" in source
    assert "SETTINGS_AUTO_REPAIRED" in source
    assert "ARCHIVE_FOLDER_MISSING" in source
    assert "create_project_folder" in source
    assert "disable_archive" in source


def test_header_selection_statistics_are_always_bound() -> None:
    source = (ROOT / "src/videobatch_fast/ui_workspace_grid_mixin.py").read_text(encoding="utf-8")
    assert "ui.header.current_selection" in source
    assert "header_selection_stats" in source
    assert "_bind_header_statistics" in source
    assert "build_selection_summary" in source
