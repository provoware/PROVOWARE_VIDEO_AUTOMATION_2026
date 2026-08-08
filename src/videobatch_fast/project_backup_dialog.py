from __future__ import annotations

from pathlib import Path
from tkinter import END, StringVar, Toplevel, filedialog, messagebox, ttk

from .project_backup import (
    ProjectBackupError,
    ProjectBackupRecord,
    create_project_backup,
    list_project_backups,
    restore_project_backup,
    verify_project_backup,
)


class ProjectBackupDialog:
    """Small local backup browser. Never overwrites the active project implicitly."""

    def __init__(self, parent, project_file: Path, on_changed=None) -> None:
        self.parent = parent
        self.project_file = Path(project_file)
        self.on_changed = on_changed
        self.records: list[ProjectBackupRecord] = []
        self.status = StringVar(value="Sicherungen werden geprüft …")
        self.window = Toplevel(parent)
        self.window.title("Projektsicherungen")
        self.window.transient(parent)
        self.window.geometry("760x480")
        self.window.minsize(620, 380)
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(1, weight=1)
        self._build()
        self.refresh()

    def _build(self) -> None:
        top = ttk.Frame(self.window, padding=(12, 10))
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(0, weight=1)
        ttk.Label(top, text="Projektsicherungen", style="SectionHeader.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Button(top, text="Jetzt sichern", command=self.create).grid(row=0, column=1, padx=(8, 0))

        body = ttk.Frame(self.window, padding=(12, 0, 12, 8))
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(body, columns=("time", "size", "file"), show="headings", selectmode="browse")
        self.tree.heading("time", text="Zeit")
        self.tree.heading("size", text="Größe")
        self.tree.heading("file", text="Sicherungsdatei")
        self.tree.column("time", width=160, stretch=False)
        self.tree.column("size", width=90, stretch=False, anchor="e")
        self.tree.column("file", width=420)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(body, orient="vertical", command=self.tree.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scroll.set)

        actions = ttk.Frame(self.window, padding=(12, 6, 12, 12))
        actions.grid(row=2, column=0, sticky="ew")
        actions.columnconfigure(0, weight=1)
        ttk.Label(actions, textvariable=self.status, style="Hint.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Button(actions, text="Prüfen", command=self.verify_selected).grid(row=0, column=1, padx=(6, 0))
        ttk.Button(actions, text="Als Kopie wiederherstellen", command=self.restore_copy).grid(row=0, column=2, padx=(6, 0))
        ttk.Button(actions, text="Schließen", command=self.window.destroy).grid(row=0, column=3, padx=(6, 0))

    def _selected(self) -> ProjectBackupRecord | None:
        selected = self.tree.selection()
        if not selected:
            self.status.set("Bitte zuerst eine Sicherung auswählen.")
            return None
        try:
            index = int(selected[0])
            return self.records[index]
        except (ValueError, IndexError):
            self.status.set("Die Auswahl ist nicht mehr gültig. Bitte Liste aktualisieren.")
            return None

    def refresh(self) -> None:
        self.records = list_project_backups()
        self.tree.delete(*self.tree.get_children())
        for index, record in enumerate(self.records):
            stamp = record.created_at.replace("T", " ").replace("+00:00", " UTC")[:20]
            size = f"{record.size_bytes / 1024:.1f} KiB"
            self.tree.insert("", END, iid=str(index), values=(stamp, size, record.path.name))
        self.status.set(f"{len(self.records)} verifizierte Sicherung(en). Medien sind nicht Bestandteil dieser Projektsicherung.")

    def create(self) -> None:
        try:
            record = create_project_backup(self.project_file)
        except ProjectBackupError as exc:
            messagebox.showerror("Projektsicherung", str(exc), parent=self.window)
            return
        self.refresh()
        self.status.set(f"Gesichert: {record.path.name}")
        if callable(self.on_changed):
            self.on_changed()

    def verify_selected(self) -> None:
        record = self._selected()
        if record is None:
            return
        try:
            manifest = verify_project_backup(record.path)
        except ProjectBackupError as exc:
            messagebox.showerror("Sicherung beschädigt", str(exc), parent=self.window)
            self.refresh()
            return
        self.status.set(f"Verifiziert · SHA-256 {str(manifest['source_sha256'])[:12]}…")

    def restore_copy(self) -> None:
        record = self._selected()
        if record is None:
            return
        initial = self.project_file.with_name(f"{self.project_file.stem}_wiederhergestellt{self.project_file.suffix}")
        selected = filedialog.asksaveasfilename(
            parent=self.window,
            title="Sicherung als Projektkopie wiederherstellen",
            initialdir=str(initial.parent),
            initialfile=initial.name,
            defaultextension=".json",
            filetypes=[("VideoBatch-Projekt", "*.vbfast.json"), ("JSON", "*.json")],
        )
        if not selected:
            return
        target = Path(selected)
        if target.resolve() == self.project_file.expanduser().resolve():
            messagebox.showwarning(
                "Aktives Projekt geschützt",
                "Die aktive Projektdatei wird aus dem Sicherungsdialog nicht überschrieben. Bitte einen neuen Dateinamen wählen.",
                parent=self.window,
            )
            return
        try:
            restored = restore_project_backup(record.path, target, overwrite=False)
        except ProjectBackupError as exc:
            messagebox.showerror("Wiederherstellung fehlgeschlagen", str(exc), parent=self.window)
            return
        self.status.set(f"Wiederhergestellt als Kopie: {restored.name}")
