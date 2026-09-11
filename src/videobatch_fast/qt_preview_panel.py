from __future__ import annotations

import queue
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QResizeEvent
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from .event_buffer import EventBuffer
from .selection_preview_controller import SelectionPreviewController


def _human_size(value: int) -> str:
    size = float(max(0, value))
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024.0 or unit == "TiB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TiB"


def _duration_text(seconds: float | None) -> str:
    if seconds is None or seconds < 0:
        return "—"
    minutes, rest = divmod(round(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:d}:{minutes:02d}:{rest:02d}"
    return f"{minutes:d}:{rest:02d}"


class PreviewPanel(QFrame):
    """Thread-safe Qt preview using the canonical typed EventBuffer boundary."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("panel")
        self._pixmap: QPixmap | None = None
        self._path: Path | None = None
        self._token = 0
        self._events = EventBuffer(maxsize=64)
        self._controller = SelectionPreviewController(self._events.put)
        self._preview_timer = QTimer(self)
        self._preview_timer.setInterval(40)
        self._preview_timer.timeout.connect(self._poll_preview_events)
        self._preview_timer.start()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        title = QLabel("Live-Vorschau")
        title.setObjectName("section")
        layout.addWidget(title)

        self.image = QLabel("Datei auswählen")
        self.image.setObjectName("previewSurface")
        self.image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image.setMinimumHeight(220)
        self.image.setWordWrap(True)
        layout.addWidget(self.image, 1)

        self.name = QLabel("Noch keine Auswahl")
        self.name.setObjectName("section")
        self.name.setWordWrap(True)
        layout.addWidget(self.name)

        self.meta = QLabel("Bild, Video oder Audio anklicken.")
        self.meta.setObjectName("subtitle")
        self.meta.setWordWrap(True)
        layout.addWidget(self.meta)

    def set_source(self, path: Path | None, *, include_image: bool) -> None:
        self._path = Path(path) if path is not None else None
        self._pixmap = None
        self.image.setPixmap(QPixmap())
        if self._path is None:
            self._token = self._controller.invalidate()
            self.image.setText("Datei auswählen")
            self.name.setText("Noch keine Auswahl")
            self.meta.setText("Bild, Video oder Audio anklicken.")
            return
        self.image.setText("Vorschau wird erzeugt …" if include_image else "Metadaten werden gelesen …")
        self.name.setText(self._path.name)
        self.meta.setText(str(self._path))
        width = max(640, self.image.width() * 2)
        self._token = self._controller.request(self._path, width, include_image=include_image)

    def shutdown(self) -> bool:
        self._preview_timer.stop()
        return self._controller.shutdown(timeout=3.0)

    def _poll_preview_events(self) -> None:
        for _ in range(16):
            try:
                event = self._events.get_nowait()
            except queue.Empty:
                break
            self._handle_event(event)

    def _handle_event(self, event: object) -> None:
        name = getattr(event, "name", "")
        payload = getattr(event, "payload", {})
        token = int(payload.get("token", -1))
        if token != self._token:
            return
        if name == "selection_preview_failed":
            message = str(payload.get("message", "Vorschau nicht verfügbar."))
            self._pixmap = None
            self.image.setPixmap(QPixmap())
            self.image.setText("Keine Bildvorschau")
            self.meta.setText(message)
            return
        if name != "selection_preview_ready":
            return

        path = Path(payload["path"])
        if self._path is None or path != self._path:
            return
        info = payload["info"]
        preview = payload.get("preview")
        size_bytes = int(payload.get("size_bytes", 0) or 0)

        dimensions = "—"
        width = getattr(info, "width", None)
        height = getattr(info, "height", None)
        if width and height:
            dimensions = f"{width} × {height}"
        codec = str(getattr(info, "codec", "") or "—")
        kind = str(getattr(info, "kind", "") or "unbekannt")
        duration = _duration_text(getattr(info, "duration", None))
        self.name.setText(path.name)
        self.meta.setText(
            f"Art: {kind} · Dauer: {duration}\n"
            f"Auflösung: {dimensions} · Codec: {codec}\n"
            f"Größe: {_human_size(size_bytes)}\n{path}"
        )

        if preview:
            pixmap = QPixmap(str(preview))
            if not pixmap.isNull():
                self._pixmap = pixmap
                self.image.setText("")
                self._render_pixmap()
                return
        self._pixmap = None
        self.image.setPixmap(QPixmap())
        self.image.setText("Keine Bildvorschau für diese Datei")

    def _render_pixmap(self) -> None:
        if self._pixmap is None or self._pixmap.isNull():
            return
        size = self.image.size()
        target = self._pixmap.scaled(
            max(64, size.width() - 12),
            max(64, size.height() - 12),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image.setPixmap(target)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._render_pixmap()

