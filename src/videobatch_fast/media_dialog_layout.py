from __future__ import annotations

from tkinter import ttk


def build_media_actions(dialog, parent) -> None:
    """Build a two-level action area that remains readable at 1220×760."""
    shell = ttk.Frame(parent, padding=(10, 8), style="MediaToolbar.TFrame")
    shell.grid(row=3, column=0, sticky="ew", pady=(10, 0))
    shell.columnconfigure(0, weight=1)

    secondary = ttk.Frame(shell, style="Toolbar.TFrame")
    secondary.grid(row=0, column=0, sticky="ew", pady=(0, 6))
    ttk.Button(secondary, text="Gesammelte Auswahl leeren", command=dialog._clear_collection).pack(side="left")
    ttk.Button(secondary, text="Alle sichtbaren übernehmen", command=dialog._collect_all_visible).pack(side="left", padx=(6, 0))
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
