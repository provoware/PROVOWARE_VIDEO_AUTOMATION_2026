from __future__ import annotations

import shlex
from pathlib import Path
from tkinter import messagebox

from .text_resources import text
from .models import PairJob
from .quick_modes import mode_spec


class UiEventHandlersMixin:
    def _handle_event(self, name: str, payload: dict) -> None:
        self.current_operation_id = str(payload.get("operation_id", self.current_operation_id or "general"))
        handlers = {
            "batch_started": self._handle_batch_started,
            "job_started": self._handle_job_started,
            "command": self._handle_command,
            "progress": self._handle_progress_event,
            "log": self._handle_log_event,
            "job_finished": self._handle_job_finished,
            "batch_failed_internal": self._handle_batch_internal_error,
            "batch_finished": self._handle_batch_finished,
            "preview_ready": self._handle_preview_ready,
            "preview_failed": self._handle_preview_failed,
            "selection_preview_ready": self._handle_selection_preview_ready,
            "selection_preview_failed": self._handle_selection_preview_failed,
            "archive_finished": self._handle_archive_finished,
            "update_finished": self._handle_update_finished,
            "assurance_finished": self._handle_assurance_finished,
            "fault_lab_finished": self._handle_fault_lab_finished,
            "waveform_ready": self._handle_waveform_ready,
            "waveform_failed": self._handle_waveform_failed,
        }
        handler = handlers.get(name)
        if handler is not None:
            handler(payload)

    def _handle_batch_started(self, payload: dict) -> None:
        self._log("info", f"Stapel mit {payload['total']} Auftrag/Aufträgen gestartet.")

    def _handle_job_started(self, payload: dict) -> None:
        job: PairJob = payload["job"]
        media_label = f"{len(job.media_sequence)} Bilder" if job.is_slideshow else job.media.name
        self.current_job.set(f"Auftrag {payload['position']}/{payload['total']} · {job.audio.name} + {media_label}")
        mode = "Auto-Diashow" if job.is_slideshow else ("Direktkopie" if job.fast_path else f"1-Pass · {mode_spec(self.quick_mode.get()).label}")
        self.phase.set(mode)
        self._event("JOB_STARTED", "Auftrag gestartet", f"{job.audio.name} + {media_label}", solution=f"Verarbeitung: {mode}")

    def _handle_command(self, payload: dict) -> None:
        self._log("technical", " ".join(shlex.quote(part) for part in payload["command"]))

    def _handle_progress_event(self, payload: dict) -> None:
        self._update_progress(payload["snapshot"])

    def _handle_log_event(self, payload: dict) -> None:
        self._log(payload.get("level", "info"), payload.get("message", ""))

    def _handle_job_finished(self, payload: dict) -> None:
        result = payload["result"]
        self._event(
            "JOB_FINISHED",
            "Auftrag erfolgreich" if result.success else "Auftrag fehlgeschlagen",
            result.message,
            level="success" if result.success else "error",
            solution="Nächsten Auftrag verarbeiten." if result.success else "Technische Details und sichere Alternative prüfen.",
        )

    def _handle_batch_internal_error(self, payload: dict) -> None:
        self._event(
            "BATCH_FAILED_INTERNAL",
            "Interner Stapelfehler sicher abgefangen",
            payload.get("message", "Interner Fehler"),
            level="error",
            detail=payload.get("traceback", ""),
            solution="Diagnosebericht öffnen und Auftrag nach Prüfung erneut starten.",
        )

    def _handle_batch_finished(self, payload: dict) -> None:
        self.last_results = payload["results"]
        self.start_button.configure(state="normal")
        self.cancel_button.configure(state="disabled")
        self.phase.set("Abgeschlossen" if not payload["cancelled"] else "Abgebrochen")
        self.status_text.set(f"Fertig · {payload['successes']} erfolgreich · {payload['failures']} fehlgeschlagen")
        self.guidance_text.set("Videoerstellung abgeschlossen. Ergebnisse prüfen und optional verwendete Dateien sicher aufräumen.")
        self._event(
            "BATCH_FINISHED",
            "Stapel abgeschlossen",
            f"{payload['successes']} erfolgreich · {payload['failures']} fehlgeschlagen",
            level="success" if not payload["failures"] else "warning",
            solution="Ausgaben prüfen; optional Dateiablage starten.",
        )
        self._finish_batch_lists(payload)
        self._autosave_project(force=True)
        if payload["successes"] and not payload["cancelled"] and self.auto_open_output.get():
            self.root.after(350, lambda: self._open_result_folders(payload["results"]))


    def _open_result_folders(self, results) -> None:
        folders: list[Path] = []
        for result in results:
            if not getattr(result, "success", False):
                continue
            output = Path(getattr(getattr(result, "job", None), "output", self.output_dir.get())).expanduser()
            folder = output.parent if output.suffix else output
            if folder not in folders:
                folders.append(folder)
        if not folders:
            folders = [Path(self.output_dir.get()).expanduser()]
        for folder in folders[:3]:
            try:
                folder.mkdir(parents=True, exist_ok=True)
            except OSError:
                continue
            self._open_path(folder)
        shown = ", ".join(str(path) for path in folders[:3])
        self.guidance_text.set(f"Produktion abgeschlossen. Ausgabeordner geöffnet: {shown}")
        self._event(
            "OUTPUT_FOLDERS_OPENED",
            "Ausgabeordner geöffnet",
            shown,
            level="success",
            solution="Ergebnisse im Dateimanager prüfen.",
        )

    def _finish_batch_lists(self, payload: dict) -> None:
        if self.archive_used.get() and payload["successes"] and not payload["cancelled"]:
            self._archive_results_async(payload["results"])
        elif not self.keep_lists.get() and not payload["cancelled"]:
            self._clear_lists()

    def _handle_preview_ready(self, payload: dict) -> None:
        if payload.get("request_id") == self.preview_request:
            self._show_preview(payload["path"], payload["preview"])

    def _handle_preview_failed(self, payload: dict) -> None:
        if payload.get("request_id") != self.preview_request:
            return
        self.preview_status.set("Vorschau nicht möglich · Datei kann separat geprüft werden")
        self._show_error("PREVIEW_FAILED", payload.get("message", ""))


    def _handle_selection_preview_ready(self, payload: dict) -> None:
        self._apply_selection_preview(payload)

    def _handle_selection_preview_failed(self, payload: dict) -> None:
        self._apply_selection_preview_failure(payload)

    def _handle_archive_finished(self, payload: dict) -> None:
        self._event(
            "ARCHIVE_FINISHED",
            "Dateiablage abgeschlossen",
            payload["message"],
            level="success" if not payload.get("failures") else "warning",
            solution="Aufräumbericht prüfen.",
        )
        self.guidance_text.set(payload["message"])
        self._refresh_file_trees()

    def _handle_update_finished(self, payload: dict) -> None:
        result = payload["result"]
        if not result.success:
            self._show_error("UPDATE_INVALID", result.message + (f"\nBericht: {result.report}" if result.report else ""))
            return
        self._event(
            "UPDATE_INSTALLED",
            "Update installiert",
            result.message,
            level="success",
            detail=f"Backup: {result.backup}\nBericht: {result.report}",
            solution="VideoBatch neu starten.",
        )
        messagebox.showinfo(text('ui.event_handlers.update_installiert'), result.message + "\n\nBitte VideoBatch jetzt neu starten.")
        self.guidance_text.set("Update installiert. VideoBatch neu starten, damit die neue Version aktiv wird.")

    def _handle_assurance_finished(self, payload: dict) -> None:
        results = payload["results"]
        passed = sum(result.status in {"pass", "blocked", "healed", "safe_failure"} for result in results)
        failed = len(results) - passed
        detail = "\n".join(f"{result.scenario_id}: {result.status} · {result.message}" for result in results)
        self._event(
            "ASSURANCE_FINISHED",
            "Anwendungsfälle simuliert",
            f"{passed}/{len(results)} erwartungsgemäß · {failed} fehlgeschlagen",
            level="success" if not failed else "error",
            detail=detail,
            solution="Fehlgeschlagene Szenarien vor Release beheben." if failed else "Keine Aktion nötig.",
        )
        messagebox.showinfo(
            text('ui.event_handlers.anwendungssimulation'),
            f"{passed}/{len(results)} Szenarien erwartungsgemäß\n{failed} fehlgeschlagen\n\nDetails wurden protokolliert.",
        )
        self.guidance_text.set("Anwendungssimulation abgeschlossen. Details stehen in Ereignissen und Protokollen.")



    def _handle_fault_lab_finished(self, payload: dict) -> None:
        results = payload["results"]
        passed = sum(item.status == "pass" for item in results)
        failed = len(results) - passed
        detail = "\n".join(f"{item.scenario_id}: {item.status} · {item.message}" for item in results)
        report = payload.get("report")
        self._event(
            "FAULT_LAB_FINISHED",
            text("fault_lab.finished_title"),
            text("fault_lab.finished_message", passed=passed, total=len(results), failed=failed),
            level="success" if not failed else "error",
            detail=detail + (f"\nBericht: {report}" if report else ""),
            solution=text("fault_lab.success_solution") if not failed else text("fault_lab.failure_solution"),
        )
        messagebox.showinfo(
            text("fault_lab.dialog_title"),
            text("fault_lab.dialog_message", passed=passed, total=len(results), failed=failed, report=report or "-"),
            parent=self.root,
        )
        self.guidance_text.set(text("fault_lab.finished_guidance", passed=passed, total=len(results)))
