from __future__ import annotations

import json
import shutil
import subprocess
import time
from dataclasses import asdict
from collections import Counter
from pathlib import Path
from tkinter import END, filedialog, messagebox

from .archive_service import append_manifest, archive_file, recover_archive_transactions
from .config import save_config
from .paths import state_dir
from .plugin_approvals import build_identity, grant_approval, revoke_approval, validate_approval
from .plugin_approval_manager import PluginApprovalManagerDialog
from .plugin_permissions import permission_summary
from .plugin_runtime import run_plugin_in_sandbox
from .plugins import scan_plugins
from .probe import ffmpeg_version, probe_media
from .registry import validate_registries
from .text_resources import text
from .ui_components import HelpCenterDialog
from .updates import apply_update_package, validate_update_package
from .validation import validate_runtime
from .versioning import build_label
from .visual_approval import sign_visual_approval, verify_visual_approval
from .visual_inspection import write_inspection_html
from .workflow_dialogs import PluginPermissionDecisionDialog, VisualApprovalSignDialog, archive_preview_dialog, update_assistant_dialog


class UiServicesMixin:

    def _help_system_status(self) -> str:
        try:
            validate_registries()
            return text("help_center.ready", ffmpeg=ffmpeg_version())
        except Exception as exc:
            return text("help_center.blocked", detail=str(exc))

    def _open_local_help_target(self, target: Path) -> None:
        opener = shutil.which("xdg-open")
        if not opener:
            messagebox.showerror(
                text("help_center.title"),
                text("help_center.open_missing", path=str(target)),
                parent=self.root,
            )
            return
        try:
            subprocess.Popen(
                [opener, str(target)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as exc:
            messagebox.showerror(
                text("help_center.title"),
                text("help_center.open_failed", detail=str(exc), path=str(target)),
                parent=self.root,
            )

    def _open_help_logs(self) -> None:
        target = state_dir() / "logs"
        target.mkdir(parents=True, exist_ok=True)
        self._open_local_help_target(target)

    def _open_help_manual(self) -> None:
        root = Path(__file__).resolve().parents[2]
        target = root / "START_HIER_save_.md"
        if not target.is_file():
            target = root / "README.md"
        self._open_local_help_target(target)

    def _show_help_center(self) -> None:
        HelpCenterDialog(
            self.root,
            system_status=self._help_system_status(),
            on_refresh=self._help_system_status,
            on_open_logs=self._open_help_logs,
            on_open_manual=self._open_help_manual,
            on_run_fault_lab=self._run_fault_lab,
        )
        self._event(
            "HELP_CENTER_OPENED",
            "Hilfezentrum geöffnet",
            "Schnellstart, Statusanzeigen, Recovery und Systemzustand sind sichtbar.",
            level="success",
            solution="Benötigten Abschnitt öffnen oder Systemstatus neu prüfen.",
        )

    def _run_fault_lab(self) -> None:
        self.guidance_text.set(text("fault_lab.running"))
        self._event(
            "FAULT_LAB_STARTED",
            text("fault_lab.started_title"),
            text("fault_lab.started_message"),
            solution=text("fault_lab.started_solution"),
        )

        def worker() -> None:
            from .fault_lab import report_payload, run_fault_lab
            from .safe_io import atomic_write_json
            results = run_fault_lab()
            payload = report_payload(results)
            target = state_dir() / "fault_lab" / "latest.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_json(target, payload)
            self.events.put_legacy("fault_lab_finished", {"results": results, "report": target})

        if not self.tasks.start("fault-lab", worker):
            self.guidance_text.set(text("fault_lab.already_running"))

    def _archive_results_async(self, results) -> None:
        project = Path(self.archive_project_dir.get()).expanduser()
        suffix = self.archive_suffix.get()
        successful = [result for result in results if result.success]
        candidate_count = len({path for result in successful for path in (result.job.audio, *result.job.source_media)})
        decision = archive_preview_dialog(self.root, candidate_count, str(project), suffix).wait()
        if not decision:
            self._event("ARCHIVE_DECLINED", "Dateiablage verschoben", "Die erfolgreich verwendeten Quelldateien bleiben am Ursprungsort.", level="warning", solution="Dateiablage später erneut starten.")
            return

        def worker() -> None:
            recovered = recover_archive_transactions(project)
            if recovered:
                self.events.put_legacy("log", {"level": "warning", "message": f"Dateiablage · {len(recovered)} unvollständige Transaktion(en) sicher geprüft."})
            successful = [result for result in results if result.success]
            all_jobs = [result.job for result in results]
            success_jobs = [result.job for result in successful]
            references = Counter(path for job in all_jobs for path in (job.audio, *job.source_media))
            successes = Counter(path for job in success_jobs for path in (job.audio, *job.source_media))
            records, failures = [], []
            for path, count in references.items():
                if successes[path] != count:
                    continue
                info = probe_media(path)
                try:
                    records.append(archive_file(path, project, info.kind, suffix))
                except Exception as exc:
                    failures.append(f"{path.name}: {exc}")
            manifest = append_manifest(project, records) if records else None
            message = f"{len(records)} Datei(en) sicher abgelegt."
            if failures:
                message += f" {len(failures)} Datei(en) blieben sicher am Ursprungsort."
            if manifest:
                message += f" Bericht: {manifest}"
            self.events.put_legacy("archive_finished", {"message": message, "failures": failures})

        self.tasks.start("archive", worker)
        self.guidance_text.set("Verwendete Dateien werden jetzt kopiert, geprüft und erst danach am Ursprungsort entfernt.")

    def _check_plugins(self) -> None:
        checks = scan_plugins(quarantine_invalid=True)
        if not checks:
            messagebox.showinfo(text('ui.services.plugins'), text('ui.services.keine_plugins_installiert_die_kernfunktionen_sind_vollstandig_verfugbar'))
            return
        lines: list[str] = []
        all_valid = True
        for item in checks:
            marker = "✓" if item.valid else "✕"
            quarantine_note = f"\n   Quarantäne: {item.quarantined_to}" if item.quarantined_to else ""
            lines.append(f"{marker} {item.plugin_id} {item.version}: {item.message}{quarantine_note}")
            if not item.valid:
                all_valid = False
                continue
            permissions = permission_summary(item.capability, item.key_id)
            identity = build_identity(
                plugin_id=item.plugin_id,
                version=item.version,
                payload_sha256=item.payload_sha256,
                key_id=item.key_id,
                capability=item.capability,
                permissions=permissions,
            )
            approval = validate_approval(identity)
            summary = permissions.plain_text(item.plugin_id, item.key_id) + f"\nVersion: {item.version}\nInhalts-Hash: {item.payload_sha256}"
            self._event(
                "PLUGIN_PERMISSIONS_SHOWN",
                "Plugin-Berechtigungen angezeigt",
                f"{item.plugin_id} · {permissions.title} · Freigabe {approval.status}",
                solution="Freigabe prüfen, erneuern oder widerrufen.",
                detail=summary + "\n\n" + approval.message,
            )
            decision = PluginPermissionDecisionDialog(self.root, summary, approval.status).wait()
            if decision == "revoke":
                revoked = revoke_approval(item.plugin_id)
                lines.append(f"   ! {revoked.message}")
                self._event("PLUGIN_APPROVAL_REVOKED", "Plugin-Freigabe widerrufen", item.plugin_id, level="warning", solution="Plugin bleibt inaktiv, bis es erneut geprüft und freigegeben wird.")
                continue
            if decision != "approve":
                lines.append("   • Keine neue Freigabe; Plugin bleibt unverändert oder inaktiv.")
                continue
            if item.capability == "validator":
                sandbox = run_plugin_in_sandbox(item.path, "validator", {"probe": True})
                sandbox_marker = "✓" if sandbox.success else "✕"
                result_note = f" Ergebnis={sandbox.result}" if sandbox.success else ""
                lines.append(f"   {sandbox_marker} Sandbox: {sandbox.message}{result_note}")
                all_valid = all_valid and sandbox.success
                if sandbox.success:
                    record = grant_approval(identity, permissions)
                    lines.append(f"   ✓ Freigabe gespeichert: {record['approved_at']}")
                    self._event("PLUGIN_APPROVAL_GRANTED", "Plugin-Freigabe gespeichert", f"{item.plugin_id} {item.version}", level="success", detail=f"Hash: {item.payload_sha256}", solution="Freigabe verfällt automatisch bei jeder Plugin- oder Berechtigungsänderung.")
                self._event(
                    "PLUGIN_SANDBOX_FINISHED",
                    "Plugin-Sandbox abgeschlossen",
                    f"{item.plugin_id}: {sandbox.message}",
                    level="success" if sandbox.success else "error",
                    solution="Plugin nur bei erfolgreichem Sandbox-Test verwenden.",
                )
            else:
                record = grant_approval(identity, permissions)
                lines.append(f"   ✓ Signatur, Berechtigungen und Freigabe gespeichert · {record['approved_at']}")
        value = "\n".join(lines)
        messagebox.showinfo(text('ui.services.plugin_prufung'), value)
        self._event("PLUGIN_SCAN", "Plugins geprüft", value, level="success" if all_valid else "warning", solution="Nur signierte, unveränderte und ausdrücklich freigegebene Plugins verwenden.")

    def _manage_plugin_approvals(self) -> None:
        def on_event(event_id: str, plugin_id: str, message: str) -> None:
            self._event(event_id, "Plugin-Freigabe geändert", f"{plugin_id}: {message}", level="warning", solution="Status in der Freigabeverwaltung erneut prüfen.")

        PluginApprovalManagerDialog(self.root, on_event=on_event)
        self._event("PLUGIN_APPROVAL_MANAGER_OPENED", "Plugin-Freigabeverwaltung geöffnet", "Aktive, abgelaufene und widerrufene Freigaben werden angezeigt.", solution="Nach Pluginänderungen Status und Hash kontrollieren.")

    def _sign_visual_approval_dialog(self) -> None:
        manifest_path = Path(__file__).resolve().parents[2] / "VISUAL_INSPECTION_MANIFEST.json"
        if not manifest_path.is_file():
            self._show_error("UNKNOWN", "Das visuelle Prüfmanifest fehlt. Führe zuerst die vollständige visuelle Prüfung aus.")
            return
        reviewer = VisualApprovalSignDialog(
            self.root,
            build_label(),
            default_reviewer=__import__("os").environ.get("USER", ""),
        ).wait()
        if not reviewer:
            return
        try:
            sign_visual_approval(
                manifest_path,
                reviewer=reviewer,
                build_id=build_label(),
                project_root=manifest_path.parent,
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            check = verify_visual_approval(manifest, manifest_path.parent)
            write_inspection_html(manifest_path.parent / "visual_inspection" / "index.html", manifest)
        except Exception as exc:
            self._event("VISUAL_APPROVAL_FAILED", "Visuelle Freigabe nicht erstellt", str(exc), level="error", solution="Alle visuellen Szenarien und Vertragsprüfungen zuerst erfolgreich abschließen.")
            messagebox.showerror(text('ui.services.freigabe_nicht_moglich'), str(exc), parent=self.root)
            return
        self._event(
            "VISUAL_APPROVAL_SIGNED",
            "Visuelle Desktop-Freigabe signiert",
            f"{reviewer} · Build {build_label()}",
            level="success",
            detail=f"Schlüssel: {check.key_id}\nDatum: {check.approved_at}",
            solution="HTML-Prüfoberfläche öffnen und Signaturstatus kontrollieren.",
        )
        messagebox.showinfo(text('ui.services.freigabe_signiert'), check.message, parent=self.root)

    def _check_update(self) -> None:
        package = filedialog.askopenfilename(title=text('ui.services.gepruftes_update_paket_wahlen'), filetypes=[("ZIP-Update", "*.zip")])
        if not package:
            return
        package_path = Path(package)
        check = validate_update_package(package_path, build_label())
        if not check.valid:
            self._show_error("UPDATE_INVALID", check.message)
            return
        self._event("UPDATE_VALIDATED", "Update-Paket geprüft", f"Version {check.version} · {len(check.files)} Datei(en)", level="success", solution="Kandidat erzeugen und Selbsttest starten.")
        proceed = update_assistant_dialog(self.root, check.version, len(check.files)).wait()
        if not proceed:
            self._event("UPDATE_DECLINED", "Update verschoben", f"Version {check.version} wurde nicht installiert.", level="warning", solution="Update später erneut auswählen.")
            return
        self.guidance_text.set("Update-Kandidat wird erstellt und vollständig getestet. Die aktuelle Installation bleibt bis zur Freigabe aktiv.")

        def worker() -> None:
            install_root = Path(__file__).resolve().parents[2]
            result = apply_update_package(
                package_path,
                install_root,
                build_label(),
                progress=lambda phase, detail: self.events.put_legacy("log", {"level": "info", "message": f"Update · {phase}: {detail}"}),
            )
            self.events.put_legacy("update_finished", {"result": result})

        self.tasks.start("update", worker)

    def _run_assurance(self) -> None:
        self.guidance_text.set("Anwendungsfälle werden isoliert simuliert. Produktdateien und Medien bleiben unverändert.")

        def worker() -> None:
            from .assurance import run_scenarios
            self.events.put_legacy("assurance_finished", {"results": run_scenarios()})

        self.tasks.start("assurance", worker)

    def _refresh_runtime_status(self) -> None:
        registry_errors = validate_registries()
        if registry_errors:
            self.status_text.set("Start blockiert · Registry inkonsistent")
            self.start_button.configure(state="disabled")
            self._event("REGISTRY_INVALID", "Registry-Prüfung fehlgeschlagen", "; ".join(registry_errors), level="error", solution="Vollständiges Paket erneut entpacken.")
            return
        issues = validate_runtime()
        if issues:
            self.status_text.set("Start blockiert · Laufzeitprüfung fehlgeschlagen")
            self.start_button.configure(state="disabled")
        else:
            self.status_text.set(f"Bereit · FFmpeg {ffmpeg_version()} · Registries geprüft")

    def _remove_missing(self) -> None:
        self.audios = [path for path in self.audios if path.is_file()]
        self.media = [path for path in self.media if path.is_file()]
        self._refresh_file_trees()
        self._rebuild_pairs()

    def _clear_lists(self) -> None:
        if self.runner.running:
            return
        self.audios.clear()
        self.media.clear()
        self._refresh_file_trees()
        self._rebuild_pairs()
        self.guidance_text.set(text("status.ready"))
        if hasattr(self, "_autosave_project"):
            self._autosave_project()

    def _open_output(self) -> None:
        path = Path(self.output_dir.get()).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        self._open_path(path)

    def _open_logs(self) -> None:
        self._open_path(state_dir())

    def _open_visual_inspection(self) -> None:
        target = Path(__file__).resolve().parents[2] / "visual_inspection" / "index.html"
        if not target.is_file():
            self._event("VISUAL_HTML_MISSING", "Visuelle Prüfseite fehlt", str(target), level="warning", solution="scripts/build_visual_inspection.py ausführen.")
            messagebox.showwarning(text('ui.services.visuelle_prufung'), text('ui.services.die_html_prufseite_wurde_noch_nicht_erzeugt_losung'))
            return
        self._open_path(target)
        self._event("VISUAL_HTML_OPENED", "Visuelle Prüfseite geöffnet", str(target), solution="Szenarien, Referenzen und Manifest im Browser prüfen.")

    @staticmethod
    def _open_path(path: Path) -> None:
        try:
            subprocess.Popen(["xdg-open", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError:
            pass

    def _event(
        self,
        event_id: str,
        title: str,
        message: str,
        *,
        level: str = "info",
        detail: str = "",
        solution: str = "",
        operation_id: str | None = None,
    ) -> None:
        correlation = operation_id or getattr(self, "current_operation_id", "general") or "general"
        record = self.logger.write(
            event_id,
            title,
            message,
            level=level,
            detail=detail,
            solution=solution,
            operation_id=correlation,
        )
        if hasattr(self, "_append_machine_event"):
            self._append_machine_event(asdict(record))
        self.event_tree.insert("", 0, values=(record.timestamp[11:19], level, title, solution or message))
        children = self.event_tree.get_children()
        if len(children) > 250:
            self.event_tree.delete(children[-1])
        self._log(level, f"{title} · {message}" + (f" · Lösung: {solution}" if solution else ""))

    def _log(self, level: str, message: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        marker = {"success": "✓", "warning": "!", "error": "✕", "technical": ">", "info": "•"}.get(level, "•")
        line = f"{timestamp}  {marker}  {message}\n"
        self.log_text.configure(state="normal")
        self.log_text.insert(END, line)
        self.log_text.see(END)
        self.log_text.configure(state="disabled")

    def _save_settings(self) -> None:
        save_config({
            "schema_version": 3,
            "output_dir": self.output_dir.get(),
            "output_mode": self.output_mode.get(),
            "theme": self.theme_name.get(),
            "auto_open_output": self.auto_open_output.get(),
            "resolution": self.resolution.get(),
            "codec": self.codec.get(),
            "profile": self.profile.get(),
            "verification": self.verification.get(),
            "font_scale": self.global_font_scale.get(),
            "window_geometry": self.root.geometry(),
            "keep_lists": self.keep_lists.get(),
            "visual_effect": self.visual_effect.get(),
            "transition": self.transition.get(),
            "quick_mode": self.quick_mode.get(),
            "assignment_mode": self.assignment_mode.get(),
            "slideshow_transition": self.slideshow_transition.get(),
            "slideshow_scene_sync": self.slideshow_scene_sync.get(),
            "slideshow_order_mode": self.slideshow_order_mode.get(),
            "slideshow_random_seed": self.slideshow_random_seed.get(),
            "slideshow_start_image": self.slideshow_start_image.get(),
            "slideshow_end_image": self.slideshow_end_image.get(),
            "audio_sort": self.audio_sort.get(),
            "media_sort": self.media_sort.get(),
            "last_audio_dir": self.last_audio_dir.get(),
            "last_media_dir": self.last_media_dir.get(),
            "area_zoom": dict(self.area_zoom),
            "archive_used": self.archive_used.get(),
            "archive_project_dir": self.archive_project_dir.get(),
            "archive_suffix": self.archive_suffix.get(),
            "playlist_repeat": self.playlist.repeat,
            "playlist_shuffle": self.playlist.shuffle,
            "preview_zoom": self.preview_zoom.get(),
            "active_tab": int(self.main_notebook.index(self.main_notebook.select())) if hasattr(self, "main_notebook") else 0,
            "workflow_layout_mode": self.config.get("workflow_layout_mode", "two_columns"),
            "current_project_file": str(getattr(self, "project_file", "") or ""),
        })

    def _close(self) -> None:
        # A double click on the window close control must never run the shutdown
        # sequence twice.  In particular, two concurrent waits/cancels can make Tk
        # appear frozen even though every individual service is bounded.
        if getattr(self, "_shutdown_in_progress", False):
            return
        if self.runner.running and not messagebox.askyesno(
            text('ui.services.provoware_videoautomation_2026_beenden'),
            text('ui.services.ein_stapel_lauft_noch_prozess_kontrolliert_abbrechen_und'),
        ):
            return
        self._shutdown_in_progress = True
        shutdown_errors: list[str] = []
        try:
            if self.runner.running:
                try:
                    self.runner.cancel()
                    self.runner.wait(timeout=8.0)
                except Exception as exc:
                    shutdown_errors.append(f"Renderprozess: {type(exc).__name__}: {exc}")
            try:
                self._cancel_pending_selection_preview()
                preview_stopped = self.selection_previews.shutdown(timeout=3.0)
                if not preview_stopped:
                    self._event(
                        "SELECTION_PREVIEW_PENDING",
                        "Vorschau wird noch beendet",
                        "Der letzte Vorschauprozess reagiert verzögert.",
                        level="warning",
                        solution="VideoBatch wurde trotzdem kontrolliert geschlossen; beim nächsten Start Protokoll prüfen.",
                    )
            except Exception as exc:
                shutdown_errors.append(f"Auswahlvorschau: {type(exc).__name__}: {exc}")
            try:
                unfinished = self.tasks.shutdown(timeout=4.0)
                if unfinished:
                    self._event(
                        "BACKGROUND_TASKS_PENDING",
                        "Hintergrundaufgaben noch aktiv",
                        ", ".join(unfinished),
                        level="warning",
                        solution="Beim nächsten Start Diagnosebericht prüfen.",
                    )
            except Exception as exc:
                shutdown_errors.append(f"Hintergrundaufgaben: {type(exc).__name__}: {exc}")
            try:
                self.audio_player.stop()
            except Exception as exc:
                shutdown_errors.append(f"Audioplayer: {type(exc).__name__}: {exc}")
            if hasattr(self, "_autosave_project"):
                try:
                    self._autosave_project(force=True)
                except Exception as exc:
                    shutdown_errors.append(f"Projekt speichern: {type(exc).__name__}: {exc}")
            try:
                self._save_settings()
            except Exception as exc:
                shutdown_errors.append(f"Einstellungen speichern: {type(exc).__name__}: {exc}")
            if shutdown_errors:
                try:
                    self._event(
                        "SHUTDOWN_PARTIAL_FAILURE",
                        "Schließen mit Teilfehlern",
                        " | ".join(shutdown_errors),
                        level="warning",
                        solution="Die Anwendung wurde dennoch beendet. Beim nächsten Start Diagnosebericht prüfen.",
                    )
                except Exception:
                    pass
        finally:
            # Closing must remain guaranteed even when persistence or a background
            # service reports an error.  This prevents a half-shut-down UI that no
            # longer accepts input but remains on screen.
            try:
                self.root.destroy()
            except Exception:
                pass

    @staticmethod
    def _duration(seconds: float | None) -> str:
        if not seconds:
            return "–"
        value = int(seconds)
        return f"{value // 60:02d}:{value % 60:02d}"

    @staticmethod
    def _clock(seconds: float | None) -> str:
        return UiServicesMixin._duration(seconds)

    @staticmethod
    def _size(size: int) -> str:
        if size >= 1024**3:
            return f"{size / 1024**3:.2f} GB"
        if size >= 1024**2:
            return f"{size / 1024**2:.1f} MB"
        if size >= 1024:
            return f"{size / 1024:.1f} KB"
        return f"{size} B"
