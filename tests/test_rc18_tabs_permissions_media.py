from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from unittest import mock

from videobatch_fast.config import normalize_config
from videobatch_fast.permission_service import ensure_writable_directory, prepare_install_root
from videobatch_fast.ui_layout_profiles_mixin import UiLayoutProfilesMixin


ROOT = Path(__file__).resolve().parents[1]


def test_rc18_config_has_independent_zoom_and_download_start_dirs() -> None:
    result = normalize_config(
        {
            "area_zoom": {"media": 999, "preview": 10, "production": "130"},
            "last_audio_dir": "",
            "last_media_dir": "/tmp/media",
            "active_tab": 99,
        }
    )
    assert result["area_zoom"]["media"] == 180
    assert result["area_zoom"]["preview"] == 70
    assert result["area_zoom"]["production"] == 130
    assert result["last_audio_dir"].endswith("Downloads")
    assert result["last_media_dir"] == "/tmp/media"
    assert result["active_tab"] == 5


def test_writable_directory_falls_back_without_root(tmp_path: Path) -> None:
    blocked = tmp_path / "blocked"
    fallback = tmp_path / "safe"
    with mock.patch("videobatch_fast.permission_service.is_writable_directory", side_effect=[False]):
        result = ensure_writable_directory(blocked, fallback)
    assert result.writable and result.fallback_used
    assert result.path == fallback
    assert fallback.is_dir()


def test_install_root_quarantines_non_writable_child(tmp_path: Path) -> None:
    requested = tmp_path / "VideoBatchFast"
    requested.mkdir()
    (requested / "old.txt").write_text("old", encoding="utf-8")
    fallback = tmp_path / "fallback" / "VideoBatchFast"
    real_access = os.access

    def fake_access(path, mode):
        if Path(path) == requested:
            return False
        return real_access(path, mode)

    with mock.patch("os.access", side_effect=fake_access):
        result = prepare_install_root(requested, fallback)
    assert result.writable
    assert result.path in {requested, fallback}


def test_tabbed_ui_contract_and_menu_are_in_source() -> None:
    source = (ROOT / "src/videobatch_fast/ui_workspace_grid_mixin.py").read_text(encoding="utf-8")
    assert 'text("ui.tabs.media")' in source
    assert 'text("ui.tabs.preview")' in source
    assert 'text("ui.tabs.production")' in source
    assert "Menu(self.root)" in source
    assert "ttk.Panedwindow" not in source


def test_main_tab_change_saves_and_survives_restart() -> None:
    class DummyNotebook:
        def __init__(self, selected: int) -> None:
            self.selected = selected

        def select(self) -> int:
            return self.selected

        def index(self, selected: int) -> int:
            return selected

    class DummyUi(UiLayoutProfilesMixin):
        def __init__(self, selected: int, restoring: bool = False) -> None:
            self.config: dict[str, int] = {"active_tab": 0}
            self.main_notebook = DummyNotebook(selected)
            self._main_tab_restore_in_progress = restoring
            self.saved: list[dict[str, int]] = []

        def _save_settings(self) -> None:
            self.saved.append(dict(self.config))

    ui = DummyUi(3)
    ui._on_main_tab_changed()
    assert ui.config["active_tab"] == 3
    assert ui.saved == [{"active_tab": 3}]

    restarted = DummyUi(ui.saved[-1]["active_tab"], restoring=True)
    restarted._on_main_tab_changed()
    assert restarted.config["active_tab"] == 3
    assert restarted.saved == []


def test_large_media_dialog_supports_preview_and_sorting() -> None:
    source = (ROOT / "src/videobatch_fast/media_import_dialog.py").read_text(encoding="utf-8")
    assert "build_preview" in source
    assert "selectmode=\"extended\"" in source
    assert "_change_sort" in source
    assert 'window.geometry("1220x760")' in source

def test_ab_installer_uses_lstat_for_broken_or_inaccessible_symlink(tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location("rc18_ab_installer", ROOT / "scripts/ab_installer.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    requested = tmp_path / "VideoBatchFast"
    requested.symlink_to(Path("/root/not-accessible-videobatch-target"))
    data_home = tmp_path / "xdg-data"
    with mock.patch.dict(os.environ, {"XDG_DATA_HOME": str(data_home)}):
        chosen, message = module._prepare_user_install_root(requested)
    assert chosen == requested.resolve()
    assert chosen.is_dir()
    assert "gesichert" in message
    conflicts = list(tmp_path.glob(".VideoBatchFast.permission-conflict-*"))
    assert len(conflicts) == 1 and conflicts[0].is_symlink()
