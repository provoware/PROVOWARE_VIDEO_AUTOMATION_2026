from __future__ import annotations

import queue
import sqlite3
import shutil
import sys
import threading
import time
from pathlib import Path

from PySide6.QtCore import QTimer, Qt, Signal, QUrl
from PySide6.QtGui import QCloseEvent, QColor, QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QFrame, QHBoxLayout,
    QLabel, QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QToolButton, QVBoxLayout, QWidget,
)

from .event_buffer import EventBuffer
from .error_handling import explain_runtime_problem
from .display_formatting import format_clock, format_eta, format_size
from .jobs import build_jobs
from .models import BatchOptions, PairJob
from .pairing_status import pairing_status
from .probe_render import plan_probe, probe_output, prune_probes
from .media_index import MediaIndex, media_roots
from .media_index_preferences import load_exclusions, save_exclusions
from .qt_main_layout import build_main_ui
from .qt_theme import APP_STYLE
from .dashboard_settings import DashboardSettings, load_settings, save_settings
from .runner import BatchRunner
from .validation import validate_pairs
from .resource_estimation import estimate_job_output_bytes
from .qt_source_panel import build_sources_panel
from .qt_system_load_dashboard import SystemLoadDashboard
from .qt_ui_polish import (
    configure_job_table, configure_output_button, field_label, install_workflow_shortcuts,
    job_table_item, text_label, update_status_chip,
)

from . import qt_desktop_actions

from . import qt_production_events

