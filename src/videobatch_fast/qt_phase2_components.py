from __future__ import annotations

import random
import threading
import time
from pathlib import Path

from PySide6.QtCore import QPointF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .audio_waveform import WaveformAnalysis, analyze_audio
from .probe import IMAGE_EXTENSIONS
from .qt_preview_panel import PreviewPanel
from .slideshow import (
    SLIDESHOW_MODE_ALL_IMAGES,
    SLIDESHOW_MODE_PAIRWISE,
    TRANSITION_LABELS,
    slideshow_summary,
)
from .slideshow_sequence import (
    ORDER_ALPHABETICAL,
    ORDER_CAPTURE_DATE,
    ORDER_MANUAL,
    ORDER_RANDOM,
    apply_anchors,
    order_images,
    reverse_images,
)


def _duration_text(seconds: float | None) -> str:
    if seconds is None or seconds < 0:
        return "—"
    minutes, rest = divmod(round(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:d}:{minutes:02d}:{rest:02d}"
    return f"{minutes:d}:{rest:02d}"


class ThumbnailOrderStrip(QListWidget):
    """Qt replacement for the Tk canvas thumbnail strip."""

    orderChanged = Signal(object)
    selectedPathChanged = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._start: Path | None = None
        self._end: Path | None = None
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setFlow(QListWidget.Flow.LeftToRight)
        self.setWrapping(False)
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setMovement(QListWidget.Movement.Snap)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setIconSize(QSize(126, 84))
        self.setMinimumHeight(150)
        self.currentItemChanged.connect(self._emit_selection)

    def paths(self) -> list[Path]:
        result: list[Path] = []
        for row in range(self.count()):
            item = self.item(row)
            raw = item.data(Qt.ItemDataRole.UserRole)
            if raw:
                result.append(Path(str(raw)))
        return result

    @property
    def selected_path(self) -> Path | None:
        item = self.currentItem()
        raw = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        return Path(str(raw)) if raw else None

    def set_items(
        self,
        paths: list[Path],
        *,
        start: Path | None = None,
        end: Path | None = None,
    ) -> None:
        previous = self.selected_path
        self._start = start if start in paths else None
        self._end = end if end in paths else None
        self.clear()
        for index, path in enumerate(paths, start=1):
            badges: list[str] = []
            if path == self._start:
                badges.append("START")
            if path == self._end:
                badges.append("ENDE")
            suffix = f"\n{' · '.join(badges)}" if badges else ""
            item = QListWidgetItem(f"{index}. {path.name}{suffix}")
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            item.setToolTip(str(path))
            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                item.setIcon(QIcon(pixmap))
            self.addItem(item)
            if previous == path:
                self.setCurrentItem(item)
        if self.currentItem() is None and self.count():
            self.setCurrentRow(0)

    def dropEvent(self, event) -> None:
        super().dropEvent(event)
        self.orderChanged.emit(self.paths())

    def _emit_selection(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        raw = current.data(Qt.ItemDataRole.UserRole) if current is not None else None
        self.selectedPathChanged.emit(Path(str(raw)) if raw else None)


class WaveformSceneView(QWidget):
    """Qt/QPainter waveform with the same scene-marker semantics as the Tk view."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.analysis: WaveformAnalysis | None = None
        self.setMinimumHeight(230)

    def set_analysis(self, analysis: WaveformAnalysis | None) -> None:
        self.analysis = analysis
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        width = max(1, self.width())
        height = max(1, self.height())
        middle = height * 0.57

        painter.fillRect(self.rect(), QColor("#0a1119"))
        painter.setPen(QPen(QColor("#273244"), 1))
        painter.drawLine(0, int(middle), width, int(middle))

        analysis = self.analysis
        if analysis is None or not analysis.peaks:
            painter.setPen(QColor("#9eabc0"))
            painter.drawText(18, 30, "Audio auswählen und analysieren.")
            return

        peaks = analysis.peaks
        step = width / max(1, len(peaks) - 1)
        amplitude = height * 0.34
        upper = QPolygonF(
            [QPointF(index * step, middle - max(1.0, value * amplitude)) for index, value in enumerate(peaks)]
        )
        lower = QPolygonF(
            [QPointF(index * step, middle + max(1.0, value * amplitude * 0.55)) for index, value in enumerate(peaks)]
        )
        painter.setPen(QPen(QColor("#55b7ff"), 2))
        painter.drawPolyline(upper)
        painter.setPen(QPen(QColor("#316bf4"), 1))
        painter.drawPolyline(lower)

        marker_colors = {
            "intro": "#54d39a",
            "beat": "#55b7ff",
            "quiet": "#e6b84a",
            "drop": "#ff667f",
            "outro": "#9f7aea",
        }
        for row, marker in enumerate(analysis.markers):
            x = width * marker.time_seconds / max(analysis.duration, 0.001)
            color = QColor(marker_colors.get(marker.kind, "#e9eef7"))
            pen = QPen(color, 2)
            pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.drawLine(int(x), 12, int(x), height - 18)
            minutes, seconds = divmod(round(marker.time_seconds), 60)
            label = f"{marker.label} · {minutes}:{seconds:02d}"
            text_x = min(max(4, int(x) + 5), max(4, width - 190))
            painter.drawText(text_x, 26 + (row % 2) * 19, label)


class SlideshowPanel(QFrame):
    """Complete Qt slideshow/order/waveform workflow backed by existing core modules."""

    stateChanged = Signal()
    orderChanged = Signal(object)
    analysisChanged = Signal()

    _analysisResult = Signal(object, object, str, int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("panel")
        self._audios: list[Path] = []
        self._media: list[Path] = []
        self._analyses: dict[Path, WaveformAnalysis] = {}
        self._analysis_failures: dict[Path, str] = {}
        self._pending: set[Path] = set()
        self._analysis_generation = 0
        self._start_image: Path | None = None
        self._end_image: Path | None = None
        self._selected_image: Path | None = None
        self._manual_seed = random.randrange(1, 2**31 - 1)
        self._build()
        self._analysisResult.connect(self._finish_analysis)

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QLabel("Diashow & Szenen")
        title.setObjectName("section")
        layout.addWidget(title)
        intro = QLabel(
            "Die drei Grundoptionen bleiben immer sichtbar. Reihenfolge und Waveform sind Zusatzwerkzeuge darunter."
        )
        intro.setObjectName("subtitle")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Zuordnung"))
        self.assignment = QComboBox()
        self.assignment.addItem("Paarweise", SLIDESHOW_MODE_PAIRWISE)
        self.assignment.addItem("Alle Bilder je Audio", SLIDESHOW_MODE_ALL_IMAGES)
        mode_row.addWidget(self.assignment, 1)
        layout.addLayout(mode_row)

        transition_row = QHBoxLayout()
        transition_row.addWidget(QLabel("Überblendung"))
        self.transition = QComboBox()
        for key, label in TRANSITION_LABELS.items():
            self.transition.addItem(label, key)
        transition_row.addWidget(self.transition, 1)
        layout.addLayout(transition_row)

        self.scene_sync = QCheckBox("Bildwechsel an erkannten Szenen ausrichten")
        layout.addWidget(self.scene_sync)

        self.summary = QLabel()
        self.summary.setObjectName("safeHint")
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)

        advanced_title = QLabel("Weitere Diashow-Werkzeuge")
        advanced_title.setObjectName("section")
        layout.addWidget(advanced_title)

        scroll = QScrollArea()
        scroll.setObjectName("secondaryScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        advanced_content = QWidget()
        advanced = QVBoxLayout(advanced_content)
        advanced.setContentsMargins(0, 0, 6, 0)
        advanced.setSpacing(8)

        order_hint = QLabel("Optional: Bildreihenfolge ändern")
        order_hint.setObjectName("subtitle")
        advanced.addWidget(order_hint)
        order_buttons = QHBoxLayout()
        for text, callback in (
            ("A–Z", lambda: self._apply_order(ORDER_ALPHABETICAL)),
            ("Aufnahmezeit", lambda: self._apply_order(ORDER_CAPTURE_DATE)),
            ("Zufall", lambda: self._apply_order(ORDER_RANDOM)),
            ("Umkehren", self._reverse),
        ):
            button = QPushButton(text)
            button.clicked.connect(callback)
            order_buttons.addWidget(button)
        advanced.addLayout(order_buttons)

        anchor_buttons = QHBoxLayout()
        start_button = QPushButton("Als START")
        end_button = QPushButton("Als ENDE")
        clear_button = QPushButton("Anker löschen")
        start_button.clicked.connect(lambda: self._set_anchor("start"))
        end_button.clicked.connect(lambda: self._set_anchor("end"))
        clear_button.clicked.connect(self._clear_anchors)
        anchor_buttons.addWidget(start_button)
        anchor_buttons.addWidget(end_button)
        anchor_buttons.addWidget(clear_button)
        advanced.addLayout(anchor_buttons)

        self.strip = ThumbnailOrderStrip()
        self.strip.setMinimumHeight(130)
        self.strip.orderChanged.connect(self._manual_order)
        self.strip.selectedPathChanged.connect(self._select_image)
        advanced.addWidget(self.strip)

        self.order_status = QLabel("Noch keine Bilder.")
        self.order_status.setObjectName("subtitle")
        self.order_status.setWordWrap(True)
        advanced.addWidget(self.order_status)

        audio_hint = QLabel("Optional: Audioanalyse / Waveform")
        audio_hint.setObjectName("subtitle")
        advanced.addWidget(audio_hint)
        audio_row = QHBoxLayout()
        audio_row.addWidget(QLabel("Waveform-Audio"))
        self.audio_select = QComboBox()
        audio_row.addWidget(self.audio_select, 1)
        self.analyze = QPushButton("Analysieren")
        audio_row.addWidget(self.analyze)
        advanced.addLayout(audio_row)

        self.waveform = WaveformSceneView()
        self.waveform.setMinimumHeight(190)
        advanced.addWidget(self.waveform)

        self.analysis_status = QLabel("Noch keine Audioanalyse.")
        self.analysis_status.setObjectName("subtitle")
        self.analysis_status.setWordWrap(True)
        advanced.addWidget(self.analysis_status)
        advanced.addStretch()

        scroll.setWidget(advanced_content)
        layout.addWidget(scroll, 1)

        self.assignment.currentIndexChanged.connect(self._state_changed)
        self.transition.currentIndexChanged.connect(self._state_changed)
        self.scene_sync.toggled.connect(self._scene_sync_changed)
        self.audio_select.currentIndexChanged.connect(self._audio_changed)
        self.analyze.clicked.connect(lambda: self.analyze_selected(refresh=True))

    @property
    def assignment_mode(self) -> str:
        return str(self.assignment.currentData() or SLIDESHOW_MODE_PAIRWISE)

    @property
    def transition_preset(self) -> str:
        return str(self.transition.currentData() or "auto")

    @property
    def scene_sync_enabled(self) -> bool:
        return bool(self.scene_sync.isChecked())

    @property
    def pending_analysis(self) -> bool:
        return bool(self._pending)

    def scene_analyses(self) -> dict[Path, WaveformAnalysis]:
        return {path: value for path, value in self._analyses.items() if path in self._audios}

    def missing_scene_analyses(self) -> list[Path]:
        if not self.scene_sync_enabled:
            return []
        return [path for path in self._audios if path not in self._analyses and path not in self._analysis_failures]

    def set_sources(self, audios: list[Path], media: list[Path]) -> None:
        self._audios = list(audios)
        self._media = list(media)
        images = self.image_paths()
        self._start_image = self._start_image if self._start_image in images else None
        self._end_image = self._end_image if self._end_image in images else None
        self._analyses = {path: value for path, value in self._analyses.items() if path in self._audios}
        self._analysis_failures = {path: value for path, value in self._analysis_failures.items() if path in self._audios}
        self._refresh_strip()
        self._refresh_audio_combo()
        self._refresh_summary()
        if self.scene_sync_enabled:
            self.ensure_scene_analyses()

    def image_paths(self) -> list[Path]:
        return [path for path in self._media if path.suffix.lower() in IMAGE_EXTENSIONS]

    def ensure_scene_analyses(self) -> None:
        if not self.scene_sync_enabled:
            return
        for path in self._audios:
            if path not in self._analyses and path not in self._analysis_failures and path not in self._pending:
                self._queue_analysis(path, refresh=False)

    def analyze_selected(self, *, refresh: bool = False) -> None:
        raw = self.audio_select.currentData()
        path = Path(str(raw)) if raw else (self._audios[0] if self._audios else None)
        if path is None:
            self.analysis_status.setText("Bitte zuerst Audio hinzufügen.")
            return
        self._queue_analysis(path, refresh=refresh)

    def _queue_analysis(self, path: Path, *, refresh: bool) -> None:
        if path in self._pending:
            return
        if path in self._analyses and not refresh:
            self._show_analysis(path)
            return
        if refresh:
            self._analyses.pop(path, None)
            self._analysis_failures.pop(path, None)
        self._pending.add(path)
        generation = self._analysis_generation
        self.analysis_status.setText(f"Analysiere {path.name} …")
        self.analyze.setEnabled(False)

        def worker() -> None:
            try:
                analysis = analyze_audio(path, refresh=refresh)
                self._analysisResult.emit(path, analysis, "", generation)
            except Exception as exc:
                self._analysisResult.emit(path, None, f"{type(exc).__name__}: {exc}", generation)

        threading.Thread(
            target=worker,
            daemon=True,
            name=f"VideoBatch-Qt-Waveform-{abs(hash(path))}",
        ).start()

    def _finish_analysis(
        self,
        path_object: object,
        analysis_object: object,
        error: str,
        generation: int,
    ) -> None:
        path = Path(path_object)
        self._pending.discard(path)
        self.analyze.setEnabled(True)
        if generation != self._analysis_generation or path not in self._audios:
            return
        if error or not isinstance(analysis_object, WaveformAnalysis):
            self._analysis_failures[path] = error or "Audioanalyse fehlgeschlagen."
            self.analysis_status.setText(f"Analyse nicht verfügbar: {self._analysis_failures[path]}")
            if self._current_audio_path() == path:
                self.waveform.set_analysis(None)
        else:
            self._analysis_failures.pop(path, None)
            self._analyses[path] = analysis_object
            self._show_analysis(path)
        self._refresh_summary()
        self.analysisChanged.emit()
        self.stateChanged.emit()

    def _current_audio_path(self) -> Path | None:
        raw = self.audio_select.currentData()
        return Path(str(raw)) if raw else None

    def _show_analysis(self, path: Path) -> None:
        analysis = self._analyses.get(path)
        self.waveform.set_analysis(analysis)
        if analysis is None:
            failure = self._analysis_failures.get(path)
            self.analysis_status.setText(failure or "Noch nicht analysiert.")
            return
        labels = " · ".join(marker.label for marker in analysis.markers) or "keine Marker"
        self.analysis_status.setText(
            f"{path.name} · {_duration_text(analysis.duration)} · "
            f"{len(analysis.peaks)} Punkte · {labels}"
        )

    def _refresh_audio_combo(self) -> None:
        selected = self._current_audio_path()
        self.audio_select.blockSignals(True)
        self.audio_select.clear()
        for index, path in enumerate(self._audios, start=1):
            self.audio_select.addItem(f"{index:02d} · {path.name}", str(path))
        if selected in self._audios:
            index = self.audio_select.findData(str(selected))
            self.audio_select.setCurrentIndex(max(0, index))
        self.audio_select.blockSignals(False)
        self._audio_changed()

    def _audio_changed(self) -> None:
        path = self._current_audio_path()
        if path is None:
            self.waveform.set_analysis(None)
            self.analysis_status.setText("Noch kein Audio gewählt.")
        else:
            self._show_analysis(path)
            if self.scene_sync_enabled and path not in self._analyses:
                self._queue_analysis(path, refresh=False)
        self._refresh_summary()

    def _scene_sync_changed(self, enabled: bool) -> None:
        if enabled:
            self.ensure_scene_analyses()
        self._state_changed()

    def _state_changed(self) -> None:
        self._refresh_summary()
        self.stateChanged.emit()

    def _select_image(self, path: object) -> None:
        self._selected_image = Path(path) if path else None

    def _set_anchor(self, kind: str) -> None:
        path = self._selected_image
        images = self.image_paths()
        if path is None or path not in images:
            self.order_status.setText("Zuerst ein Bild in der Leiste auswählen.")
            return
        if kind == "start":
            self._start_image = path
            if self._end_image == path:
                self._end_image = None
        else:
            self._end_image = path
            if self._start_image == path:
                self._start_image = None
        ordered = apply_anchors(images, start_image=self._start_image, end_image=self._end_image)
        self._commit_order(ordered, f"{path.name} als {kind.upper()} gesetzt.")

    def _clear_anchors(self) -> None:
        self._start_image = None
        self._end_image = None
        self._refresh_strip()
        self.order_status.setText("Start-/Endanker gelöscht.")
        self.stateChanged.emit()

    def _apply_order(self, mode: str) -> None:
        images = self.image_paths()
        if not images:
            self.order_status.setText("Noch keine Bilder vorhanden.")
            return
        if mode == ORDER_RANDOM:
            self._manual_seed = int(time.time_ns() & 0x7FFFFFFF)
        ordered = order_images(
            images,
            mode,
            random_seed=self._manual_seed,
            start_image=self._start_image,
            end_image=self._end_image,
        )
        self._commit_order(ordered, f"{len(ordered)} Bilder neu sortiert.")

    def _reverse(self) -> None:
        images = self.image_paths()
        if not images:
            return
        ordered = reverse_images(
            images,
            start_image=self._start_image,
            end_image=self._end_image,
        )
        self._commit_order(ordered, f"{len(ordered)} Bilder umgekehrt.")

    def _manual_order(self, raw_paths: object) -> None:
        paths = [Path(value) for value in list(raw_paths)]
        ordered = apply_anchors(paths, start_image=self._start_image, end_image=self._end_image)
        self._commit_order(ordered, "Manuelle Reihenfolge übernommen.", mode=ORDER_MANUAL)

    def _commit_order(self, ordered: list[Path], message: str, *, mode: str = ORDER_MANUAL) -> None:
        del mode
        self.order_status.setText(message)
        self.orderChanged.emit(list(ordered))
        self._media = list(ordered) + [path for path in self._media if path.suffix.lower() not in IMAGE_EXTENSIONS]
        self._refresh_strip()
        self._refresh_summary()
        self.stateChanged.emit()

    def _refresh_strip(self) -> None:
        images = self.image_paths()
        self.strip.set_items(images, start=self._start_image, end=self._end_image)
        start = self._start_image.name if self._start_image else "automatisch"
        end = self._end_image.name if self._end_image else "automatisch"
        self.order_status.setText(f"{len(images)} Bilder · Start: {start} · Ende: {end}")

    def _refresh_summary(self) -> None:
        images = self.image_paths()
        path = self._current_audio_path()
        analysis = self._analyses.get(path) if path else None
        duration = analysis.duration if analysis is not None else None
        marker_count = len(analysis.markers) if analysis is not None else 0
        self.summary.setText(
            slideshow_summary(
                duration,
                len(images),
                self.transition_preset,
                scene_sync=self.scene_sync_enabled,
                marker_count=marker_count,
            )
        )
