from __future__ import annotations

from pathlib import Path
from unittest import mock

from videobatch_fast.media_import_dialog import preview_candidate
from videobatch_fast.permission_service import create_writable_subdirectory
from videobatch_fast.selection_summary import build_selection_summary
from videobatch_fast.slideshow import SLIDESHOW_MODE_ALL_IMAGES
from videobatch_fast.ui_components import SolutionDialog
from videobatch_fast.ui_resolution_mixin import UiResolutionMixin
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


class _SelectionNotebook:
    def __init__(self) -> None:
        self.selected: list[object] = []

    def select(self, value) -> None:
        self.selected.append(value)


class _SelectionTree:
    def __init__(self, rows: dict[str, tuple[object, ...]]) -> None:
        self.rows = rows
        self.selected: list[str] = []
        self.focused = ""
        self.seen = ""
        self.focus_calls = 0

    def get_children(self):
        return tuple(self.rows)

    def item(self, iid: str, option: str):
        assert option == "values"
        return self.rows[iid]

    def selection_set(self, iid: str) -> None:
        self.selected = [iid]

    def focus(self, iid: str) -> None:
        self.focused = iid

    def see(self, iid: str) -> None:
        self.seen = iid

    def focus_set(self) -> None:
        self.focus_calls += 1


class _Guidance:
    def __init__(self) -> None:
        self.value = ""

    def set(self, value: str) -> None:
        self.value = value


class _AudioMissingHarness(UiResolutionMixin):
    def __init__(self) -> None:
        self.main_notebook = _SelectionNotebook()
        self.production_notebook = _SelectionNotebook()
        self.library_notebook = _SelectionNotebook()
        self.audio_tab = object()
        self.pair_tree = _SelectionTree({
            "pair-1": (1, "ok.wav", "bild.png"),
            "pair-2": (2, "missing.wav", "bild2.png"),
        })
        self.audio_tree = _SelectionTree({})
        self.tree_path_map: dict[str, Path] = {}
        self.guidance_text = _Guidance()


def test_audio_missing_navigation_marks_exact_pairing_row() -> None:
    harness = _AudioMissingHarness()
    harness._focus_missing_audio("missing.wav")
    assert harness.main_notebook.selected[-1] == 4
    assert harness.production_notebook.selected[-1] == 0
    assert harness.pair_tree.selected == ["pair-2"]
    assert harness.pair_tree.focused == "pair-2"
    assert harness.pair_tree.seen == "pair-2"
    assert harness.pair_tree.focus_calls == 1
    assert "missing.wav" in harness.guidance_text.value


def test_audio_missing_navigation_falls_back_to_offline_audio_row() -> None:
    harness = _AudioMissingHarness()
    harness.pair_tree = _SelectionTree({"pair-1": (1, "ok.wav", "bild.png")})
    harness.audio_tree = _SelectionTree({"audio:0": ()})
    harness.tree_path_map = {"audio:0": Path("/tmp/missing.wav")}
    harness._focus_missing_audio("missing.wav")
    assert harness.main_notebook.selected[-1] == 1
    assert harness.library_notebook.selected[-1] is harness.audio_tab
    assert harness.audio_tree.selected == ["audio:0"]
    assert harness.audio_tree.focused == "audio:0"
    assert harness.audio_tree.seen == "audio:0"
    assert "missing.wav" in harness.guidance_text.value


def test_audio_missing_dialog_uses_targeted_primary_action() -> None:
    validation_source = (ROOT / "src/videobatch_fast/validation.py").read_text(encoding="utf-8")
    resolution_source = (ROOT / "src/videobatch_fast/ui_resolution_mixin.py").read_text(encoding="utf-8")
    assert 'actions=("focus_missing_audio", "add_audio", "remove_missing")' in validation_source
    assert 'action_overrides["focus_missing_audio"]' in resolution_source
    assert SolutionDialog._label("focus_missing_audio") == "Fehlende Zuordnung anzeigen"
