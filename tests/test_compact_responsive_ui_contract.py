from pathlib import Path

import pytest


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
    catalog = _read("resources/texts/ui-recovery.json")
    assert 'text=text("recovery.dialog.clear")' in source
    assert '"recovery.dialog.clear": "Liste leeren"' in catalog
    assert 'action="dismissed_by_user"' in source
    assert 'Quelldateien und erzeugte Medien werden nicht gelöscht' in catalog
    assert '.unlink(' not in source
    assert 'shutil.rmtree' not in source


def test_f1_help_and_escape_contract_remain_present():
    canonical = _read("src/videobatch_fast/canonical_ui.py")
    components = _read("src/videobatch_fast/ui_components.py")
    shell = _read("src/videobatch_fast/canonical_shell_chrome.py")
    assert 'root.bind("<F1>", app._open_help_from_keyboard, add="+")' in canonical
    assert 'command=self._show_help_center' in shell
    assert 'self.window.bind("<Escape>"' in components


def test_source_widths_change_and_survive_reflow(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication, QFrame
    from videobatch_fast.qt_source_panel import ResponsiveSourceColumns

    app = QApplication.instance() or QApplication([])
    first, second = QFrame(), QFrame()
    columns = ResponsiveSourceColumns(first, second)
    try:
        columns.resize(1300, 450)
        columns.show()
        app.processEvents()
        assert not columns.stacked
        assert (columns.grid.columnStretch(0), columns.grid.columnStretch(1)) == (1, 1)
        columns.set_column_ratio(3, 2)
        assert (columns.grid.columnStretch(0), columns.grid.columnStretch(1)) == (3, 2)

        columns.resize(560, 700)
        app.processEvents()
        assert columns.stacked
        assert columns.grid.itemAtPosition(0, 0).widget() is first
        assert columns.grid.itemAtPosition(1, 0).widget() is second
        assert columns.grid.columnStretch(1) == 0
        columns.set_column_ratio(2, 3)

        columns.resize(1300, 450)
        app.processEvents()
        assert not columns.stacked
        assert (columns.grid.columnStretch(0), columns.grid.columnStretch(1)) == (2, 3)
        columns.set_column_ratio(1, 1)
        assert (columns.grid.columnStretch(0), columns.grid.columnStretch(1)) == (1, 1)
    finally:
        columns.close()
