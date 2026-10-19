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


def test_cached_missing_media_and_replaced_symlinks_are_not_imported(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    dialog = MediaImportDialog(None, audio=False, initial_dir=tmp_path)
    try:
        actual = tmp_path / "valid.png"
        actual.write_bytes(b"fake image bytes")
        vanished = tmp_path / "gone.png"
        outside = tmp_path / "outside.png"
        outside.write_bytes(b"not a source")
        shortcut = tmp_path / "shortcut.png"
        shortcut.symlink_to(outside)
        dialog._collect_paths([actual, vanished, shortcut])
        assert dialog.collected == [actual]
        assert "2 nicht mehr verfügbare" in dialog.collection_status.text()
        actual.unlink()  # removed after the user collected it
        dialog._accept_selection()
        assert dialog.result == ()
        assert "Noch keine Datei" in dialog.status.text()
    finally:
        dialog.close()
        app.processEvents()
