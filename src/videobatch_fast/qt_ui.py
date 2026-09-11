from __future__ import annotations

import queue
import shutil
import sys
import threading
from pathlib import Path

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QCloseEvent, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .event_buffer import EventBuffer
from .jobs import build_jobs
from .models import BatchOptions, PairJob
from .qt_theme import APP_STYLE
from .quick_modes import QUICK_MODES, apply_quick_mode
from .runner import BatchRunner

AUDIO_EXTS = {".aac", ".flac", ".m4a", ".mp3", ".ogg", ".opus", ".wav", ".wma"}
MEDIA_EXTS = {
    ".avif", ".bmp", ".gif", ".jpeg", ".jpg", ".mkv", ".mov", ".mp4",
    ".mpeg", ".mpg", ".png", ".tif", ".tiff", ".webm", ".webp",
}


class DropList(QListWidget):
    changed = Signal()

    def __init__(self, extensions: set[str]) -> None:
        super().__init__()
        self.extensions = {value.lower() for value in extensions}
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

    def paths(self) -> list[Path]:
        return [Path(self.item(row).data(Qt.ItemDataRole.UserRole)) for row in range(self.count())]

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
            item = QListWidgetItem(path.name)
            item.setData(Qt.ItemDataRole.UserRole, resolved)
            item.setToolTip(resolved)
            self.addItem(item)
            known.add(resolved)
            added = True
        if added:
            self.changed.emit()

    def remove_selected(self) -> None:
        rows = sorted((self.row(item) for item in self.selectedItems()), reverse=True)
        for row in rows:
            self.takeItem(row)
        if rows:
            self.changed.emit()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        event.acceptProposedAction() if event.mimeData().hasUrls() else event.ignore()

    def dragMoveEvent(self, event) -> None:
        event.acceptProposedAction() if event.mimeData().hasUrls() else event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        self.add_paths([Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()])
        event.acceptProposedAction()


