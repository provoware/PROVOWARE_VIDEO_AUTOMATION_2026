from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from tkinter import StringVar, Toplevel, messagebox, ttk

from .preview_service import clear_preview_cache, preview_cache_status
from .text_resources import text
from .ui_components import Tooltip


def _human_bytes(value: int) -> str:
    size = float(max(0, int(value)))
    for unit in ("B", "KiB", "MiB", "GiB"):
        if size < 1024.0 or unit == "GiB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} GiB"


def show_preview_cache_dialog(parent) -> Toplevel:
    """Show read-only cache facts plus narrowly scoped safe actions."""
    window = Toplevel(parent)
    window.title(text("preview_cache.title"))
    window.geometry("660x430")
    window.minsize(580, 390)
    window.transient(parent)

    values = {name: StringVar(window, value="–") for name in ("files", "size", "limit", "usage", "prune", "path")}
    outer = ttk.Frame(window, padding=16)
    outer.pack(fill="both", expand=True)
    outer.columnconfigure(1, weight=1)

    ttk.Label(outer, text=text("preview_cache.heading"), style="HeaderTitle.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 5))
    ttk.Label(outer, text=text("preview_cache.intro"), wraplength=610, justify="left").grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 14))
    rows = (
        ("preview_cache.files", values["files"]),
        ("preview_cache.size", values["size"]),
        ("preview_cache.limits", values["limit"]),
        ("preview_cache.usage", values["usage"]),
        ("preview_cache.last_prune", values["prune"]),
        ("preview_cache.directory", values["path"]),
    )
    for index, (key, variable) in enumerate(rows, start=2):
        ttk.Label(outer, text=text(key), style="Recommended.TLabel").grid(row=index, column=0, sticky="nw", padx=(0, 14), pady=5)
        ttk.Label(outer, textvariable=variable, justify="left", wraplength=455).grid(row=index, column=1, sticky="ew", pady=5)

    progress = ttk.Progressbar(outer, mode="determinate", maximum=100)
    progress.grid(row=8, column=0, columnspan=2, sticky="ew", pady=(12, 6))
    ttk.Label(outer, text=text("preview_cache.prune_hint"), wraplength=610, justify="left").grid(row=9, column=0, columnspan=2, sticky="ew", pady=(0, 14))

    def refresh() -> None:
        try:
            status = preview_cache_status()
        except OSError as exc:
            messagebox.showerror(text("preview_cache.title"), text("preview_cache.read_error", detail=str(exc)), parent=window)
            return
        values["files"].set(text("preview_cache.files_value", files=status["files"], max_files=status["max_files"]))
        values["size"].set(_human_bytes(int(status["bytes"])))
        values["limit"].set(text("preview_cache.limit_value", bytes=_human_bytes(int(status["max_bytes"])), files=status["max_files"]))
        percent = min(100, max(0, int(status["usage_percent"])))
        values["usage"].set(text("preview_cache.usage_value", percent=percent))
        progress.configure(value=percent)
        values["prune"].set(str(status["last_prune_at"] or text("preview_cache.never_pruned")))
        values["path"].set(str(status["directory"]))

    def clear_cache() -> None:
        if not messagebox.askyesno(text("preview_cache.clear_title"), text("preview_cache.clear_confirmation"), parent=window):
            return
        try:
            result = clear_preview_cache()
        except OSError as exc:
            messagebox.showerror(text("preview_cache.title"), text("preview_cache.clear_error", detail=str(exc)), parent=window)
            return
        refresh()
        note = text("preview_cache.cleared", files=result["removed_files"], bytes=_human_bytes(result["removed_bytes"]))
        if result["skipped_busy"]:
            note += " " + text("preview_cache.busy_protected", files=result["skipped_busy"])
        if result["removed_partials"]:
            note += " " + text("preview_cache.partials_removed", files=result["removed_partials"])
        messagebox.showinfo(text("preview_cache.title"), note, parent=window)

    def open_directory() -> None:
        opener = shutil.which("xdg-open")
        if not opener:
            messagebox.showerror(text("preview_cache.title"), text("preview_cache.opener_missing"), parent=window)
            return
        try:
            directory = Path(str(preview_cache_status()["directory"]))
            subprocess.Popen([opener, str(directory)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError as exc:
            messagebox.showerror(text("preview_cache.title"), text("preview_cache.open_error", detail=str(exc)), parent=window)

    actions = ttk.Frame(outer)
    actions.grid(row=10, column=0, columnspan=2, sticky="ew")
    refresh_button = ttk.Button(actions, text=text("preview_cache.refresh"), command=refresh)
    refresh_button.pack(side="left")
    Tooltip(refresh_button, text("preview_cache.tooltip.refresh"))
    open_button = ttk.Button(actions, text=text("preview_cache.open"), command=open_directory)
    open_button.pack(side="left", padx=(7, 0))
    Tooltip(open_button, text("preview_cache.tooltip.open"))
    clear_button = ttk.Button(actions, text=text("preview_cache.clear"), style="Danger.TButton", command=clear_cache)
    clear_button.pack(side="left", padx=(7, 0))
    Tooltip(clear_button, text("preview_cache.tooltip.clear"))
    close_button = ttk.Button(actions, text=text("preview_cache.close"), command=window.destroy)
    close_button.pack(side="right")
    Tooltip(close_button, text("preview_cache.tooltip.close"))

    refresh()
    return window


def build_media_actions(dialog, parent) -> None:
    """Build a two-level action area that remains readable at 1220×760."""
    shell = ttk.Frame(parent, padding=(10, 8), style="MediaToolbar.TFrame")
    shell.grid(row=3, column=0, sticky="ew", pady=(10, 0))
    shell.columnconfigure(0, weight=1)

    secondary = ttk.Frame(shell, style="Toolbar.TFrame")
    secondary.grid(row=0, column=0, sticky="ew", pady=(0, 6))
    clear_button = ttk.Button(secondary, text=text("media_collection.clear"), command=dialog._clear_collection)
    clear_button.pack(side="left")
    Tooltip(clear_button, text("media_collection.tooltip.clear"))
    visible_button = ttk.Button(secondary, text=text("media_collection.collect_visible"), command=dialog._collect_all_visible)
    visible_button.pack(side="left", padx=(6, 0))
    Tooltip(visible_button, text("media_collection.tooltip.collect_visible"))
    if not dialog.audio:
        cache_button = ttk.Button(secondary, text=text("preview_cache.button"), command=lambda: show_preview_cache_dialog(dialog.window))
        cache_button.pack(side="left", padx=(6, 0))
        Tooltip(cache_button, text("preview_cache.tooltip.button"))
    ttk.Label(secondary, textvariable=dialog.collection_value, style="HeaderHint.TLabel").pack(side="right")

    primary = ttk.Frame(shell, style="Toolbar.TFrame")
    primary.grid(row=1, column=0, sticky="ew")
    primary.columnconfigure(0, weight=1)
    continue_button = ttk.Button(primary, text=dialog.KEEP_OPEN_LABEL, style="Success.TButton", command=dialog._collect_and_continue)
    continue_button.grid(row=0, column=0, sticky="ew", padx=(0, 7))
    Tooltip(continue_button, text("media_collection.tooltip.continue"))
    final_key = "media_collection.finish_audio" if dialog.audio else "media_collection.finish_media"
    finish_button = ttk.Button(primary, text=text(final_key), style="Accent.TButton", command=dialog._accept)
    finish_button.grid(row=0, column=1, padx=(0, 7))
    Tooltip(finish_button, text("media_collection.tooltip.finish"))
    cancel_button = ttk.Button(primary, text=text("media_collection.cancel"), command=dialog._cancel)
    cancel_button.grid(row=0, column=2)
    Tooltip(cancel_button, text("media_collection.tooltip.cancel"))
