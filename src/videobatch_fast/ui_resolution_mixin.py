from __future__ import annotations

from pathlib import Path
from tkinter import simpledialog
from typing import Callable

from .error_handling import ErrorDefinition, error_definition
from .paths import default_output_dir
from .permission_service import create_writable_subdirectory, ensure_writable_directory
from .quick_modes import QUICK_MODES
from .slideshow import SLIDESHOW_MODE_ALL_IMAGES
from .ui_components import SolutionDialog
from .text_resources import text
from .validation import ValidationIssue


class UiResolutionMixin:
    """Interactive, reversible solutions for missing settings and validation errors."""

    def _prepare_start_intelligently(self) -> bool:
        repaired: list[str] = []
        if self.quick_mode.get() not in QUICK_MODES:
            self._apply_quick_mode("smart_auto", rebuild=False)
            repaired.append("empfohlener Schnellmodus wiederhergestellt")

        raw_output = str(self.output_dir.get() or "").strip()
        requested = Path(raw_output).expanduser() if raw_output else default_output_dir()
        access = ensure_writable_directory(requested, default_output_dir())
        if access.writable and access.path != requested:
            self.output_dir.set(str(access.path))
            repaired.append(f"sicherer Ausgabeordner aktiviert: {access.path}")
        elif not access.writable:
            issue = ValidationIssue(
                "OUTPUT_PERMISSION",
                "Ausgabeordner kann nicht vorbereitet werden",
                access.message or str(requested),
                "Erstelle einen neuen Benutzerordner oder wähle ein anderes Ziel.",
                actions=("create_output_folder", "choose_output", "use_safe_output"),
            )
            self._show_validation_issue(issue)
            return False

        if self.archive_used.get() and not str(self.archive_project_dir.get() or "").strip():
            definition = ErrorDefinition(
                code="ARCHIVE_FOLDER_MISSING",
                title=text("ui.resolution.archive_folder_missing"),
                cause="Automatisches Aufräumen ist aktiviert, aber es wurde kein Zielordner festgelegt.",
                effect="Die Produktion wird vor dem Start angehalten, damit keine Datei an einen unbekannten Ort verschoben wird.",
                automatic_action="Originaldateien und Einstellungen wurden nicht verändert.",
                solution="Projektordner automatisch erstellen, selbst auswählen oder das Aufräumen für diesen Lauf deaktivieren.",
                alternative="Die Videos jetzt ohne automatische Dateiablage erstellen.",
                severity="blocking",
                actions=("create_project_folder", "choose_project_folder", "disable_archive"),
            )
            self._show_solution_dialog(definition, "Die fehlende Angabe kann direkt hier ergänzt werden.")
            return False

        if repaired:
            message = " · ".join(repaired)
            self.guidance_text.set(f"VideoBatch hat fehlende Einstellungen automatisch ergänzt: {message}.")
            self._event(
                "SETTINGS_AUTO_REPAIRED",
                "Einstellungen automatisch vervollständigt",
                message,
                level="success",
                solution="Zuordnung kurz prüfen; danach kann die Produktion starten.",
            )
        return True

    def _show_validation_issue(self, issue: ValidationIssue) -> None:
        actions = issue.actions or self._fallback_actions(issue.code)
        action_overrides: dict[str, Callable[[], None]] = {}
        cause = issue.message
        solution = issue.solution
        alternative = "Die Eingaben können angepasst oder der Vorgang später erneut gestartet werden."
        if issue.code == "AUDIO_MISSING":
            cause = f"Diese Audiodatei fehlt: {issue.message}"
            solution = (
                "Öffne zuerst die fehlende Zuordnung. VideoBatch markiert die betroffene Zeile; "
                "ergänze danach die Audiodatei oder entferne den verwaisten Eintrag."
            )
            alternative = "Audiodatei ergänzen und die Zuordnung anschließend erneut prüfen."
            action_overrides["focus_missing_audio"] = lambda name=issue.message: self._focus_missing_audio(name)
        definition = ErrorDefinition(
            code=issue.code,
            title=issue.title,
            cause=cause,
            effect="Der betroffene Schritt wurde vor einer unsicheren Änderung gestoppt.",
            automatic_action="Originaldateien, vorhandene Ausgaben und der bestätigte Projektzustand bleiben unverändert.",
            solution=solution,
            alternative=alternative,
            severity="blocking" if issue.blocking else "warning",
            actions=actions,
        )
        self._show_solution_dialog(
            definition,
            f"{issue.code}\n{issue.message}",
            action_overrides=action_overrides,
        )
        self.guidance_text.set(f"{issue.title}. Wähle im Lösungsfenster eine passende Aktion.")

    def _show_error(self, code: str, detail: str = "") -> None:
        self._show_solution_dialog(error_definition(code), detail)

    def _show_solution_dialog(
        self,
        definition: ErrorDefinition,
        detail: str = "",
        *,
        action_overrides: dict[str, Callable[[], None]] | None = None,
    ) -> None:
        actions = {
            "retry_runtime": self._refresh_runtime_status,
            "choose_output": self._choose_output_and_retry,
            "use_safe_output": self._use_safe_output_and_retry,
            "create_output_folder": self._create_output_folder_and_retry,
            "retry_validation": self._start,
            "focus_file_lists": self._focus_file_lists,
            "show_pairing": self._focus_pairing,
            "reselect_file": self._add_media,
            "add_audio": self._add_audio,
            "add_media": self._add_media,
            "switch_to_slideshow": self._switch_to_slideshow,
            "repair_settings": self._repair_settings_and_retry,
            "remove_missing": self._remove_missing,
            "open_external": self._open_selected_external,
            "probe_selected": self._probe_selected_media,
            "open_logs": self._open_logs,
            "open_install_help": self._show_help_center,
            "create_project_folder": self._create_project_folder,
            "choose_project_folder": self._choose_project_folder,
            "disable_archive": self._disable_archive_and_retry,
        }
        if action_overrides:
            actions.update(action_overrides)
        SolutionDialog(self.root, definition, detail, actions)

    @staticmethod
    def _fallback_actions(code: str) -> tuple[str, ...]:
        if code.startswith("OUTPUT") or code == "DISK_LOW":
            return ("create_output_folder", "choose_output", "use_safe_output")
        if code.startswith("AUDIO"):
            return ("add_audio", "remove_missing", "focus_file_lists")
        if code.startswith("MEDIA") or code.startswith("SLIDESHOW_IMAGE"):
            return ("add_media", "remove_missing", "focus_file_lists")
        if code == "NO_JOBS":
            return ("add_audio", "add_media", "switch_to_slideshow")
        return ("retry_validation", "open_logs")

    def _choose_output_and_retry(self) -> None:
        before = self.output_dir.get()
        self._choose_directory(self.output_dir)
        if self.output_dir.get() != before:
            self.root.after_idle(self._start)

    def _use_safe_output_and_retry(self) -> None:
        access = create_writable_subdirectory(default_output_dir().parent, "VideoBatch_Ausgabe")
        if not access.writable:
            self.guidance_text.set(access.message)
            return
        self.output_dir.set(str(access.path))
        self._save_settings()
        self.guidance_text.set(access.message)
        self.root.after_idle(self._start)

    def _create_output_folder_and_retry(self) -> None:
        name = simpledialog.askstring(
            "Neuen Ausgabeordner erstellen",
            "Name des neuen Ordners:",
            initialvalue="VideoBatch_Ausgabe",
            parent=self.root,
        )
        if name is None:
            return
        current = Path(str(self.output_dir.get() or default_output_dir())).expanduser()
        base = current if current.is_dir() else current.parent
        access = create_writable_subdirectory(base, name, fallback_base=default_output_dir().parent)
        if not access.writable:
            definition = ErrorDefinition(
                "OUTPUT_CREATE_FAILED",
                "Ordner konnte nicht erstellt werden",
                access.message,
                "Die Produktion wurde nicht gestartet.",
                "Es wurden keine Ausgabedateien verändert.",
                "Wähle einen anderen Zielordner oder verwende den sicheren Standardordner.",
                "Protokolle öffnen und Ordnerrechte prüfen.",
                "blocking",
                ("choose_output", "use_safe_output", "open_logs"),
            )
            self._show_solution_dialog(definition)
            return
        self.output_dir.set(str(access.path))
        self._save_settings()
        self.guidance_text.set(access.message)
        self.root.after_idle(self._start)

    def _repair_settings_and_retry(self) -> None:
        self._apply_quick_mode("smart_auto", rebuild=True)
        self.root.after_idle(self._start)

    def _switch_to_slideshow(self) -> None:
        self._set_assignment_mode(SLIDESHOW_MODE_ALL_IMAGES)
        self.guidance_text.set("Diashowmodus aktiviert. Alle Bilder werden automatisch auf jedes Audio angewendet.")

    def _focus_file_lists(self) -> None:
        try:
            self.main_notebook.select(1)
            self.audio_tree.focus_set()
        except Exception:
            pass

    def _focus_missing_audio(self, filename: str) -> None:
        target = Path(str(filename)).name

        # Prefer the actual production pairing because that is the actionable row
        # the user needs to repair. Selection is purely UI state; no project data
        # is modified by this navigation step.
        try:
            self._focus_pairing()
            for iid in self.pair_tree.get_children():
                values = self.pair_tree.item(iid, "values") or ()
                if len(values) > 1 and Path(str(values[1])).name == target:
                    self.pair_tree.selection_set(iid)
                    self.pair_tree.focus(iid)
                    self.pair_tree.see(iid)
                    self.guidance_text.set(
                        f"Fehlende Audio-Zuordnung markiert: {target}. "
                        "Audiodatei ergänzen oder den verwaisten Eintrag entfernen."
                    )
                    return
        except Exception:
            pass

        # Fallback for incomplete pairing views: open the audio library and mark
        # the matching source row if it is still present as an offline entry.
        self._focus_file_lists()
        try:
            if hasattr(self, "library_notebook") and hasattr(self, "audio_tab"):
                self.library_notebook.select(self.audio_tab)
            for iid, path in getattr(self, "tree_path_map", {}).items():
                if str(iid).startswith("audio:") and Path(path).name == target:
                    self.audio_tree.selection_set(iid)
                    self.audio_tree.focus(iid)
                    self.audio_tree.see(iid)
                    self.audio_tree.focus_set()
                    self.guidance_text.set(
                        f"Fehlende Audiodatei markiert: {target}. "
                        "Datei ergänzen oder den Eintrag entfernen."
                    )
                    return
        except Exception:
            pass
        self.guidance_text.set(
            f"Die fehlende Audiodatei {target} ist in der aktuellen Liste nicht mehr sichtbar. "
            "Audiodatei ergänzen oder Zuordnung neu aufbauen."
        )

    def _focus_pairing(self) -> None:
        try:
            self.main_notebook.select(4)
            self.production_notebook.select(0)
            self.pair_tree.focus_set()
        except Exception:
            pass

    def _create_project_folder(self) -> None:
        project = str(self.project_name.get() or "VideoBatch_Projekt").strip()
        access = create_writable_subdirectory(Path.home() / "Videos" / "VideoBatchFast-Projekte", project)
        if not access.writable:
            self.guidance_text.set(access.message)
            return
        self.archive_project_dir.set(str(access.path))
        self._save_settings()
        self.guidance_text.set(f"Projektordner erstellt: {access.path}")
        self.root.after_idle(self._start)

    def _choose_project_folder(self) -> None:
        before = self.archive_project_dir.get()
        self._choose_directory(self.archive_project_dir, project=True)
        if self.archive_project_dir.get() != before:
            self.root.after_idle(self._start)

    def _disable_archive_and_retry(self) -> None:
        self.archive_used.set(False)
        self._save_settings()
        self.guidance_text.set("Automatische Dateiablage wurde für diesen Lauf deaktiviert.")
        self.root.after_idle(self._start)
