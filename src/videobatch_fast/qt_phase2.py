from __future__ import annotations

import shutil
import sys
import threading
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QGridLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .jobs import build_jobs
from .qt_media_import_dialog import MediaImportDialog
from .qt_phase2_components import PreviewPanel, SlideshowPanel
from .qt_theme import APP_STYLE
from .qt_ui import VideoBatchQtWindow
from .qt_workflow_dialogs import (
    PluginPermissionDecisionDialog,
    VisualApprovalSignDialog,
    archive_preview_dialog,
    plugin_permission_dialog,
    recovery_dialog,
    update_assistant_dialog,
)
from .slideshow import SLIDESHOW_MODE_ALL_IMAGES


class VideoBatchQtPhase2Window(VideoBatchQtWindow):
    """Phase-2 Qt frontend: preview, slideshow, waveform and special dialogs."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PROVOWARE VideoBatch 2026 · Qt 6 · Phase 2")
        self._build_phase2_dock()
        self._connect_phase2()
        self._refresh()
        self._write_log("Qt Phase 2 aktiv: Vorschau · Diashow · Waveform · Spezialdialoge.")

    def _build_phase2_dock(self) -> None:
        self.phase2_dock = QDockWidget("Werkzeuge · Phase 2", self)
        self.phase2_dock.setObjectName("phase2Dock")
        self.phase2_dock.setAllowedAreas(
            Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.BottomDockWidgetArea
        )

        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        self.phase2_tabs = tabs

        self.preview_panel = PreviewPanel()
        tabs.addTab(self.preview_panel, "Vorschau")

        self.slideshow = SlideshowPanel()
        tabs.addTab(self.slideshow, "Diashow & Waveform")

        tabs.addTab(self._dialogs_panel(), "Spezialdialoge")

        self.phase2_dock.setWidget(tabs)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.phase2_dock)
        self.resizeDocks([self.phase2_dock], [470], Qt.Orientation.Horizontal)

    def _dialogs_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        intro = QLabel(
            "Native Qt-Dialoge. Die bisherigen Tk-Dialoge bleiben nur im Legacy-Pfad "
            "und werden vom Phase-2-Start nicht benötigt."
        )
        intro.setObjectName("subtitle")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        grid = QGridLayout()
        buttons = (
            ("Audio-Browser", self._browse_audio),
            ("Medien-Browser", self._browse_media),
            ("Plugin-Freigabe", self._show_plugin_dialog),
            ("Plugin-Entscheidung", self._show_plugin_decision),
            ("Update-Assistent", self._show_update_dialog),
            ("Recovery", self._show_recovery_dialog),
            ("Ablageprüfung", self._show_archive_dialog),
            ("Visuelle Freigabe", self._show_visual_approval),
        )
        for index, (label, callback) in enumerate(buttons):
            button = QPushButton(label)
            button.clicked.connect(callback)
            grid.addWidget(button, index // 2, index % 2)
        layout.addLayout(grid)

        note = QLabel(
            "Hinweis: Die Dialoge führen nur die Entscheidung. "
            "Dateiänderungen, Updates, Recovery oder Signaturen werden weiterhin "
            "durch die bestehenden geprüften Core-Services ausgeführt."
        )
        note.setObjectName("subtitle")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch()
        return panel

    def _connect_phase2(self) -> None:
        self.audio.currentItemChanged.connect(lambda *_args: self._preview_audio_selection())
        self.media.currentItemChanged.connect(lambda *_args: self._preview_media_selection())
        self.slideshow.orderChanged.connect(self._apply_slideshow_media_order)
        self.slideshow.stateChanged.connect(self._refresh)
        self.slideshow.analysisChanged.connect(self._refresh)

    def _preview_audio_selection(self) -> None:
        item = self.audio.currentItem()
        if item is None:
            if self.media.currentItem() is None:
                self.preview_panel.set_source(None, include_image=False)
            return
        raw = item.data(Qt.ItemDataRole.UserRole)
        if raw:
            self.preview_panel.set_source(Path(str(raw)), include_image=False)
            self.phase2_tabs.setCurrentWidget(self.preview_panel)

    def _preview_media_selection(self) -> None:
        item = self.media.currentItem()
        if item is None:
            return
        raw = item.data(Qt.ItemDataRole.UserRole)
        if raw:
            self.preview_panel.set_source(Path(str(raw)), include_image=True)
            self.phase2_tabs.setCurrentWidget(self.preview_panel)

    def _apply_slideshow_media_order(self, ordered_object: object) -> None:
        if self.runner.running or self.preparing:
            return
        ordered = [Path(value) for value in list(ordered_object)]
        videos = [path for path in self.media.paths() if path not in ordered]
        combined = ordered + videos
        self.media.blockSignals(True)
        self.media.clear()
        self.media.add_paths(combined)
        self.media.blockSignals(False)
        self.media.changed.emit()

    def _options(self):
        options = super()._options()
        if not hasattr(self, "slideshow"):
            return options
        return replace(
            options,
            assignment_mode=self.slideshow.assignment_mode,
            slideshow_transition=self.slideshow.transition_preset,
            slideshow_scene_sync=self.slideshow.scene_sync_enabled,
        )

    def _refresh(self) -> None:
        super()._refresh()
        if not hasattr(self, "slideshow"):
            return

        audios = self.audio.paths()
        media = self.media.paths()
        self.slideshow.set_sources(audios, media)

        if self.slideshow.assignment_mode != SLIDESHOW_MODE_ALL_IMAGES:
            return

        images = self.slideshow.image_paths()
        self.table.setRowCount(len(audios))
        for row, audio in enumerate(audios):
            values = (
                str(row + 1),
                audio.name,
                f"Diashow · {len(images)} Bilder",
                "Bereit" if images else "Bilder fehlen",
            )
            for column, text in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(text))

        jobs = len(audios) if audios and images else 0
        self.kpi_values["jobs"].setText(str(jobs))
        pending = self.slideshow.pending_analysis and self.slideshow.scene_sync_enabled
        self.start.setEnabled(bool(jobs) and not self.runner.running and not self.preparing and not pending)

        if pending and not self.runner.running and not self.preparing:
            self._status("ANALYSE")
        elif not self.runner.running and not self.preparing:
            self._status("BEREIT" if jobs else "PRÜFEN")

    def _start(self) -> None:
        if not hasattr(self, "slideshow") or self.slideshow.assignment_mode != SLIDESHOW_MODE_ALL_IMAGES:
            super()._start()
            return
        if self.runner.running or self.preparing:
            return

        missing = [name for name in ("ffmpeg", "ffprobe") if shutil.which(name) is None]
        if missing:
            QMessageBox.critical(self, "FFmpeg fehlt", "Nicht gefunden: " + ", ".join(missing))
            return

        audios = self.audio.paths()
        media = self.media.paths()
        images = self.slideshow.image_paths()
        if not audios:
            QMessageBox.warning(self, "Audio fehlt", "Für eine Diashow wird mindestens eine Audiodatei benötigt.")
            return
        if not images:
            QMessageBox.warning(self, "Bilder fehlen", "Für eine Diashow wird mindestens ein Bild benötigt.")
            return

        if self.slideshow.scene_sync_enabled:
            self.slideshow.ensure_scene_analyses()
            if self.slideshow.pending_analysis or self.slideshow.missing_scene_analyses():
                QMessageBox.information(
                    self,
                    "Szenenanalyse läuft",
                    "Die Audios werden zuerst analysiert. Der Start wird freigegeben, sobald die Analyse abgeschlossen ist.",
                )
                self._refresh()
                return

        try:
            options = self._options()
        except ValueError as exc:
            QMessageBox.warning(self, "Einstellung fehlt", str(exc))
            return

        analyses = self.slideshow.scene_analyses()
        self.preparing = True
        self.prepare_generation += 1
        generation = self.prepare_generation
        self.start.setEnabled(False)
        self.cancel.setEnabled(True)
        self.progress.setRange(0, 0)
        self.progress.setFormat("Diashow wird vorbereitet …")
        self._status("PRÜFT")
        self._write_log(
            f"Prüfe {len(audios)} Diashow-Auftrag/Aufträge · "
            f"{len(images)} Bilder · Szenensync: {'ja' if options.slideshow_scene_sync else 'nein'}."
        )

        def prepare() -> None:
            try:
                jobs = build_jobs(
                    audios,
                    media,
                    options,
                    scene_analyses=analyses,
                )
                if not jobs:
                    raise RuntimeError("Es konnten keine Diashow-Aufträge erzeugt werden.")
                self.prepare_queue.put(("ok", (generation, jobs, options)))
            except Exception as exc:
                self.prepare_queue.put(("error", (generation, f"{type(exc).__name__}: {exc}")))

        self.prepare_thread = threading.Thread(
            target=prepare,
            daemon=True,
            name="VideoBatch-Qt-Diashow-Prepare",
        )
        self.prepare_thread.start()

    def _browse_audio(self) -> None:
        dialog = MediaImportDialog(
            self,
            audio=True,
            initial_dir=Path.home() / "Music",
            modal=True,
        )
        paths = dialog.wait()
        if paths:
            self.audio.add_paths(list(paths))

    def _browse_media(self) -> None:
        dialog = MediaImportDialog(
            self,
            audio=False,
            initial_dir=Path.home() / "Pictures",
            modal=True,
        )
        paths = dialog.wait()
        if paths:
            self.media.add_paths(list(paths))

    def _show_plugin_dialog(self) -> None:
        dialog = plugin_permission_dialog(
            self,
            "Beispielansicht der Qt-Migration. Reale Berechtigungen werden vom Plugin-Service geliefert.",
            "missing",
        )
        approved = dialog.wait()
        self._write_log(f"Qt Plugin-Freigabedialog: {'freigegeben' if approved else 'abgebrochen'}.")

    def _show_plugin_decision(self) -> None:
        dialog = PluginPermissionDecisionDialog(
            self,
            "Berechtigungsübersicht der Qt-Migration.",
            "active",
        )
        self._write_log(f"Qt Plugin-Entscheidung: {dialog.wait()}.")

    def _show_update_dialog(self) -> None:
        dialog = update_assistant_dialog(self, "Qt-Phase-2", 0)
        self._write_log(f"Qt Update-Dialog: {'bestätigt' if dialog.wait() else 'abgebrochen'}.")

    def _show_recovery_dialog(self) -> None:
        dialog = recovery_dialog(self, "QT-PHASE2-DEMO")
        self._write_log(f"Qt Recovery-Dialog: {'bestätigt' if dialog.wait() else 'abgebrochen'}.")

    def _show_archive_dialog(self) -> None:
        dialog = archive_preview_dialog(
            self,
            len(self.audio.paths()) + len(self.media.paths()),
            self.output.text().strip(),
            "_verwendet",
        )
        self._write_log(f"Qt Ablageprüfung: {'bestätigt' if dialog.wait() else 'abgebrochen'}.")

    def _show_visual_approval(self) -> None:
        dialog = VisualApprovalSignDialog(self, "qt-phase2", default_reviewer="")
        reviewer = dialog.wait()
        self._write_log(
            f"Qt visuelle Freigabe: {reviewer}" if reviewer else "Qt visuelle Freigabe abgebrochen."
        )

    def closeEvent(self, event) -> None:
        super().closeEvent(event)
        if event.isAccepted() and hasattr(self, "preview_panel"):
            self.preview_panel.shutdown()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("PROVOWARE VideoBatch 2026 Qt Phase 2")
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLE)
    window = VideoBatchQtPhase2Window()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
