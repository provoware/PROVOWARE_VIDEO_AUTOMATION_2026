from __future__ import annotations

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


def media_size_text(size: int) -> str:
    value = float(max(0, size))
    units = ("B", "KB", "MB", "GB", "TB")
    for unit in units:
        if value < 1024.0 or unit == units[-1]:
            return f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{value:.1f} TB"


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
    MIN_ZOOM_POINT_SIZE = 10.0
    MAX_ZOOM_POINT_SIZE = 22.0

    def __init__(self, extensions: set[str]) -> None:
        super().__init__()
        self.extensions = {value.lower() for value in extensions}
        self._production_paths: list[str] = []
        self._zoom_point_size = max(
            self.MIN_ZOOM_POINT_SIZE,
            min(self.MAX_ZOOM_POINT_SIZE, float(self.font().pointSizeF() or 11.0)),
        )
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setIconSize(QSize(72, 54))
        self.setToolTip(
            "Strg + Mausrad oder Strg +/-: Liste vergrößern oder verkleinern · "
            "Strg+0: Normalgröße · Entf: Auswahl entfernen"
        )
        self.setAccessibleDescription(
            "Dateiliste. Mit Entf wird die Auswahl entfernt. "
            "Mit Strg plus oder minus wird die Liste vergrößert oder verkleinert."
        )

    def paths(self) -> list[Path]:
        return [Path(self.item(row).data(Qt.ItemDataRole.UserRole)) for row in range(self.count())]

    def production_paths(self) -> list[Path]:
        return [Path(value) for value in self._production_paths]

    def clear(self) -> None:
        super().clear()
        self._production_paths.clear()

    def add_paths(self, paths: list[Path]) -> None:
        known = {str(path) for path in self.paths()}
        added = False
        for candidate in paths:
            path = candidate.expanduser()
            if not path.is_file() or path.suffix.lower() not in self.extensions:
                continue
            resolved = str(path.resolve())
            if resolved in known:
                continue
            item = QListWidgetItem(media_path_display_text(path))
            item.setData(Qt.ItemDataRole.UserRole, resolved)
            item.setToolTip(resolved)
            if path.suffix.lower() in IMAGE_THUMBNAIL_EXTS:
                pixmap = QPixmap(resolved)
                if not pixmap.isNull():
                    item.setIcon(QIcon(pixmap))
            self.addItem(item)
            known.add(resolved)
            self._production_paths.append(resolved)
            added = True
        if added:
            self.changed.emit()

    def remove_selected(self) -> None:
        selected = {
            str(item.data(Qt.ItemDataRole.UserRole))
            for item in self.selectedItems()
        }
        rows = sorted((self.row(item) for item in self.selectedItems()), reverse=True)
        for row in rows:
            self.takeItem(row)
        if rows:
            self._production_paths = [value for value in self._production_paths if value not in selected]
            self.changed.emit()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        event.acceptProposedAction() if event.mimeData().hasUrls() else event.ignore()

    def dragMoveEvent(self, event) -> None:
        event.acceptProposedAction() if event.mimeData().hasUrls() else event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        self.add_paths([Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()])
        event.acceptProposedAction()

    def zoom_percent(self) -> int:
        return int(round(self._zoom_point_size / 11.0 * 100))

    def _apply_zoom(self, point_size: float) -> None:
        bounded = max(self.MIN_ZOOM_POINT_SIZE, min(self.MAX_ZOOM_POINT_SIZE, point_size))
        if abs(bounded - self._zoom_point_size) < 0.01:
            return
        self._zoom_point_size = bounded
        font = self.font()
        font.setPointSizeF(bounded)
        self.setFont(font)
        scale = bounded / 11.0
        self.setIconSize(QSize(max(48, round(72 * scale)), max(36, round(54 * scale))))
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
                self._apply_zoom(11.0)
                event.accept()
                return
        super().keyPressEvent(event)

    def sort_by(self, mode: str) -> None:
        selected = {str(item.data(Qt.ItemDataRole.UserRole)) for item in self.selectedItems()}
        current = self.currentItem()
        current_path = str(current.data(Qt.ItemDataRole.UserRole)) if current is not None else ""
        ordered = sorted(self.paths(), key=lambda path: media_path_sort_key(path, mode))
        if ordered == self.paths():
            return
        production_order = list(self._production_paths)
        self.blockSignals(True)
        try:
            self.clear()
            self.add_paths(ordered)
            self._production_paths = production_order
            for row in range(self.count()):
                item = self.item(row)
                raw = str(item.data(Qt.ItemDataRole.UserRole))
                item.setSelected(raw in selected)
                if raw == current_path:
                    self.setCurrentItem(item)
        finally:
            self.blockSignals(False)
        self.changed.emit()
