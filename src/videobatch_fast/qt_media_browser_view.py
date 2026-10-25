from __future__ import annotations
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtWidgets import (
    QListWidget,
    QListWidgetItem,
)
from .media_dialog_support import human_size, sort_directory_records
from .qt_thumbnail_cache import load_thumbnail
from .probe import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS

def _render_records(self) -> None:
    selected = {Path(str(item.data(Qt.ItemDataRole.UserRole))) for item in self.files.selectedItems()}
    query = self.filter_edit.text().strip().casefold()
    key = (self.sort_key, self.sort_reverse, self._records_version)
    if self._sorted_cache_key != key:
        self._sorted_cache = sort_directory_records(
            self._records, self.sort_key, self.sort_reverse
        )
        self._sorted_cache_key = key
    records = self._sorted_cache
    if query:
        records = [record for record in records if query in record.path.name.casefold()]

    total = len(records)
    shown = min(total, self._display_limit)
    self.more_button.setVisible(shown < total)
    if shown < total:
        self.more_button.setText(
            f"Weitere Dateien anzeigen · {shown} von {total} sichtbar"
        )
    scroll = self.files.verticalScrollBar().value()
    self._thumb_generation += 1
    self._thumb_items.clear()
    self._thumb_keys.clear()
    self.files.blockSignals(True)
    self.files.clear()
    for record in records[:shown]:
        if record.is_dir:
            text = f"📁 {record.path.name}"
        else:
            changed = datetime.fromtimestamp(record.modified).strftime("%Y-%m-%d %H:%M")
            text = record.path.name
        item = QListWidgetItem(text)
        item.setData(Qt.ItemDataRole.UserRole, str(record.path))
        item.setData(Qt.ItemDataRole.UserRole + 1, record.is_dir)
        item.setToolTip(
            str(record.path) if record.is_dir else
            f"{record.path}\\n{human_size(record.size)} · {changed}"
        )
        self.files.addItem(item)
        if not record.is_dir:
            filename = str(record.path)
            self._thumb_items[filename] = item
            self._thumb_keys[filename] = (filename, record.size, int(record.modified * 1_000_000_000))
            cached = self._thumb_images.get(self._thumb_keys[filename])
            if cached is not None and not cached.isNull():
                item.setIcon(QIcon(QPixmap.fromImage(cached)))
        if record.path in selected:
            item.setSelected(True)
    self.files.blockSignals(False)
    self.files.verticalScrollBar().setValue(scroll)
    self._selection_changed()
    QTimer.singleShot(0, self._show_visible_thumbnails)

def _show_visible_thumbnails(self, *_args: object) -> None:
    if self._thumb_closing or self.audio or self.files.viewMode() != QListWidget.ViewMode.IconMode:
        return
    current = self.files.indexAt(QPoint(20, 20))
    start = max(0, current.row() - 10) if current.isValid() else max(0, self.files.currentRow())
    viewport = self.files.viewport().rect()
    scheduled = 0
    for row in range(start, min(self.files.count(), start + 120)):
        item = self.files.item(row)
        if not self.files.visualItemRect(item).intersects(viewport):
            continue
        filename = str(item.data(Qt.ItemDataRole.UserRole) or "")
        if Path(filename).suffix.lower() not in (IMAGE_EXTENSIONS | VIDEO_EXTENSIONS):
            continue
        key = self._thumb_keys.get(filename)
        if key is None or key in self._thumb_pending or key in self._thumb_images:
            continue
        self._thumb_pending.add(key)
        generation = self._thumb_generation
        future = self._thumb_pool.submit(load_thumbnail, Path(filename))

        def on_done(fut, image_key=key, token=generation):
            try:
                picture = fut.result()
            except Exception:
                picture = QImage()
            if not self._thumb_closing:
                try:
                    self._thumbReady.emit(token, image_key, picture)
                except RuntimeError:
                    pass

        future.add_done_callback(on_done)
        scheduled += 1
        if scheduled >= 32:
            break

def _apply_thumbnail(self, generation: int, key: object, picture: object) -> None:
    self._thumb_pending.discard(key)
    if generation != self._thumb_generation:
        QTimer.singleShot(0, self._show_visible_thumbnails)
        return
    if not isinstance(picture, QImage) or picture.isNull():
        return
    self._thumb_images[key] = picture
    if len(self._thumb_images) > 256:
        self._thumb_images.pop(next(iter(self._thumb_images)))
    if generation != self._thumb_generation:
        return
    item = self._thumb_items.get(key[0])
    if item is not None and self._thumb_keys.get(key[0]) == key:
        item.setIcon(QIcon(QPixmap.fromImage(picture)))
