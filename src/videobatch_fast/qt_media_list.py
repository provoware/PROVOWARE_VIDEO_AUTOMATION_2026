from __future__ import annotations

from .display_formatting import media_size_text

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QIcon, QKeyEvent, QPixmap, QWheelEvent
from PySide6.QtWidgets import QAbstractItemView, QListWidget, QListWidgetItem

AUDIO_EXTS = {".aac", ".flac", ".m4a", ".mp3", ".ogg", ".opus", ".wav", ".wma"}
MEDIA_EXTS = {
    ".avif", ".bmp", ".gif", ".jpeg", ".jpg", ".mkv", ".mov", ".mp4",
    ".mpeg", ".mpg", ".png", ".tif", ".tiff", ".webm", ".webp",
}
SORT_MODES = (
    ("Name A–Z", "name"),
    ("Änderung neu → alt", "modified"),
    ("Größe groß → klein", "size"),
)
IMAGE_THUMBNAIL_EXTS = {
    ".avif", ".bmp", ".gif", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp",
}





def media_path_display_text(path: Path) -> str:
    try:
        stat = path.stat()
        changed = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
        return f"{path.name}\n{media_size_text(stat.st_size)} · geändert {changed}"
    except OSError:
        return f"{path.name}\nGröße / Änderungsdatum nicht verfügbar"


def media_path_sort_key(path: Path, mode: str) -> tuple[object, ...]:
    try:
        stat = path.stat()
        modified = float(stat.st_mtime)
        size = int(stat.st_size)
    except OSError:
        modified = 0.0
        size = -1
    stable = (path.name.casefold(), str(path).casefold())
    if mode == "modified":
        return (-modified, *stable)
    if mode == "size":
        return (-size, *stable)
    return stable


