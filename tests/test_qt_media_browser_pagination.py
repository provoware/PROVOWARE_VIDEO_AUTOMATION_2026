"""Qt browser stays bounded even if a single directory has thousands of media."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication

from videobatch_fast.incremental_directory import DirectoryRecord
from videobatch_fast.qt_media_import_dialog import MediaImportDialog


def test_browser_paginates_large_directory_without_losing_search(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    dialog = MediaImportDialog(None, audio=False, initial_dir=tmp_path)
    try:
        dialog._records = [
            DirectoryRecord(
                path=tmp_path / f"image-{number:05d}.png",
                is_dir=False, size=1024, modified=0.0
            )
            for number in range(2700)
        ]
        dialog._render_records()
        assert dialog.files.count() == 2000
        assert not dialog.more_button.isHidden()
        dialog._show_more_records()
        assert dialog.files.count() == 2700
        dialog.filter_edit.setText("image-02699")
        assert dialog.files.count() == 1
    finally:
        dialog.close()
        app.processEvents()
