from __future__ import annotations

from pathlib import Path

from .project_backup import ProjectBackupError, create_project_backup, latest_project_backup
from .project_backup_dialog import ProjectBackupDialog


class CanonicalBackupMixin:
    """Expose a small, honest project-state backup action to the canonical shell."""


    def _open_backup_manager(self) -> None:
        if hasattr(self, "_autosave_project"):
            self._autosave_project(force=True)
        project_file = Path(getattr(self, "project_file", ""))
        if not project_file.is_file():
            self.guidance_text.set("Die aktuelle Projektdatei ist nicht erreichbar; Sicherungsmanager wurde nicht geöffnet.")
            return
        ProjectBackupDialog(
            self.root,
            project_file,
            on_changed=getattr(self, "_refresh_footer_metrics", None),
        )

    def _create_shell_backup(self) -> None:
        if hasattr(self, "_autosave_project"):
            self._autosave_project(force=True)
        project_file = Path(getattr(self, "project_file", ""))
        try:
            record = create_project_backup(project_file)
        except ProjectBackupError as exc:
            self.guidance_text.set(str(exc))
            return
        self.guidance_text.set(
            f"Projektzustand gesichert: {record.path.name}. Medien wurden nicht dupliziert."
        )
        if hasattr(self, "_refresh_footer_metrics"):
            self._refresh_footer_metrics()

    def _project_backup_status(self) -> str:
        record = latest_project_backup()
        if record is None:
            return "Backup noch keines"
        stamp = record.created_at.replace("T", " ").replace("+00:00", " UTC")
        return f"Backup {stamp[:16]}"
