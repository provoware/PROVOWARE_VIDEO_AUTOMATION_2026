from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QPoint, QSize, Qt, Signal, QTimer
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from .incremental_directory import DirectoryRecord, scan_directory_batches
from .media_dialog_support import human_size, safe_media_directory, sort_directory_records
from .media_index import MediaIndex, media_roots
from .qt_thumbnail_cache import load_thumbnail
from .probe import AUDIO_EXTENSIONS, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS
from .qt_phase2_components import PreviewPanel


from . import qt_media_browser_layout

from . import qt_media_browser_view

class MediaImportDialog(QDialog):
    """Native Qt media browser with incremental scan, filter, sorting and live preview."""

    KEEP_OPEN_LABEL = "Auswahl übernehmen + im Ordner bleiben"

    _scanBatch = Signal(int, object)
    _scanDone = Signal(int, str)
    _thumbReady = Signal(int, object, object)

    def __init__(
        self,
        parent: QWidget | None,
        *,
        audio: bool,
        initial_dir: Path,
        modal: bool = True,
    ) -> None:
        super().__init__(parent)
        self.audio = bool(audio)
        self.allowed = AUDIO_EXTENSIONS if self.audio else IMAGE_EXTENSIONS | VIDEO_EXTENSIONS
        self.current_dir = safe_media_directory(initial_dir)
        self.result: tuple[Path, ...] = ()
        self.collected: list[Path] = []
        self._records: list[DirectoryRecord] = []
        self._record_positions: dict[str, int] = {}
        self._records_version = 0
        self._sorted_cache_key: tuple[str, bool, int] | None = None
        self._sorted_cache: list[DirectoryRecord] = []
        self._cached_index = MediaIndex()
        self._scan_seen: set[str] = set()
        self._scan_generation = 0
        self._scan_cancel = threading.Event()
        self._scan_complete = False
        self._display_limit = 2000
        self.sort_key = "name"
        self.sort_reverse = False
        self._thumb_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="VB-Thumbnail")
        self._thumb_generation = 0
        self._thumb_pending: set[tuple[str, int, int]] = set()
        self._thumb_images: dict[tuple[str, int, int], QImage] = {}
        self._thumb_items: dict[str, QListWidgetItem] = {}
        self._thumb_keys: dict[str, tuple[str, int, int]] = {}
        self._thumb_closing = False
        self._redraw_timer = QTimer(self)
        self._redraw_timer.setSingleShot(True)
        self._redraw_timer.setInterval(200)
        self._redraw_timer.timeout.connect(self._render_records)

        self.setWindowTitle("Audio auswählen" if self.audio else "Bilder und Videos auswählen")
        self.resize(1220, 760)
        self.setMinimumSize(760, 520)
        self.setModal(modal)
        self._build()
        self._scanBatch.connect(self._apply_scan_batch)
        self._scanDone.connect(self._finish_scan)
        self._thumbReady.connect(self._apply_thumbnail)
        self.finished.connect(self._stop_background_tasks)
        self.files.verticalScrollBar().valueChanged.connect(self._show_visible_thumbnails)
        self.files.horizontalScrollBar().valueChanged.connect(self._show_visible_thumbnails)
        self._load_directory()

    def _build(self) -> None:
        return qt_media_browser_layout._build(self)

    def _navigate(self, path: Path) -> None:
        candidate = safe_media_directory(path)
        self.current_dir = candidate
        self.path_edit.setText(str(candidate))
        self._load_directory()

    def _load_directory(self) -> None:
        self._scan_cancel.set()
        self._scan_generation += 1
        generation = self._scan_generation
        self._scan_cancel = threading.Event()
        cancel = self._scan_cancel
        directory = self.current_dir
        self._records = []
        self._records_version += 1
        self._record_positions.clear()
        self._display_limit = 2000
        self._scan_seen.clear()
        self._scan_complete = False
        self.files.clear()
        # The cache is a last-known listing, not proof that files still exist.
        try:
            indexed = self._cached_index.cached_directory(directory)
            self._records = [
                DirectoryRecord(item.path, False, item.size, item.mtime_ns / 1_000_000_000)
                for item in indexed
            ]
        except Exception:
            self._records = []
        if self._records:
            self._record_positions = {
                str(record.path): index for index, record in enumerate(self._records)
            }
            self._render_records()
        self.preview.set_source(None, include_image=False)
        self.status.setText(
            f"{len(self._records)} zuletzt bekannte Medien · Aktualisierung läuft …"
            if self._records else "Erste Dateien werden geladen …"
        )
        self.scan_progress.setRange(0, 0)
        self.scan_stop.setEnabled(True)

        def worker() -> None:
            error = ""
            try:
                for batch in scan_directory_batches(
                    directory,
                    self.allowed,
                    cancel=cancel,
                    batch_size=128,
                ):
                    if cancel.is_set():
                        break
                    self._scanBatch.emit(generation, batch)
            except OSError as exc:
                error = str(exc)
            self._scanDone.emit(generation, error)

        threading.Thread(
            target=worker,
            daemon=True,
            name=f"VideoBatch-Qt-MediaScan-{generation}",
        ).start()

    def _apply_scan_batch(self, generation: int, records_object: object) -> None:
        if generation != self._scan_generation:
            return
        records = list(records_object)
        if records:
            self._records_version += 1
        for record in records:
            key = str(record.path)
            self._scan_seen.add(key)
            position = self._record_positions.get(key)
            if position is not None:
                self._records[position] = record
            else:
                self._record_positions[key] = len(self._records)
                self._records.append(record)
        self.status.setText(f"{len(self._records)} Einträge · Ordner wird geprüft …")
        if not self._redraw_timer.isActive():
            self._redraw_timer.start()

    def _finish_scan(self, generation: int, error: str) -> None:
        if generation != self._scan_generation:
            return
        self._scan_complete = True
        self._redraw_timer.stop()
        if not error and not self._scan_cancel.is_set():
            self._records_version += 1
            self._records = [record for record in self._records
                             if str(record.path) in self._scan_seen]
            self._record_positions = {
                str(record.path): index for index, record in enumerate(self._records)
            }
        self.scan_progress.setRange(0, 100)
        self.scan_progress.setValue(100)
        self.scan_stop.setEnabled(False)
        self._render_records()
        if error:
            self.status.setText(f"Scan mit Einschränkung beendet: {error}")
        elif self._scan_cancel.is_set():
            self.status.setText(f"Scan angehalten · {len(self._records)} Einträge gefunden")
        else:
            self.status.setText(f"Scan fertig · {len(self._records)} Einträge gefunden")

    def _stop_scan(self) -> None:
        self._scan_cancel.set()
        self.scan_stop.setEnabled(False)
        self.scan_progress.setRange(0, 100)
        self.scan_progress.setValue(0)
        self.status.setText(f"Scan angehalten · {len(self._records)} Einträge bleiben auswählbar")

    def _sort_changed(self) -> None:
        self.sort_key = str(self.sort_combo.currentData() or "name")
        self._render_records()

    def _toggle_sort(self) -> None:
        self.sort_reverse = not self.sort_reverse
        self.sort_direction.setText("↓" if self.sort_reverse else "↑")
        self._render_records()

    def _show_more_records(self) -> None:
        self._display_limit += 2000
        self._render_records()

    def _render_records(self) -> None:
        return qt_media_browser_view._render_records(self)

    def _set_view_mode(self, mode: str) -> None:
        if mode == "icons":
            self.files.setViewMode(QListWidget.ViewMode.IconMode)
            self.files.setFlow(QListWidget.Flow.LeftToRight)
            self.files.setWrapping(True)
            self.files.setResizeMode(QListWidget.ResizeMode.Adjust)
            self.files.setGridSize(QSize(190, 124))
        else:
            self.files.setViewMode(QListWidget.ViewMode.ListMode)
            self.files.setWrapping(False)
            self.files.setGridSize(QSize())
        self.list_mode.setProperty("selectedMode", mode == "list")
        self.icon_mode.setProperty("selectedMode", mode == "icons")
        self.list_mode.style().unpolish(self.list_mode)
        self.list_mode.style().polish(self.list_mode)
        self.icon_mode.style().unpolish(self.icon_mode)
        self.icon_mode.style().polish(self.icon_mode)
        QTimer.singleShot(0, self._show_visible_thumbnails)

    def _show_visible_thumbnails(self, *_args: object) -> None:
        return qt_media_browser_view._show_visible_thumbnails(self, *_args)

    def _apply_thumbnail(self, generation: int, key: object, picture: object) -> None:
        return qt_media_browser_view._apply_thumbnail(self, generation, key, picture)

    def _selected_file_paths(self) -> list[Path]:
        paths: list[Path] = []
        for item in self.files.selectedItems():
            if bool(item.data(Qt.ItemDataRole.UserRole + 1)):
                continue
            raw = item.data(Qt.ItemDataRole.UserRole)
            if raw:
                paths.append(Path(str(raw)))
        return paths

    def _selection_changed(self) -> None:
        current = self.files.currentItem()
        if current is None:
            self.preview.set_source(None, include_image=False)
            return
        raw = current.data(Qt.ItemDataRole.UserRole)
        is_dir = bool(current.data(Qt.ItemDataRole.UserRole + 1))
        if not raw or is_dir:
            self.preview.set_source(None, include_image=False)
            return
        path = Path(str(raw))
        self.preview.set_source(path, include_image=not self.audio)

    def _activate_item(self, item: QListWidgetItem) -> None:
        raw = item.data(Qt.ItemDataRole.UserRole)
        if not raw:
            return
        path = Path(str(raw))
        if bool(item.data(Qt.ItemDataRole.UserRole + 1)):
            self._navigate(path)
            return
        self._collect_paths([path])

    def _collect_paths(self, paths: list[Path]) -> None:
        known = set(self.collected)
        stale = 0
        for path in paths:
            # Cache entries may have been deleted or replaced with a link while
            # the user was browsing. Never hand such files to the renderer.
            if path.is_symlink() or not path.is_file():
                stale += 1
                continue
            if path not in known:
                self.collected.append(path)
                known.add(path)
        message = f"{len(self.collected)} Datei(en) gesammelt"
        if stale:
            message += f" · {stale} nicht mehr verfügbare Datei(en) übersprungen"
        self.collection_status.setText(message)

    def _collect_selection(self) -> None:
        self._collect_paths(self._selected_file_paths())

    def _accept_selection(self) -> None:
        selected = self._selected_file_paths()
        self._collect_paths(selected)
        # Previously collected files may disappear before the final click.
        self.result = tuple(
            path for path in self.collected if not path.is_symlink() and path.is_file()
        )
        if len(self.result) != len(self.collected):
            self.collection_status.setText(
                "Einige Dateien sind nicht mehr verfügbar. "
                "Bitte die verbleibende Auswahl kontrollieren."
            )
        if not self.result:
            self.status.setText("Noch keine Datei ausgewählt.")
            return
        self.accept()

    def wait(self) -> tuple[Path, ...]:
        if not self.isVisible():
            self.exec()
        return self.result

    def reject(self) -> None:
        self.result = ()
        super().reject()

    def _stop_background_tasks(self, *_args: object) -> None:
        if self._thumb_closing:
            return
        self._scan_cancel.set()
        self._thumb_closing = True
        self._thumb_pool.shutdown(wait=False, cancel_futures=True)
        self.preview.shutdown()

    def closeEvent(self, event) -> None:
        self._stop_background_tasks()
        super().closeEvent(event)
