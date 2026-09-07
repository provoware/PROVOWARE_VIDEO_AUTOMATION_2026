from pathlib import Path


def _read(name: str) -> str:
    return Path(name).read_text(encoding="utf-8")


def test_ctrl_mousewheel_uses_existing_area_zoom_and_reaches_200_percent():
    source = _read("src/videobatch_fast/ui_area_zoom_mixin.py")
    assert 'bind_all("<Control-MouseWheel>"' in source
    assert 'bind_all("<Control-Button-4>"' in source
    assert 'bind_all("<Control-Button-5>"' in source
    assert 'min(200, max(70' in source
    assert '_layout_canonical_dashboard' in source


def test_dashboard_has_compact_density_and_compact_appearance_controls():
    source = _read("src/videobatch_fast/canonical_dashboard_mixin.py")
    assert 'density = "compact" if int(height) < 690 else "comfortable"' in source
    assert 'self._dashboard_source_tree.configure(height=4 if compact else 7)' in source
    assert 'self._dashboard_queue_tree.configure(height=5 if compact else 8)' in source
    assert 'self._dashboard_preview_canvas.configure(height=104 if compact else 164)' in source
    assert 'text="Theme"' in source and 'text="Schrift"' in source
    assert 'self._sync_dashboard_scrollbar' in source
    assert 'text="Queue filtern"' in source
    assert 'filter_row.columnconfigure(1, weight=1)' in source


def test_recovery_clear_is_safe_archive_not_source_delete():
    source = _read("src/videobatch_fast/ui_recovery_mixin.py")
    assert 'text="Liste leeren"' in source
    assert 'action="dismissed_by_user"' in source
    assert 'Quelldateien und erzeugte Medien werden nicht gelöscht' in source
    assert '.unlink(' not in source
    assert 'shutil.rmtree' not in source


def test_f1_help_and_escape_contract_remain_present():
    canonical = _read("src/videobatch_fast/canonical_ui.py")
    components = _read("src/videobatch_fast/ui_components.py")
    shell = _read("src/videobatch_fast/canonical_shell_chrome.py")
    assert 'root.bind("<F1>", app._open_help_from_keyboard, add="+")' in canonical
    assert 'command=self._show_help_center' in shell
    assert 'self.window.bind("<Escape>"' in components