class VideoBatchQtWindow(QMainWindow):
    """Tk-free Qt 6 frontend that reuses the verified processing core."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PROVOWARE VideoBatch 2026 · Qt 6")
        self.setMinimumSize(980, 640)
        self.resize(1360, 820)
        self.events = EventBuffer()
        self.runner = BatchRunner(self.events.put)
        self.prepare_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self.prepare_generation = 0
        self.preparing = False
        self.prepare_thread: threading.Thread | None = None
        self.close_after_stop = False
        self.jobs: list[PairJob] = []
        self._build_ui()
        self._connect()
        self._refresh()
        self.timer = QTimer(self)
        self.timer.setInterval(80)
        self.timer.timeout.connect(self._poll)
        self.timer.start()

    @staticmethod
    def _panel(title: str, hint: str) -> tuple[QFrame, QVBoxLayout]:
        box = QFrame()
        box.setObjectName("panel")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(13, 13, 13, 13)
        heading = QLabel(title)
        heading.setObjectName("section")
        note = QLabel(hint)
        note.setObjectName("subtitle")
        note.setWordWrap(True)
        layout.addWidget(heading)
        layout.addWidget(note)
        return box, layout

    @staticmethod
    def _kpi(label: str) -> tuple[QFrame, QLabel]:
        box = QFrame()
        box.setObjectName("card")
        layout = QVBoxLayout(box)
        value = QLabel("0")
        value.setObjectName("kpiValue")
        caption = QLabel(label)
        caption.setObjectName("kpiLabel")
        layout.addWidget(value)
        layout.addWidget(caption)
        return box, value

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(18, 16, 18, 16)

        header = QHBoxLayout()
        brand = QVBoxLayout()
        title = QLabel("VideoBatch 2026")
        title.setObjectName("title")
        subtitle = QLabel("Kubuntu 26.04 · KDE Plasma · Wayland · Qt 6")
        subtitle.setObjectName("subtitle")
        brand.addWidget(title)
        brand.addWidget(subtitle)
        header.addLayout(brand)
        header.addStretch()
        self.status = QLabel("BEREIT")
        self.status.setObjectName("statusChip")
        header.addWidget(self.status, alignment=Qt.AlignmentFlag.AlignTop)
        outer.addLayout(header)

        guide = QFrame()
        guide.setObjectName("workflowGuide")
        guide_row = QHBoxLayout(guide)
        guide_row.setContentsMargins(12, 8, 12, 8)
        guide_row.setSpacing(8)
        guide_title = QLabel("Einfacher Ablauf")
        guide_title.setObjectName("guideTitle")
        guide_row.addWidget(guide_title)
        self.step_files = QLabel("1 · Dateien")
        self.step_output = QLabel("2 · Ausgabe")
        self.step_start = QLabel("3 · Start")
        for step in (self.step_files, self.step_output, self.step_start):
            step.setObjectName("stepChip")
            guide_row.addWidget(step)
        guide_row.addStretch()
        outer.addWidget(guide)

        kpis = QHBoxLayout()
        kpis.setSpacing(8)
        self.kpi_values: dict[str, QLabel] = {}
        for key, label in (("audio", "Audios"), ("media", "Medien"), ("jobs", "Aufträge"), ("done", "Fertig")):
            card, value = self._kpi(label)
            self.kpi_values[key] = value
            kpis.addWidget(card, 1)
        outer.addLayout(kpis)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._sources_panel())
        splitter.addWidget(self._queue_panel())
        splitter.addWidget(self._settings_panel())
        splitter.setSizes([320, 700, 420])
        for index, stretch in enumerate((22, 48, 30)):
            splitter.setStretchFactor(index, stretch)
        outer.addWidget(splitter, 1)

        footer = QFrame()
        footer.setObjectName("actionFooter")
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(12, 9, 12, 9)
        footer_layout.setSpacing(7)
        self.next_step = QLabel("Nächster Schritt: 1 · Dateien auswählen")
        self.next_step.setObjectName("nextStep")
        self.next_step.setWordWrap(True)
        footer_layout.addWidget(self.next_step)

        row = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setFormat("Bereit · %p %")
        self.cancel = QPushButton("Abbrechen")
        self.cancel.setObjectName("danger")
        self.cancel.setEnabled(False)
        self.start = QPushButton("▶ 3 · Videos erstellen")
        self.start.setObjectName("primary")
        self.start.setMinimumWidth(220)
        row.addWidget(self.progress, 1)
        row.addWidget(self.cancel)
        row.addWidget(self.start)
        footer_layout.addLayout(row)
        outer.addWidget(footer)

    def _sources_panel(self) -> QWidget:
        panel, layout = self._panel(
            "1 · Dateien auswählen",
            "Zuerst Audio, dann passende Bilder/Videos wählen. Position 1 wird mit Position 1 kombiniert.",
        )
        self.audio = DropList(AUDIO_EXTS)
        self.media = DropList(MEDIA_EXTS)
        for label, widget, add_text in (
            ("Audiodateien", self.audio, "Audio auswählen …"),
            ("Bilder / Videos", self.media, "Bilder/Videos auswählen …"),
        ):
            layout.addWidget(QLabel(label))
            layout.addWidget(widget, 1)
            row = QHBoxLayout()
            add = QPushButton(add_text)
            remove = QPushButton("Entfernen")
            add.clicked.connect(self._choose_audio if widget is self.audio else self._choose_media)
            remove.clicked.connect(widget.remove_selected)
            row.addWidget(add)
            row.addWidget(remove)
            layout.addLayout(row)
        self.clear = QPushButton("Alle ausgewählten Dateien entfernen")
        layout.addWidget(self.clear)
        return panel

    def _queue_panel(self) -> QWidget:
        panel, layout = self._panel(
            "Kontrolle · automatische Paarung",
            "Hier nur prüfen: 1. Audio + 1. Medium = 1 Video. Du musst hier nichts einstellen.",
        )
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["#", "Audio", "Medium", "Status"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 42)
        layout.addWidget(self.table, 1)
        self.log_toggle = QToolButton()
        self.log_toggle.setText("▸ Technische Meldungen anzeigen")
        self.log_toggle.setCheckable(True)
        self.log_toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        layout.addWidget(self.log_toggle)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(1000)
        self.log.setMaximumHeight(120)
        self.log.setPlaceholderText("Technische Diagnose- und FFmpeg-Meldungen …")
        self.log.setVisible(False)
        layout.addWidget(self.log)
        self.log_toggle.toggled.connect(self._toggle_log)
        return panel

    def _settings_panel(self) -> QWidget:
        panel, layout = self._panel(
            "2 · Ausgabe festlegen",
            "Für den ersten Durchlauf reichen die empfohlenen Einstellungen.",
        )
        layout.addWidget(QLabel("Wo sollen die fertigen Videos gespeichert werden?"))
        target = QHBoxLayout()
        self.output = QLineEdit(str(Path.home() / "Videos" / "VideoBatch"))
        self.output_button = QPushButton("Ordner wählen …")
        self.output_button.setMinimumWidth(125)
        target.addWidget(self.output, 1)
        target.addWidget(self.output_button)
        layout.addLayout(target)

        layout.addWidget(QLabel("Verarbeitung"))
        self.mode = QComboBox()
        for key, spec in QUICK_MODES.items():
            if key != "custom":
                self.mode.addItem(spec.label + (" · empfohlen" if spec.recommended else ""), key)
        index = self.mode.findData("smart_auto")
        self.mode.setCurrentIndex(max(0, index))
        layout.addWidget(self.mode)
        self.mode_hint = QLabel()
        self.mode_hint.setObjectName("subtitle")
        self.mode_hint.setWordWrap(True)
        layout.addWidget(self.mode_hint)

        layout.addWidget(QLabel("Kontrolle nach der Erstellung"))
        self.verification = QComboBox()
        self.verification.addItems(["Vollständig", "Schnell"])
        layout.addWidget(self.verification)
        verification_hint = QLabel("Empfehlung: Vollständig. Schnell spart Zeit, prüft aber weniger.")
        verification_hint.setObjectName("subtitle")
        verification_hint.setWordWrap(True)
        layout.addWidget(verification_hint)

        safety = QLabel("🛡 Originaldateien bleiben unverändert.")
        safety.setObjectName("safeHint")
        safety.setWordWrap(True)
        layout.addWidget(safety)

        self.details_toggle = QToolButton()
        self.details_toggle.setText("▸ Technische Details & Sicherheit")
        self.details_toggle.setCheckable(True)
        self.details_toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        layout.addWidget(self.details_toggle)
        self.safety_details = QLabel(
            "• eindeutige Ausgabedateien\n"
            "• Fehlerprotokoll\n"
            "• kontrollierter FFmpeg-Abbruch"
        )
        self.safety_details.setObjectName("subtitle")
        self.safety_details.setWordWrap(True)
        self.safety_details.setVisible(False)
        layout.addWidget(self.safety_details)
        self.details_toggle.toggled.connect(self._toggle_details)

        layout.addStretch()
        self.runtime = QLabel()
        self.runtime.setObjectName("subtitle")
        layout.addWidget(self.runtime)
        self._mode_changed()
        self._runtime_state()
        return panel

    def _connect(self) -> None:
        self.audio.changed.connect(self._refresh)
        self.media.changed.connect(self._refresh)
        self.clear.clicked.connect(self._clear_lists)
        self.output_button.clicked.connect(self._choose_output)
        self.output.textChanged.connect(self._refresh)
        self.mode.currentIndexChanged.connect(self._mode_changed)
        self.start.clicked.connect(self._start)
        self.cancel.clicked.connect(self._cancel)

    def _toggle_log(self, visible: bool) -> None:
        self.log.setVisible(visible)
        self.log_toggle.setText(
            "▾ Technische Meldungen ausblenden" if visible else "▸ Technische Meldungen anzeigen"
        )

    def _toggle_details(self, visible: bool) -> None:
        self.safety_details.setVisible(visible)
        self.details_toggle.setText(
            "▾ Technische Details & Sicherheit" if visible else "▸ Technische Details & Sicherheit"
        )

    def _choose_audio(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self, "Audiodateien", str(Path.home()),
            "Audio (*.mp3 *.wav *.flac *.m4a *.aac *.ogg *.opus *.wma);;Alle Dateien (*)",
        )
        self.audio.add_paths([Path(value) for value in files])

    def _choose_media(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self, "Bilder oder Videos", str(Path.home()),
            "Medien (*.png *.jpg *.jpeg *.webp *.avif *.mp4 *.mkv *.mov *.webm *.mpeg *.mpg);;Alle Dateien (*)",
        )
        self.media.add_paths([Path(value) for value in files])

    def _choose_output(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Ausgabeordner", self.output.text() or str(Path.home()))
        if selected:
            self.output.setText(selected)

    def _clear_lists(self) -> None:
        if self.runner.running or self.preparing:
            return
        self.audio.clear()
        self.media.clear()
        self.audio.changed.emit()
        self.kpi_values["done"].setText("0")
        self.progress.setValue(0)

    def _refresh(self) -> None:
        audios, media = self.audio.paths(), self.media.paths()
        self.kpi_values["audio"].setText(str(len(audios)))
        self.kpi_values["media"].setText(str(len(media)))
        self.table.setRowCount(max(len(audios), len(media)))
        for row in range(self.table.rowCount()):
            complete = row < len(audios) and row < len(media)
            values = (
                str(row + 1),
                audios[row].name if row < len(audios) else "— fehlt —",
                media[row].name if row < len(media) else "— fehlt —",
                "Bereit" if complete else "Unvollständig",
            )
            for col, text in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(text))
        jobs = len(audios) if audios and len(audios) == len(media) else 0
        output_ready = bool(self.output.text().strip())
        files_ready = bool(jobs)
        self.kpi_values["jobs"].setText(str(jobs))
        ready = files_ready and output_ready and not self.runner.running and not self.preparing
        self.start.setEnabled(ready)

        self.step_files.setText("1 · Dateien ✓" if files_ready else "1 · Dateien")
        self.step_output.setText("2 · Ausgabe ✓" if output_ready else "2 · Ausgabe")
        self.step_start.setText("3 · Start bereit" if ready else "3 · Start")

        if self.runner.running:
            self.next_step.setText("Produktion läuft. Fortschritt und Abbrechen bleiben hier immer sichtbar.")
        elif self.preparing:
            self.next_step.setText("Dateien werden geprüft. Danach startet die Verarbeitung automatisch.")
        elif not audios and not media:
            self.next_step.setText("Nächster Schritt: 1 · Audiodateien und passende Bilder/Videos auswählen.")
        elif not audios:
            self.next_step.setText("Nächster Schritt: 1 · Mindestens eine Audiodatei hinzufügen.")
        elif len(audios) != len(media):
            self.next_step.setText(
                f"Nächster Schritt: 1 · Paarung vervollständigen — {len(audios)} Audio, {len(media)} Medien."
            )
        elif not output_ready:
            self.next_step.setText("Nächster Schritt: 2 · Einen Ausgabeordner wählen.")
        else:
            self.next_step.setText(f"Bereit: {jobs} Video(s). Nächster Schritt: 3 · Videos erstellen.")

        if not self.runner.running and not self.preparing:
            self._status("BEREIT" if ready or not self.table.rowCount() else "PRÜFEN")

    def _mode_changed(self) -> None:
        spec = QUICK_MODES.get(str(self.mode.currentData()), QUICK_MODES["smart_auto"])
        self.mode_hint.setText(f"{spec.description}\nGeschwindigkeit: {spec.speed_class}")

    def _runtime_state(self) -> None:
        missing = [name for name in ("ffmpeg", "ffprobe") if shutil.which(name) is None]
        self.runtime.setText("🔴 Fehlt: " + ", ".join(missing) if missing else "🟢 FFmpeg + FFprobe gefunden")

    def _options(self) -> BatchOptions:
        if not self.output.text().strip():
            raise ValueError("Bitte einen Ausgabeordner wählen.")
        base = BatchOptions(
            output_dir=Path(self.output.text().strip()).expanduser(),
            verification=self.verification.currentText(),
            quick_mode=str(self.mode.currentData() or "smart_auto"),
            assignment_mode="pairwise",
        )
        selected = apply_quick_mode(base, base.quick_mode)
        return BatchOptions(
            output_dir=selected.output_dir, output_mode=selected.output_mode, resolution=selected.resolution,
            codec=selected.codec, profile=selected.profile, verification=self.verification.currentText(),
            overwrite=selected.overwrite, keep_lists=selected.keep_lists, audio_bitrate=selected.audio_bitrate,
            fps=selected.fps, max_threads=selected.max_threads, visual_effect=selected.visual_effect,
            transition=selected.transition, quick_mode=selected.quick_mode, assignment_mode="pairwise",
            slideshow_transition=selected.slideshow_transition, slideshow_scene_sync=selected.slideshow_scene_sync,
        )

    def _start(self) -> None:
        if self.runner.running or self.preparing:
            return
        missing = [name for name in ("ffmpeg", "ffprobe") if shutil.which(name) is None]
        if missing:
            QMessageBox.critical(self, "FFmpeg fehlt", "Nicht gefunden: " + ", ".join(missing))
            return
        audios, media = self.audio.paths(), self.media.paths()
        if not audios or len(audios) != len(media):
            QMessageBox.warning(self, "Paarung unvollständig", "Zu jedem Audio muss genau ein Bild oder Video gehören.")
            return
        try:
            options = self._options()
        except ValueError as exc:
            QMessageBox.warning(self, "Einstellung fehlt", str(exc))
            return

        self.preparing = True
        self.prepare_generation += 1
        generation = self.prepare_generation
        self.start.setEnabled(False)
        self.cancel.setEnabled(True)
        self.progress.setRange(0, 0)
        self.progress.setFormat("Quellen werden geprüft …")
        self._status("PRÜFT")
        self.step_start.setText("3 · Start …")
        self.next_step.setText("Dateien werden geprüft. Danach startet die Verarbeitung automatisch.")
        self._write_log(f"Prüfe {len(audios)} Auftrag/Aufträge mit FFprobe.")

        def prepare() -> None:
            try:
                jobs = build_jobs(audios, media, options)
                self.prepare_queue.put(("ok", (generation, jobs, options)))
            except Exception as exc:
                self.prepare_queue.put(("error", (generation, f"{type(exc).__name__}: {exc}")))

        self.prepare_thread = threading.Thread(target=prepare, daemon=True, name="VideoBatch-Qt-Prepare")
        self.prepare_thread.start()

    def _cancel(self) -> None:
        if self.preparing and not self.runner.running:
            self.prepare_generation += 1
            self.preparing = False
            self.progress.setRange(0, 100)
            self.progress.setValue(0)
            self.cancel.setEnabled(False)
            self._status("ABGEBROCHEN")
            self._write_log("Vorbereitung verworfen; kein Stapel wird gestartet.")
            self._refresh()
        elif self.runner.running:
            self.runner.cancel()
            self.cancel.setEnabled(False)
            self._status("STOPPT")
            self._write_log("Kontrollierter Abbruch angefordert.")

    def _poll(self) -> None:
        try:
            kind, payload = self.prepare_queue.get_nowait()
        except queue.Empty:
            pass
        else:
            generation, data, *rest = payload  # type: ignore[misc]
            if generation == self.prepare_generation and self.preparing:
                self.preparing = False
                self.progress.setRange(0, 100)
                if kind == "error":
                    self._status("FEHLER")
                    self._write_log(str(data))
                    self.cancel.setEnabled(False)
                    self._refresh()
                else:
                    self.jobs = list(data)
                    options = rest[0]
                    self._load_jobs()
                    try:
                        self.runner.start(self.jobs, options)
                    except Exception as exc:
                        self._status("FEHLER")
                        self._write_log(f"{type(exc).__name__}: {exc}")
                        self.cancel.setEnabled(False)
                        self._refresh()
        self._drain_events()
        prepare_alive = bool(self.prepare_thread and self.prepare_thread.is_alive())
        if self.close_after_stop and not self.runner.running and not prepare_alive:
            self.close_after_stop = False
            self.close()

    def _drain_events(self) -> None:
        for _ in range(200):
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                return
            p, name = event.payload, event.name
            if name == "batch_started":
                self.progress.setValue(0)
                self.progress.setFormat("Verarbeitung · %p %")
                self.kpi_values["done"].setText("0")
                self._status("LÄUFT")
                self.step_start.setText("3 · Läuft …")
                self.next_step.setText("Produktion läuft. Fortschritt und Abbrechen bleiben hier immer sichtbar.")
            elif name == "job_started":
                self._row_status(int(p.get("position", 1)) - 1, "Läuft …")
            elif name == "progress":
                snap = p.get("snapshot")
                value = float(getattr(snap, "total_percent", 0.0) or 0.0)
                value = value * 100.0 if 0 <= value <= 1 else value
                self.progress.setValue(max(0, min(100, round(value))))
                self.progress.setFormat(f"{getattr(snap, 'phase', 'Verarbeitung')} · %p %")
            elif name == "job_finished":
                result, pos = p.get("result"), int(p.get("position", 1))
                self._row_status(pos - 1, "Fertig ✓" if getattr(result, "success", False) else "Fehler")
                self.kpi_values["done"].setText(str(pos))
                if getattr(result, "message", ""):
                    self._write_log(f"Auftrag {pos}: {result.message}")
            elif name in {"job_failed_internal", "batch_failed_internal"}:
                self._status("SCHUTZSTOPP" if name == "batch_failed_internal" else "FEHLER")
                self._write_log(str(p.get("message", "")))
            elif name == "log":
                self._write_log(str(p.get("message", "")))
            elif name == "batch_finished":
                ok, failed, open_ = int(p.get("successes", 0)), int(p.get("failures", 0)), int(p.get("unprocessed", 0))
                self._status("ABGEBROCHEN" if p.get("cancelled") else ("FERTIG" if not failed and not open_ else "FERTIG MIT HINWEIS"))
                if not failed and not open_ and not p.get("cancelled"):
                    self.progress.setValue(100)
                self.progress.setFormat("Abgeschlossen · %p %")
                self.cancel.setEnabled(False)
                self._write_log(f"Abschluss: {ok} erfolgreich · {failed} Fehler · {open_} offen.")
                self._refresh()

    def _load_jobs(self) -> None:
        self.table.setRowCount(len(self.jobs))
        for row, job in enumerate(self.jobs):
            for col, text in enumerate((str(job.index), job.audio.name, job.media.name, "Geprüft")):
                self.table.setItem(row, col, QTableWidgetItem(text))
            self.table.item(row, 2).setToolTip(f"Ausgabe: {job.output}")

    def _row_status(self, row: int, text: str) -> None:
        if 0 <= row < self.table.rowCount():
            if self.table.item(row, 3) is None:
                self.table.setItem(row, 3, QTableWidgetItem())
            self.table.item(row, 3).setText(text)

    def _write_log(self, message: str) -> None:
        if message.strip():
            self.log.appendPlainText(message.strip())

    def _status(self, text: str) -> None:
        self.status.setText(text)

    def closeEvent(self, event: QCloseEvent) -> None:
        prepare_alive = bool(self.prepare_thread and self.prepare_thread.is_alive())
        if self.runner.running or prepare_alive:
            if self.close_after_stop:
                event.ignore()
                return
            answer = QMessageBox.question(
                self, "Vorgang läuft", "Kontrolliert beenden und danach VideoBatch schließen?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.close_after_stop = True
            if self.preparing:
                self.prepare_generation += 1
                self.preparing = False
            if self.runner.running:
                self.runner.cancel()
            self._status("STOPPT")
            self._write_log("Sicheres Beenden angefordert; laufender Vorgang wird zuerst abgeschlossen.")
            event.ignore()
            return
        event.accept()


def run_qt_ui() -> int:
    app = QApplication.instance()
    owns_app = app is None
    if app is None:
        app = QApplication(sys.argv)
    app.setApplicationName("PROVOWARE VideoBatch 2026")
    app.setOrganizationName("provoware")
    app.setStyleSheet(APP_STYLE)
    window = VideoBatchQtWindow()
    window.show()
    return app.exec() if owns_app else 0


if __name__ == "__main__":
    raise SystemExit(run_qt_ui())
