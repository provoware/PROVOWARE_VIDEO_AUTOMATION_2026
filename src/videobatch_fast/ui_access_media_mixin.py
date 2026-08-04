from __future__ import annotations

import os
from pathlib import Path
from tkinter import filedialog, messagebox

from .media_import_dialog import MediaImportDialog
from .paths import default_output_dir
from .permission_service import downloads_dir, ensure_writable_directory, is_writable_directory
from .probe import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS
from .text_resources import text
from .versioning import build_label
from .validation import ValidationIssue


class UiAccessMediaMixin:
    """Media import, directory access and permission feedback."""

    def _add_audio(self) -> None:
        dialog = MediaImportDialog(self.root, audio=True, initial_dir=Path(self.last_audio_dir.get() or downloads_dir()))
        if dialog.result:
            self.last_audio_dir.set(str(dialog.result[0].parent))
            self._append_paths(dialog.result, True)
            self._save_settings()

    def _add_media(self) -> None:
        dialog = MediaImportDialog(self.root, audio=False, initial_dir=Path(self.last_media_dir.get() or downloads_dir()))
        if dialog.result:
            self.last_media_dir.set(str(dialog.result[0].parent))
            self._append_paths(dialog.result, False)
            self._save_settings()

    def _add_media_folder(self) -> None:
        initial = self.last_media_dir.get() or str(downloads_dir())
        selected = filedialog.askdirectory(initialdir=initial, title=text("ui.media_panels.add_folder"))
        if not selected:
            return
        folder = Path(selected).expanduser()
        self.last_media_dir.set(str(folder))
        dialog = MediaImportDialog(self.root, audio=False, initial_dir=folder)
        if dialog.result:
            self._append_paths(dialog.result, False)
        self._save_settings()

    def _open_preview_tab(self) -> None:
        try:
            self.main_notebook.select(2)
        except Exception:
            pass

    def _sort_from_heading(self, audio: bool, column: str) -> None:
        mapping = {
            "name": ("name_asc", "name_desc"),
            "size": ("size_asc", "size_desc"),
            "date": ("modified_new", "modified_old"),
            "duration": ("duration_short", "duration_long"),
            "type": ("type", "type"),
        }
        first, second = mapping.get(column, ("import", "import"))
        variable = self.audio_sort if audio else self.media_sort
        key = second if variable.get() == first else first
        self._set_sort(audio, key)

    def _choose_directory(self, variable, project: bool = False) -> None:
        initial = variable.get() or (str(downloads_dir()) if project else str(default_output_dir()))
        selected = filedialog.askdirectory(initialdir=initial)
        if not selected:
            return
        candidate = Path(selected).expanduser()
        if project:
            if not candidate.is_dir() or not os.access(candidate, os.R_OK | os.X_OK):
                self._show_validation_issue(ValidationIssue(
                    "PROJECT_DIRECTORY_PERMISSION",
                    "Projektordner ist nicht erreichbar",
                    str(candidate),
                    "Erstelle einen neuen Projektordner oder wähle einen lesbaren Benutzerordner.",
                    actions=("create_project_folder", "choose_project_folder", "disable_archive"),
                ))
                return
            variable.set(str(candidate))
            self._save_settings()
            return
        access = ensure_writable_directory(candidate, default_output_dir())
        if not access.writable:
            self._show_validation_issue(ValidationIssue(
                "OUTPUT_PERMISSION",
                "Ausgabeordner ist nicht beschreibbar",
                access.message or str(candidate),
                "Erstelle einen neuen Ausgabeordner oder wähle ein anderes Ziel.",
                actions=("create_output_folder", "choose_output", "use_safe_output"),
            ))
            return
        variable.set(str(access.path))
        if access.repaired:
            self.guidance_text.set(access.message)
            self._event(
                "OUTPUT_DIRECTORY_REPAIRED",
                "Ausgabeordner automatisch repariert",
                access.message,
                level="success",
                solution="Der neue Ordner ist bereits aktiv.",
            )
        self._save_settings()

    def _open_downloads(self) -> None:
        target = downloads_dir()
        target.mkdir(parents=True, exist_ok=True)
        self._open_path(target)

    def _show_permission_status(self) -> None:
        checks = {
            "Downloads": downloads_dir(),
            "Ausgabe": Path(self.output_dir.get()).expanduser(),
            "Konfiguration": Path.home() / ".config" / "VideoBatchFast",
            "Status": Path.home() / ".local" / "state" / "VideoBatchFast",
        }
        lines = []
        for label, path in checks.items():
            ok = is_writable_directory(path)
            lines.append(f"{'✓' if ok else '✕'} {label}: {path}")
        messagebox.showinfo(text("ui.permissions.title"), "\n".join(lines), parent=self.root)

    def _show_about(self) -> None:
        messagebox.showinfo(
            text("ui.about.title"),
            text("ui.about.body", version=build_label()),
            parent=self.root,
        )
