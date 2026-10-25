from __future__ import annotations
import queue
from pathlib import Path
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QMessageBox, QTableWidgetItem,
)
from .display_formatting import format_clock, format_eta, format_size
from .probe_render import plan_probe, probe_output, prune_probes
from .resource_estimation import estimate_job_output_bytes
from .qt_ui_polish import (
    job_table_item,
)


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
            self.job_progress.setRange(0, 100)
            if kind == "error":
                self._probe_pending = False
                self._show_start_error(str(data), "Vorbereitung")
            else:
                self.jobs = list(data)
                options = rest[0]
                notices = rest[1] if len(rest) > 1 else []
                if notices:
                    details = "\n\n".join(
                        f"• {notice.title}: {notice.message}\n{notice.solution}"
                        for notice in notices[:5]
                    )
                    if len(notices) > 5:
                        details += f"\n\nWeitere Hinweise: {len(notices) - 5}"
                    response = QMessageBox.question(
                        self, "Hinweise vor der Videoerstellung",
                        details + "\n\nTrotz dieser Hinweise fortfahren?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No,
                    )
                    if response != QMessageBox.StandardButton.Yes:
                        self._probe_pending = False
                        self._status("ABGEBROCHEN")
                        self._write_log("Produktion nach Hinweisen nicht gestartet.")
                        self._refresh()
                        return
                if not self._probe_pending:
                    estimated = sum(estimate_job_output_bytes(j, options) for j in self.jobs)
                    self._write_log(
                        f"Grobe Dateigrößenschätzung: {estimated / 1024**2:.0f} MiB "
                        "einschließlich Auftragsreserve; keine Größen- oder Laufzeitgarantie."
                    )
                if self._probe_pending:
                    self._probe_pending = False
                    try:
                        destination = probe_output()
                        short_job, options = plan_probe(
                            self.jobs[0], options, destination
                        )
                        self.jobs = [short_job]
                        self._probe_file = destination
                        self._probe_active = True
                        prune_probes(destination.parent, keep=10)
                    except (ValueError, OSError, IndexError) as exc:
                        self._probe_active = False
                        self._show_start_error(str(exc), "Probevorbereitung")
                        self._drain_events()
                        return
                self._load_jobs()
                try:
                    self.runner.start(self.jobs, options)
                except Exception as exc:
                    self._probe_active = False
                    self._show_start_error(f"{type(exc).__name__}: {exc}", "Start")
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
            self.job_progress.setValue(0)
            self.job_progress.setFormat("Auftrag startet · %p %")
            self.kpi_values["done"].setText("0")
            self.kpi_values["active"].setText("Ja")
            self._status("LÄUFT")
            self.step_start.setText("3 · Läuft …")
            self.next_step.setText("Produktion läuft. Fortschritt und Abbrechen bleiben hier immer sichtbar.")
        elif name == "job_started":
            position, total = int(p.get("position", 1)), int(p.get("total", len(self.jobs)))
            self._row_status(position - 1, "Läuft …", "0 %")
            self.activity_detail.setText(f"Aktiv · Auftrag {position}/{total} wird gestartet")
        elif name == "progress":
            snap = p.get("snapshot")
            value = float(getattr(snap, "total_percent", 0.0) or 0.0)
            value = value * 100.0 if 0 <= value <= 1 else value
            self.progress.setValue(max(0, min(100, round(value))))
            self.progress.setFormat(f"{getattr(snap, 'phase', 'Verarbeitung')} · %p %")
            job_value = max(0, min(100, round(float(getattr(snap, "job_percent", 0.0) or 0.0))))
            position = int(getattr(snap, "job_index", 0) or 0)
            total = int(getattr(snap, "job_total", len(self.jobs)) or len(self.jobs))
            self.job_progress.setValue(job_value)
            self.job_progress.setFormat(f"Auftrag {position}/{total} · %p %")
            self._row_status(position - 1, "Läuft …", f"{job_value} %")
            elapsed_seconds = float(getattr(snap, "elapsed_seconds", 0.0) or 0.0)
            elapsed = format_clock(elapsed_seconds)
            eta = format_eta(getattr(snap, "eta_seconds", None), elapsed_seconds, job_value)
            speed = getattr(snap, "speed", "") or "aktiv"
            size = format_size(int(getattr(snap, "output_size", 0) or 0))
            idle = float(getattr(snap, "last_activity_seconds", 0.0) or 0.0)
            self.activity_detail.setText(
                f"Aktiv · Auftrag {position}/{total} · Phase: {getattr(snap, 'phase', 'Verarbeitung')} · "
                f"Zeit {elapsed} · ETA {eta} · {speed} · Ausgabe {size} · Signal vor {idle:.0f} s"
            )
        elif name == "job_finished":
            result, pos = p.get("result"), int(p.get("position", 1))
            success = bool(getattr(result, "success", False))
            status = "Fertig ✓" if success else "⚠ Fehler · Protokoll prüfen"
            self._row_status(pos - 1, status, "100 %" if success else "Fehler", failed=not success)
            self.job_progress.setValue(100 if success else self.job_progress.value())
            completed = int(self.kpi_values["done"].text() or "0") + int(success)
            self.kpi_values["done"].setText(str(completed))
            if getattr(result, "message", ""):
                self._write_log(f"Auftrag {pos}: {result.message}")
        elif name in {"job_failed_internal", "batch_failed_internal"}:
            self._status("SCHUTZSTOPP" if name == "batch_failed_internal" else "FEHLER")
            self._write_log(str(p.get("message", "")))
        elif name == "log":
            self._write_log(str(p.get("message", "")))
        elif name == "batch_finished":
            self._finish_batch(p)