class VideoBatchQtWindow(QMainWindow):
    """Tk-free Qt 6 frontend that reuses the verified processing core."""

    mediaIndexMessage = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PROVOWARE VideoBatch 2026 · Qt 6")
        self.setMinimumSize(800, 600)
        self.resize(1360, 820)
        self.events = EventBuffer()
        self.runner = BatchRunner(self.events.put)
        self.prepare_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self.prepare_generation = 0
        self.preparing = False
        self.prepare_thread: threading.Thread | None = None
        self.close_after_stop = False
        self.jobs: list[PairJob] = []
        self._probe_pending = False
        self._probe_active = False
        self._probe_file: Path | None = None
        self._settings_warning = ""
        try:
            self.dashboard_settings = load_settings()
        except (OSError, ValueError, TypeError) as exc:
            self.dashboard_settings = DashboardSettings()
            self._settings_warning = f"Gespeicherte Videoeinstellungen konnten nicht gelesen werden: {exc}. Standardwerte aktiv."
        self._settings_dirty = False
        self.load_dashboard = SystemLoadDashboard(self)
        self._build_ui()
        self.mediaIndexMessage.connect(self._media_index_notice)
        self._connect()
        self._refresh()
        if self._settings_warning:
            self._write_log(self._settings_warning)
            self.next_step.setText("Einstellungen nicht lesbar – Standardwerte aktiv. Technische Meldungen beachten.")
        self.timer = QTimer(self)
        self.timer.setInterval(80)
        self.timer.timeout.connect(self._poll)
        self.timer.start()
        # A previous index can be read immediately in the file dialog.
        # Refresh only in a worker, after the first frame has been displayed.
        self._media_index_stop = threading.Event()
        self._media_index_reconfigure = threading.Event()
        try:
            self._index_exclusions = frozenset(load_exclusions())
        except ValueError as exc:
            self._index_exclusions = frozenset()
            self._write_log(f"Ordnerausschlüsse konnten nicht gelesen werden: {exc}")
        self._media_index = MediaIndex(excluded_paths=self._index_exclusions)
        self._media_index_worker: threading.Thread | None = None
        self._media_rescan_pending = False
        QTimer.singleShot(300, self._refresh_media_index_async)

    def _media_index_notice(self, message: str) -> None:
        self._write_log("Mediensuche: " + message)
        status = getattr(self, "media_exclusion_status", None)
        if status is not None:
            status.setText(message)

    def _refresh_media_index_async(self) -> None:
        return qt_desktop_actions._refresh_media_index_async(self)

    @staticmethod
    def _panel(title: str, hint: str) -> tuple[QFrame, QVBoxLayout]:
        box = QFrame()
        box.setObjectName("panel")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(13, 13, 13, 13)
        heading = QLabel(title)
        heading.setObjectName("section")
        note = text_label(hint, "panelHint", wrap=True)
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
        build_main_ui(self)

    def _sources_panel(self) -> QWidget:
        return build_sources_panel(self)

    def _queue_panel(self) -> QWidget:
        panel, layout = self._panel(
            "Kontrolle · automatische Paarung",
            "Hier nur prüfen: 1. Audio + 1. Medium = 1 Video. Du musst hier nichts einstellen.",
        )
        self.pairing_summary_label = QLabel("Bitte zuerst Audio und Bilder/Videos auswählen.")
        self.pairing_summary_label.setObjectName("pairingReadiness")
        self.pairing_summary_label.setWordWrap(True)
        self.pairing_summary_label.setAccessibleName("Bereitschaft und Dateipaarung")
        layout.addWidget(self.pairing_summary_label)
        self.table = QTableWidget(0, 5)
        configure_job_table(self.table)
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
        return qt_desktop_actions._settings_panel(self)

    def _connect(self) -> None:
        self.audio.changed.connect(self._refresh)
        self.media.changed.connect(self._refresh)
        self.clear.clicked.connect(self._clear_lists)
        self.output_button.clicked.connect(self._choose_output)
        self.output.textChanged.connect(self._refresh)
        self.settings_save_timer = QTimer(self)
        self.settings_save_timer.setSingleShot(True)
        self.settings_save_timer.setInterval(400)
        self.settings_save_timer.timeout.connect(self._save_dashboard_settings)
        for field in ("resolution", "quality", "effect", "transition"):
            getattr(self, field).currentIndexChanged.connect(
                lambda _index, name=field: self._dashboard_changed(name)
            )
        self.effect_intensity.valueChanged.connect(self._intensity_changed)
        self.fade_seconds.valueChanged.connect(
            lambda _value: self._dashboard_changed("transition_duration")
        )
        self.fade_seconds.setEnabled(self.transition.currentData() != "none")
        self.output.editingFinished.connect(lambda: self._dashboard_changed("output_dir"))
        self.start.clicked.connect(self._start)
        self.probe_button.clicked.connect(self._request_probe)
        self.open_probe_button.clicked.connect(self._open_probe)
        self.cancel.clicked.connect(self._cancel)
        install_workflow_shortcuts(self)

    def _browse_media_exclusion(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            self, "Programmierordner auslassen", str(media_roots()["downloads"])
        )
        if not selected:
            return
        existing = [line.strip() for line in self.media_exclusions.toPlainText().splitlines()
                    if line.strip()]
        if selected not in existing:
            existing.append(selected)
        self.media_exclusions.setPlainText("\n".join(existing))

    def _save_media_exclusions(self) -> None:
        paths = self.media_exclusions.toPlainText().splitlines()
        try:
            saved = save_exclusions(paths, media_roots())
        except (ValueError, OSError) as exc:
            self.media_exclusion_status.setText(f"Nicht gespeichert: {exc}")
            return
        self._index_exclusions = frozenset(saved)
        self._media_index_reconfigure.set()
        self._media_index = MediaIndex(excluded_paths=self._index_exclusions)
        self._media_rescan_pending = True
        self.media_exclusion_status.setText(
            f"{len(saved)} Ordner ausgeschlossen. Medienliste wird aktualisiert."
        )
        QTimer.singleShot(300, self._refresh_media_index_async)

    def _intensity_changed(self, value: int) -> None:
        self.intensity_value.setText(f"{value} %")
        self._dashboard_changed("effect_intensity")

    def _dashboard_changed(self, field: str) -> None:
        if getattr(self, "_loading_project", False):
            # Project restoration is not a new user preference.
            return
        if field == "output_dir":
            value = self.output.text()
        elif field == "effect_intensity":
            value = self.effect_intensity.value()
        elif field == "transition_duration":
            value = self.fade_seconds.value()
        else:
            value = getattr(self, field).currentData()
        if field == "transition":
            self.fade_seconds.setEnabled(value != "none")
        try:
            self.dashboard_settings = self.dashboard_settings.set_user_value(field, value)
        except ValueError:
            # A blank, partially edited path must not overwrite the last valid value.
            return
        self._settings_dirty = True
        self.settings_save_timer.start()

    def _save_dashboard_settings(self) -> None:
        if not self._settings_dirty:
            return
        try:
            save_settings(self.dashboard_settings)
        except OSError as exc:
            self._write_log(f"Videoeinstellungen konnten nicht gespeichert werden: {exc}")
            self.next_step.setText("Videoeinstellungen konnten nicht gespeichert werden. Bitte Speicherort prüfen.")
        else:
            self._settings_dirty = False

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
        from .qt_media_import_dialog import MediaImportDialog
        dialog = MediaImportDialog(self, audio=True, initial_dir=Path.home() / "Music")
        selected = dialog.wait()
        if selected:
            self.audio.add_paths(list(selected))

    def _choose_media(self) -> None:
        from .qt_media_import_dialog import MediaImportDialog
        dialog = MediaImportDialog(self, audio=False, initial_dir=Path.home() / "Pictures")
        selected = dialog.wait()
        if selected:
            self.media.add_paths(list(selected))

    def _choose_output(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Ausgabeordner", self.output.text() or str(Path.home()))
        if selected:
            self.output.setText(selected)
            self._dashboard_changed("output_dir")

    def _clear_lists(self) -> None:
        if self.runner.running or self.preparing:
            return
        self.audio.clear()
        self.media.clear()
        self.audio.changed.emit()
        self.kpi_values["done"].setText("0")
        self.progress.setValue(0)
        self.job_progress.setValue(0)
        self.job_progress.setFormat("Kein Auftrag aktiv · %p %")
        self.activity_detail.setText("Keine Verarbeitung aktiv · bereit für neue Aufträge")

    def _refresh(self, *, preserve_results: bool = False) -> None:
        audios, media = self.audio.production_paths(), self.media.production_paths()
        pairing = pairing_status(len(audios), len(media), self.output.text())
        self.pairing_summary_label.setText(
            ("✓ " if pairing.ready else "⚠ ") + pairing.explanation
        )
        self.pairing_summary_label.setToolTip(
            "Dies ist die Zuordnungsvorschau; tatsächliche Formate werden "
            "erst bei der Startprüfung kontrolliert."
        )
        self.kpi_values["audio"].setText(str(len(audios)))
        self.kpi_values["media"].setText(str(len(media)))
        if not preserve_results:
            self.table.setRowCount(max(len(audios), len(media)))
            for row in range(self.table.rowCount()):
                complete = row < len(audios) and row < len(media)
                values = (
                    str(row + 1),
                    audios[row].name if row < len(audios) else "— fehlt —",
                    media[row].name if row < len(media) else "— fehlt —",
                    "Bereit" if complete else "Unvollständig",
                    "0 %" if complete else "–",
                )
                for col, text in enumerate(values):
                    self.table.setItem(row, col, job_table_item(text, col))
        jobs = len(audios) if audios and len(audios) == len(media) else 0
        output_dir = Path(self.output.text().strip()).expanduser()
        output_ready = bool(self.output.text().strip())
        self.open_output.setEnabled(output_dir.is_dir())
        files_ready = bool(jobs)
        self.kpi_values["jobs"].setText(str(jobs))
        ready = files_ready and output_ready and not self.runner.running and not self.preparing
        self.probe_button.setEnabled(ready)
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
            self.next_step.setText("Nächster Schritt: " + pairing.explanation)
        elif not output_ready:
            self.next_step.setText("Nächster Schritt: einen Ausgabeordner oben wählen.")
        else:
            self.next_step.setText(f"Bereit: {jobs} Video(s). Nächster Schritt: 3 · Videos erstellen.")

        if not self.runner.running and not self.preparing:
            self._status("BEREIT" if ready or not self.table.rowCount() else "PRÜFEN")

    def _runtime_state(self) -> None:
        missing = [name for name in ("ffmpeg", "ffprobe") if shutil.which(name) is None]
        self.runtime.setText("🔴 Fehlt: " + ", ".join(missing) if missing else "🟢 FFmpeg + FFprobe gefunden")

    def _options(self) -> BatchOptions:
        """Freeze the *displayed* values into the actual job options."""
        from .command_builder import PROFILES, RESOLUTIONS
        state = self.dashboard_settings
        for field in ("resolution", "quality", "effect", "transition", "output_dir",
                      "effect_intensity", "transition_duration"):
            if field == "output_dir":
                value = self.output.text()
            elif field == "effect_intensity":
                value = self.effect_intensity.value()
            elif field == "transition_duration":
                value = self.fade_seconds.value()
            else:
                value = getattr(self, field).currentData()
            state = state.set_user_value(field, value)
        if state.resolution not in RESOLUTIONS or state.quality not in PROFILES:
            raise ValueError("Videoauflösung oder Qualität wird nicht unterstützt.")
        self.dashboard_settings = state
        self._settings_dirty = True
        self._save_dashboard_settings()
        return BatchOptions(
            output_dir=state.output_dir,
            resolution=state.resolution,
            profile=state.quality,
            visual_effect=state.effect,
            effect_intensity=state.effect_intensity,
            transition=state.transition,
            transition_duration=state.transition_duration,
            verification=self.verification.currentText(),
            quick_mode="custom",
            assignment_mode="pairwise",
        )

    def _start(self) -> None:
        if self.runner.running or self.preparing:
            return
        missing = [name for name in ("ffmpeg", "ffprobe") if shutil.which(name) is None]
        if missing:
            QMessageBox.critical(self, "FFmpeg fehlt", "Nicht gefunden: " + ", ".join(missing))
            return
        audios, media = self.audio.production_paths(), self.media.production_paths()
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
        self.open_output.setEnabled(False)
        self.show_result_log.setEnabled(False)
        self.cancel.setEnabled(True)
        self.progress.setRange(0, 0)
        self.progress.setFormat("Quellen werden geprüft …")
        self.job_progress.setRange(0, 0)
        self.job_progress.setFormat("Aufträge werden vorbereitet …")
        self.activity_detail.setText(f"Aktiv · prüfe {len(audios)} Auftrag/Aufträge mit FFprobe")
        self.kpi_values["active"].setText("Prüfung")
        self._status("PRÜFT")
        self.step_start.setText("3 · Start …")
        self.next_step.setText("Dateien werden geprüft. Danach startet die Verarbeitung automatisch.")
        self._write_log(f"Prüfe {len(audios)} Auftrag/Aufträge mit FFprobe.")

        def prepare() -> None:
            try:
                jobs = build_jobs(audios, media, options)
                issues = validate_pairs(jobs, options, audio_peak_limit=2)
                blocking = [item for item in issues if item.blocking]
                if blocking:
                    raise ValueError("\n".join(
                        f"{item.title}: {item.message} Lösung: {item.solution}"
                        for item in blocking[:6]
                    ))
                self.prepare_queue.put(("ok", (generation, jobs, options,
                                                [item for item in issues if not item.blocking])))
            except Exception as exc:
                self.prepare_queue.put(("error", (generation, f"{type(exc).__name__}: {exc}")))

        self.prepare_thread = threading.Thread(target=prepare, daemon=True, name="VideoBatch-Qt-Prepare")
        self.prepare_thread.start()

    def _request_probe(self) -> None:
        """Use the ordinary validated preparation and the normal batch runner."""
        if self.runner.running or self.preparing:
            return
        slideshow = getattr(self, "slideshow", None)
        if slideshow is not None and getattr(slideshow, "assignment_mode", "pairwise") != "pairwise":
            QMessageBox.information(
                self, "Probevideo für normale Dateipaare",
                "Der kurze Probelauf unterstützt derzeit ein Audio mit einem "
                "Bild oder Video. Für eine Diashow bitte die Vorschau im "
                "Diashow-Bereich verwenden."
            )
            return
        self._probe_pending = True
        self._probe_active = False
        self.open_probe_button.setVisible(False)
        self.open_probe_button.setEnabled(False)
        self._start()
        # If the ordinary validation blocked preparation, no probe must be
        # accidentally launched by a later click on Videos erstellen.
        if not self.preparing:
            self._probe_pending = False

    def _open_probe(self) -> None:
        if self._probe_file is not None and self._probe_file.is_file():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._probe_file)))
        else:
            QMessageBox.information(self, "Probevideo nicht verfügbar",
                                    "Das Probevideo ist nicht mehr vorhanden.")

    def _cancel(self) -> None:
        if self.preparing and not self.runner.running:
            self._probe_pending = False
            self.prepare_generation += 1
            self.preparing = False
            self.progress.setRange(0, 100)
            self.progress.setValue(0)
            self.job_progress.setRange(0, 100)
            self.job_progress.setValue(0)
            self.job_progress.setFormat("Abgebrochen · %p %")
            self.activity_detail.setText("Abgebrochen · Vorbereitung sicher beendet")
            self.kpi_values["active"].setText("Nein")
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
        return qt_production_events._poll(self)

    def _show_start_error(self, message: str, phase: str) -> None:
        self._status("FEHLER")
        self._write_log(message)
        self.job_progress.setValue(0)
        self.job_progress.setFormat(f"{phase} fehlgeschlagen · %p %")
        self.activity_detail.setText(f"Fehler · {phase} beendet; technische Meldungen prüfen")
        self.kpi_values["active"].setText("Nein")
        self.cancel.setEnabled(False)
        self._refresh()
        reason, solution = explain_runtime_problem(message)
        self.next_step.setText(f"{reason} Nächster Schritt: {solution}")
        self.activity_detail.setText(f"{phase}: {reason}")

    def _drain_events(self) -> None:
        return qt_production_events._drain_events(self)

    def _finish_batch(self, payload) -> None:
        return qt_production_events._finish_batch(self, payload)

    def _load_jobs(self) -> None:
        return qt_production_events._load_jobs(self)

    def _row_status(self, row: int, text: str, progress: str | None=None, *, failed: bool=False) -> None:
        return qt_production_events._row_status(self, row, text, progress, failed=failed)

    def _write_log(self, message: str) -> None:
        if message.strip():
            self.log.appendPlainText(message.strip())

    def _status(self, text: str) -> None:
        update_status_chip(self.status, text)

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
        self._media_index_stop.set()
        self._save_dashboard_settings()
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