class DropList(QListWidget):
    changed = Signal()
    zoomChanged = Signal(int)
    MIN_ZOOM_POINT_SIZE = 12.0
    MAX_ZOOM_POINT_SIZE = 24.0

    def __init__(self, extensions: set[str]) -> None:
        super().__init__()
        self.extensions = {value.lower() for value in extensions}
        self._production_paths: list[str] = []
        self._parity_production_paths: list[Path] = []
        self._parity_view_sort = "import"
        self._zoom_point_size = max(
            self.MIN_ZOOM_POINT_SIZE,
            min(self.MAX_ZOOM_POINT_SIZE, float(self.font().pointSizeF() or 12.0)),
        )
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setIconSize(QSize(48, 36))
        self.setToolTip(
            "Strg + Mausrad oder Strg +/-: Liste vergrößern oder verkleinern · "
            "Strg+0: Normalgröße · Entf: Auswahl entfernen"
        )
        self.setAccessibleDescription(
            "Dateiliste. Mit Entf wird die Auswahl entfernt. "
            "Mit Strg plus oder minus wird die Liste vergrößert oder verkleinert."
        )

    def _visible_paths(self) -> list[Path]:
        """Only the visible list, never the authoritative production order."""
        return [
            Path(str(self.item(row).data(Qt.ItemDataRole.UserRole)))
            for row in range(self.count())
            if self.item(row).data(Qt.ItemDataRole.UserRole)
        ]

    def paths(self) -> list[Path]:
        """Preserve the explicit production order even when the view is sorted."""
        return self.production_paths()

    def production_paths(self) -> list[Path]:
        return list(self._parity_production_paths)

    def apply_view_as_production_order(self) -> None:
        displayed = self._visible_paths()
        self._parity_production_paths = list(displayed)
        self._production_paths = [str(path) for path in displayed]
        self.changed.emit()

    def render_view(self) -> None:
        """Rebuild the sorted presentation without mutating output sequencing."""
        from .media_library import sort_paths

        selected = {
            Path(str(item.data(Qt.ItemDataRole.UserRole)))
            for item in self.selectedItems()
            if item.data(Qt.ItemDataRole.UserRole)
        }
        order = self.production_paths()
        mode = str(getattr(self, "_parity_view_sort", "import") or "import")
        displayed = sort_paths(order, mode) if mode != "import" else order
        previous_block = self.blockSignals(True)
        try:
            QListWidget.clear(self)
            for path in displayed:
                item = QListWidgetItem(path.name)
                item.setData(Qt.ItemDataRole.UserRole, str(path))
                item.setToolTip(str(path))
                self.addItem(item)
                if path in selected:
                    item.setSelected(True)
        finally:
            self.blockSignals(previous_block)

    def clear(self) -> None:
        self._parity_production_paths = []
        self._production_paths = []
        QListWidget.clear(self)

    def add_paths(self, paths: list[Path]) -> None:
        production = self.production_paths()
        known = {str(path) for path in production}
        added = False
        for candidate in paths:
            path = Path(candidate).expanduser()
            if not path.is_file() or path.suffix.lower() not in self.extensions:
                continue
            resolved = path.resolve()
            if str(resolved) in known:
                continue
            production.append(resolved)
            known.add(str(resolved))
            added = True
        if added:
            self._parity_production_paths = production
            self._production_paths = [str(path) for path in production]
            self.render_view()
            self.changed.emit()

    def remove_selected(self) -> None:
        selected = {
            Path(str(item.data(Qt.ItemDataRole.UserRole)))
            for item in self.selectedItems()
            if item.data(Qt.ItemDataRole.UserRole)
        }
        if not selected:
            return
        new_order = [path for path in self.production_paths() if path not in selected]
        self._parity_production_paths = new_order
        self._production_paths = [str(path) for path in new_order]
        self.render_view()
        self.changed.emit()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        event.acceptProposedAction() if event.mimeData().hasUrls() else event.ignore()

    def dragMoveEvent(self, event) -> None:
        event.acceptProposedAction() if event.mimeData().hasUrls() else event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        self.add_paths([Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()])
        event.acceptProposedAction()

    def zoom_percent(self) -> int:
        return int(round(self._zoom_point_size / 12.0 * 100))

    def _apply_zoom(self, point_size: float) -> None:
        bounded = max(self.MIN_ZOOM_POINT_SIZE, min(self.MAX_ZOOM_POINT_SIZE, point_size))
        if abs(bounded - self._zoom_point_size) < 0.01:
            return
        self._zoom_point_size = bounded
        font = self.font()
        font.setPointSizeF(bounded)
        self.setFont(font)
        scale = bounded / 12.0
        self.setIconSize(QSize(max(48, round(48 * scale)), max(36, round(36 * scale))))
        self.setSpacing(max(2, int(round((bounded - self.MIN_ZOOM_POINT_SIZE) / 2.0)) + 2))
        self.zoomChanged.emit(self.zoom_percent())

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y() or event.pixelDelta().y()
            if delta:
                self._apply_zoom(self._zoom_point_size + (1.0 if delta > 0 else -1.0))
            event.accept()
            return
        super().wheelEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Delete:
            self.remove_selected()
            event.accept()
            return
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.key() in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
                self._apply_zoom(self._zoom_point_size + 1.0)
                event.accept()
                return
            if event.key() == Qt.Key.Key_Minus:
                self._apply_zoom(self._zoom_point_size - 1.0)
                event.accept()
                return
            if event.key() == Qt.Key.Key_0:
                self._apply_zoom(12.0)
                event.accept()
                return
        super().keyPressEvent(event)
    def sort_by(self, mode: str) -> None:
        """Sort the view only. Persist the selection without changing jobs."""
        from .media_library import SORT_KEYS
        from .qt_legacy_parity_completion import _save_config, _select_combo_data

        key = {"name": "name_asc", "modified": "modified_new", "size": "size_desc"}.get(mode, mode)
        if key not in SORT_KEYS:
            return
        self._parity_view_sort = key
        self.render_view()
        window = self.window()
        is_audio = self is getattr(window, "audio", None)
        combo = getattr(window, "parity_audio_sort" if is_audio else "parity_media_sort", None)
        if combo is not None:
            was_blocked = combo.blockSignals(True)
            try:
                _select_combo_data(combo, key)
            finally:
                combo.blockSignals(was_blocked)
        _save_config(window, **{("audio_sort" if is_audio else "media_sort"): key})
        if hasattr(window, "_project_dirty"):
            window._project_dirty = True
        if hasattr(window, "next_step"):
            window.next_step.setText(
                "Sortierung geändert: nur die Ansicht. Die Produktionsreihenfolge bleibt unverändert."
            )