def _finish_batch(self, payload) -> None:
    ok = int(payload.get("successes", 0))
    failed = int(payload.get("failures", 0))
    open_ = int(payload.get("unprocessed", 0))
    cancelled = bool(payload.get("cancelled"))
    self._status("ABGEBROCHEN" if cancelled else ("FERTIG" if not failed and not open_ else "FERTIG MIT HINWEIS"))
    if not failed and not open_ and not cancelled:
        self.progress.setValue(100)
    self.progress.setFormat("Abgeschlossen · %p %")
    self.cancel.setEnabled(False)
    self.kpi_values["active"].setText("Nein")
    self.kpi_values["done"].setText(str(ok))
    self.open_output.setEnabled(Path(self.output.text().strip()).expanduser().is_dir())
    self.show_result_log.setEnabled(bool(self.log.toPlainText().strip()))
    self.activity_detail.setText(f"Beendet · {ok} erfolgreich · {failed} Fehler · {open_} offen")
    self._write_log(f"Abschluss: {ok} erfolgreich · {failed} Fehler · {open_} offen.")
    for row in range(max(0, self.table.rowCount() - open_), self.table.rowCount()):
        self._row_status(row, "Nicht gestartet", "–")
    self._refresh(preserve_results=True)
    if self._probe_active:
        self._probe_active = False
        good = ok == 1 and not failed and not open_ and not cancelled
        self.open_probe_button.setVisible(good)
        self.open_probe_button.setEnabled(good)
        if good:
            self.next_step.setText(
                "Probevideo fertig (höchstens 10 Sekunden). "
                "Mit „Probevideo öffnen“ das Ergebnis prüfen. "
                "Die normale Ausgabe wurde nicht verändert."
            )
        else:
            self.next_step.setText(
                "Probevideo nicht erfolgreich. Fehlerdetails unter "
                "„Technische Meldungen anzeigen“ prüfen."
            )


def _load_jobs(self) -> None:
    self.table.setRowCount(len(self.jobs))
    for row, job in enumerate(self.jobs):
        for col, text in enumerate((str(job.index), job.audio.name, job.media.name, "Geprüft", "0 %")):
            self.table.setItem(row, col, job_table_item(text, col))
        duration = job.audio_info.duration
        duration_text = f"{duration:.1f} Sekunden" if duration else "unbekannt"
        self.table.item(row, 1).setToolTip(
            f"Audio: {job.audio}\nAudiodauer: {duration_text}"
        )
        self.table.item(row, 2).setToolTip(
            f"Medium: {job.media}\nAusgabe: {job.output.name}\nZiel: {job.output.parent}"
        )
    if self.jobs:
        first = self.jobs[0]
        self.pairing_summary_label.setText(
            f"✓ {len(self.jobs)} Auftrag/Aufträge geprüft. "
            f"Beispiel: {first.audio.name} + {first.media.name} → {first.output.name}. "
            "Dateidetails stehen in den beiden Spalten als Hinweis bereit."
        )


def _row_status(self, row: int, text: str, progress: str | None = None, *, failed: bool = False) -> None:
    if 0 <= row < self.table.rowCount():
        if self.table.item(row, 3) is None:
            self.table.setItem(row, 3, QTableWidgetItem())
        self.table.item(row, 3).setText(text)
        if progress is not None:
            if self.table.item(row, 4) is None:
                self.table.setItem(row, 4, QTableWidgetItem())
            self.table.item(row, 4).setText(progress)
        if failed:
            for column in range(self.table.columnCount()):
                item = self.table.item(row, column)
                if item is not None:
                    item.setBackground(QColor("#4a1722"))
                    item.setForeground(QColor("#ffffff"))
                    item.setToolTip("Auftrag fehlgeschlagen. Ergebnisprotokoll öffnen und Ursache prüfen.")
