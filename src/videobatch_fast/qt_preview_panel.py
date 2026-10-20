from __future__ import annotations

import queue
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QResizeEvent
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QSizePolicy, QSpinBox, QVBoxLayout, QWidget,
)

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

        self._init_parity_controls()

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

    def _init_parity_controls(self) -> None:
        """Native preview controls: no import-time method replacement."""
        self._parity_zoom = 100
        self._parity_fit = True
        layout = self.layout()
        index = layout.indexOf(self.image)
        layout.removeWidget(self.image)
        self.image.setMinimumSize(64, 64)
        self.image.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        scroll = QScrollArea(self)
        scroll.setObjectName("previewScroll")
        scroll.setWidgetResizable(False)
        scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(self.image)
        layout.insertWidget(max(1, index), scroll, 1)
        self._parity_scroll = scroll

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Zoom"))
        self.parity_zoom = QSpinBox()
        self.parity_zoom.setRange(25, 800)
        self.parity_zoom.setSingleStep(25)
        self.parity_zoom.setSuffix(" %")
        self.parity_zoom.setValue(100)
        minus = QPushButton("−")
        plus = QPushButton("+")
        fit_button = QPushButton("Einpassen")
        fullscreen_button = QPushButton("Vollbild")
        for control in (minus, self.parity_zoom, plus, fit_button, fullscreen_button):
            controls.addWidget(control)
        controls.addStretch()
        layout.addLayout(controls)
        self.parity_zoom.valueChanged.connect(self.set_parity_zoom)
        minus.clicked.connect(lambda: self.set_parity_zoom(self.parity_zoom.value() - 25))
        plus.clicked.connect(lambda: self.set_parity_zoom(self.parity_zoom.value() + 25))
        fit_button.clicked.connect(self.fit_parity_preview)
        fullscreen_button.clicked.connect(self.open_parity_fullscreen)
        self._parity_fit_button = fit_button
        self._parity_fullscreen_button = fullscreen_button

    def _render_pixmap(self) -> None:
        pixmap = self._pixmap
        if pixmap is None or pixmap.isNull():
            return
        scroll = self._parity_scroll
        if self._parity_fit:
            viewport = scroll.viewport().size()
            target = pixmap.scaled(
                max(64, viewport.width() - 12), max(64, viewport.height() - 12),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        else:
            factor = max(0.25, min(8.0, self._parity_zoom / 100.0))
            target = pixmap.scaled(
                max(1, round(pixmap.width() * factor)),
                max(1, round(pixmap.height() * factor)),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        self.image.setPixmap(target)
        self.image.resize(target.size())

    def set_parity_zoom(self, value: int, *, persist: bool = True) -> None:
        self._parity_zoom = max(25, min(800, int(value)))
        self._parity_fit = False
        was_blocked = self.parity_zoom.blockSignals(True)
        try:
            self.parity_zoom.setValue(self._parity_zoom)
        finally:
            self.parity_zoom.blockSignals(was_blocked)
        self._render_pixmap()
        if persist:
            from .qt_legacy_parity_completion import _preview_save_zoom

            _preview_save_zoom(self)

    def fit_parity_preview(self) -> None:
        self._parity_fit = True
        self._render_pixmap()

    def open_parity_fullscreen(self) -> None:
        if self._pixmap is None or self._pixmap.isNull():
            return
        from .qt_legacy_parity_completion import _PreviewFullscreenDialog

        _PreviewFullscreenDialog(self).exec()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._render_pixmap()

