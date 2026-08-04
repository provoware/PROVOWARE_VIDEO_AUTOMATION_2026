from __future__ import annotations

import subprocess
from pathlib import Path
from tkinter import StringVar, Toplevel, messagebox, ttk

from .preview_service import clear_preview_cache, preview_cache_status


def _human_bytes(value: int) -> str:
    size = float(max(0, int(value)))
    for unit in ("B", "KiB", "MiB", "GiB"):
        if size < 1024.0 or unit == "GiB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} GiB"


def show_preview_cache_dialog(parent) -> Toplevel:
    """Show cache status and safe controls without changing the preview architecture."""
    window = Toplevel(parent)
    window.title("Vorschau-Cache")
    window.geometry("660x430")
    window.minsize(580, 390)
    window.transient(parent)

    files_value = StringVar(window, value="–")
    size_value = StringVar(window, value="–")
    limit_value = StringVar(window, value="–")
    usage_value = StringVar(window, value="–")
    prune_value = StringVar(window, value="–")
    path_value = StringVar(window, value="–")

    outer = ttk.Frame(window, padding=16)
    outer.pack(fill="both", expand=True)
    outer.columnconfigure(1, weight=1)

    ttk.Label(outer, text="Thumbnail-Datenträgercache", style="HeaderTitle.TLabel").grid(
        row=0, column=0, columnspan=2, sticky="w", pady=(0, 5)
    )
    ttk.Label(
        outer,
        text=(
            "Hier liegen ausschließlich automatisch erzeugte Vorschaubilder. "
            "Originalmedien und Projektdateien werden weder angezeigt noch gelöscht."
        ),
        wraplength=610,
        justify="left",
    ).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 14))

    rows = (
        ("Vorschaubilder", files_value),
        ("Belegter Speicher", size_value),
        ("Grenzen", limit_value),
        ("Auslastung", usage_value),
        ("Letzte Bereinigung", prune_value),
        ("Cacheordner", path_value),
    )
    for index, (label, variable) in enumerate(rows, start=2):
        ttk.Label(outer, text=label, style="Recommended.TLabel").grid(
            row=index, column=0, sticky="nw", padx=(0, 14), pady=5
        )
        ttk.Label(
            outer,
            textvariable=variable,
            justify="left",
            wraplength=455,
        ).grid(row=index, column=1, sticky="ew", pady=5)

    progress = ttk.Progressbar(outer, mode="determinate", maximum=100)
    progress.grid(row=8, column=0, columnspan=2, sticky="ew", pady=(12, 6))
    ttk.Label(
        outer,
        text=(
            "Die automatische LRU-Bereinigung entfernt bei Bedarf zuerst die am längsten "
            "nicht verwendeten VideoBatch-Vorschaubilder."
        ),
        wraplength=610,
        justify="left",
    ).grid(row=9, column=0, columnspan=2, sticky="ew", pady=(0, 14))

    def refresh() -> None:
        try:
            status = preview_cache_status()
        except OSError as exc:
            messagebox.showerror(
                "Vorschau-Cache",
                f"Der Cache-Status konnte nicht gelesen werden:\n{exc}",
                parent=window,
            )
            return
        files_value.set(f"{status['files']} von maximal {status['max_files']}")
        size_value.set(_human_bytes(int(status["bytes"])))
        limit_value.set(
            f"{_human_bytes(int(status['max_bytes']))} · {status['max_files']} Dateien"
        )
        percent = min(100, max(0, int(status["usage_percent"])))
        usage_value.set(f"{percent} % der Speichergrenze")
        progress.configure(value=percent)
        prune_value.set(str(status["last_prune_at"] or "Noch keine Bereinigung protokolliert"))
        path_value.set(str(status["directory"]))

    def clear_cache() -> None:
        confirmed = messagebox.askyesno(
            "Vorschau-Cache leeren",
            (
                "Nur automatisch erzeugte VideoBatch-Vorschaubilder werden entfernt.\n\n"
                "Originalmedien, Projekte und fremde Dateien bleiben unverändert. Fortfahren?"
            ),
            parent=window,
        )
        if not confirmed:
            return
        try:
            result = clear_preview_cache()
        except OSError as exc:
            messagebox.showerror(
                "Vorschau-Cache",
                f"Der Cache konnte nicht vollständig geleert werden:\n{exc}",
                parent=window,
            )
            return
        refresh()
        note = (
            f"{result['removed_files']} Vorschaubilder mit "
            f"{_human_bytes(result['removed_bytes'])} wurden entfernt."
        )
        if result["skipped_busy"]:
            note += f" {result['skipped_busy']} aktuell verwendete Datei(en) wurden geschützt."
        if result["removed_partials"]:
            note += f" {result['removed_partials']} veraltete Teildatei(en) wurden bereinigt."
        messagebox.showinfo("Vorschau-Cache", note, parent=window)

    def open_directory() -> None:
        try:
            directory = Path(str(preview_cache_status()["directory"]))
            subprocess.Popen(
                ["xdg-open", str(directory)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as exc:
            messagebox.showerror(
                "Vorschau-Cache",
                f"Der Cacheordner konnte nicht geöffnet werden:\n{exc}",
                parent=window,
            )

    actions = ttk.Frame(outer)
    actions.grid(row=10, column=0, columnspan=2, sticky="ew")
    ttk.Button(actions, text="Status aktualisieren", command=refresh).pack(side="left")
    ttk.Button(actions, text="Cacheordner öffnen", command=open_directory).pack(
        side="left", padx=(7, 0)
    )
    ttk.Button(
        actions,
        text="Vorschau-Cache leeren",
        style="Danger.TButton",
        command=clear_cache,
    ).pack(side="left", padx=(7, 0))
    ttk.Button(actions, text="Schließen", command=window.destroy).pack(side="right")

    refresh()
    return window


def build_media_actions(dialog, parent) -> None:
    """Build a two-level action area that remains readable at 1220×760."""
    shell = ttk.Frame(parent, padding=(10, 8), style="MediaToolbar.TFrame")
    shell.grid(row=3, column=0, sticky="ew", pady=(10, 0))
    shell.columnconfigure(0, weight=1)

    secondary = ttk.Frame(shell, style="Toolbar.TFrame")
    secondary.grid(row=0, column=0, sticky="ew", pady=(0, 6))
    ttk.Button(secondary, text="Gesammelte Auswahl leeren", command=dialog._clear_collection).pack(side="left")
    ttk.Button(secondary, text="Alle sichtbaren übernehmen", command=dialog._collect_all_visible).pack(side="left", padx=(6, 0))
    if not dialog.audio:
        ttk.Button(
            secondary,
            text="Vorschau-Cache",
            command=lambda: show_preview_cache_dialog(dialog.window),
        ).pack(side="left", padx=(6, 0))
    ttk.Label(secondary, textvariable=dialog.collection_value, style="HeaderHint.TLabel").pack(side="right")

    primary = ttk.Frame(shell, style="Toolbar.TFrame")
    primary.grid(row=1, column=0, sticky="ew")
    primary.columnconfigure(0, weight=1)
    ttk.Button(
        primary,
        text=dialog.KEEP_OPEN_LABEL,
        style="Success.TButton",
        command=dialog._collect_and_continue,
    ).grid(row=0, column=0, sticky="ew", padx=(0, 7))
    final_label = "Fertig · Audios übernehmen" if dialog.audio else "Fertig · Medien übernehmen"
    ttk.Button(primary, text=final_label, style="Accent.TButton", command=dialog._accept).grid(row=0, column=1, padx=(0, 7))
    ttk.Button(primary, text="Abbrechen", command=dialog._cancel).grid(row=0, column=2)
