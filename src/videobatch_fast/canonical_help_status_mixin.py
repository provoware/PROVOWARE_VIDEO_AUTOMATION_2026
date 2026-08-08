from __future__ import annotations

from tkinter import StringVar, ttk

from .canonical_shell_contract import responsive_column_count
from .system_metrics import collect_system_metrics, format_bytes


class CanonicalHelpStatusMixin:
    """Intent-based help and a bounded single-line footer."""

    def _build_canonical_help_page(self, parent) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)

        intent = ttk.LabelFrame(
            parent,
            text="Ich möchte …",
            style="Card.TLabelframe",
            padding=(12, 10),
        )
        intent.grid(row=0, column=0, sticky="ew", padx=2, pady=(2, 10))
        self._help_intent_frame = intent

        entries = (
            (
                "Erstes Video erstellen",
                1,
                "Zuerst Audio und Medien hinzufügen. Danach Queue prüfen und Produktion starten.",
            ),
            (
                "Fehlende Datei beheben",
                1,
                "Im Medienbereich nicht erreichbare Verweise prüfen und kontrolliert entfernen oder neu zuordnen.",
            ),
            (
                "Queuefehler wiederholen",
                4,
                "Im Queuebereich den ursprünglichen Fehler lesen und nur wiederanlaufbare Quellen erneut laden.",
            ),
            (
                "Cache leeren",
                5,
                "Unter Hilfe die Vorschau-Cache-Diagnose öffnen. Es werden ausschließlich VideoBatch-Vorschaudateien entfernt.",
            ),
            (
                "Update rückgängig machen",
                5,
                "Den bestätigten A/B-Slot beibehalten oder auf ihn zurückfallen. Projekt- und Originaldateien bleiben unverändert.",
            ),
        )
        self.help_intent_buttons = {}
        for label, page_index, guidance in entries:
            button = ttk.Button(
                intent,
                text=label,
                command=lambda target=page_index, note=guidance: self._open_help_intent(
                    target,
                    note,
                ),
            )
            self.help_intent_buttons[label] = button

        note = ttk.Label(
            intent,
            text=(
                "Jede Auswahl öffnet den passenden Arbeitsbereich und nennt den unmittelbar nächsten sicheren Schritt. "
                "Es wird keine Produktion, Löschung oder Aktualisierung automatisch gestartet."
            ),
            style="Muted.TLabel",
            justify="left",
        )
        self._help_intent_note = note
        intent.bind("<Configure>", self._layout_help_intents, add="+")
        self.root.after_idle(lambda: self._layout_help_intents(width=intent.winfo_width()))

        legacy_help = ttk.Frame(parent, style="Card.TFrame")
        legacy_help.grid(row=1, column=0, sticky="nsew")
        self._build_help_page(legacy_help)

    def _layout_help_intents(self, event=None, *, width: int | None = None) -> None:
        if not hasattr(self, "help_intent_buttons"):
            return
        available = int(width if width is not None else getattr(event, "width", 0))
        buttons = list(self.help_intent_buttons.values())
        requested = max((button.winfo_reqwidth() for button in buttons), default=180) + 12
        columns = responsive_column_count(
            available,
            requested,
            len(buttons),
            minimum_item_width=170,
        )
        frame = self._help_intent_frame
        for column in range(len(buttons)):
            frame.columnconfigure(column, weight=1 if column < columns else 0)
        for index, button in enumerate(buttons):
            button.grid_forget()
            button.grid(
                row=index // columns,
                column=index % columns,
                sticky="ew",
                padx=4,
                pady=4,
            )
        note_row = (len(buttons) + columns - 1) // columns
        self._help_intent_note.grid_forget()
        self._help_intent_note.configure(wraplength=max(240, available - 24))
        self._help_intent_note.grid(
            row=note_row,
            column=0,
            columnspan=columns,
            sticky="ew",
            padx=4,
            pady=(6, 0),
        )

    def _open_help_intent(self, page_index: int, guidance: str) -> None:
        self._select_shell_page(page_index)
        self.guidance_text.set(guidance)
        self.root.after_idle(self.main_notebook.focus_set)

    def _build_canonical_status_bar(self, parent) -> None:
        bar = ttk.Frame(parent, style="Toolbar.TFrame", padding=(9, 4))
        bar.pack(fill="x")
        for column in range(7):
            bar.columnconfigure(column, weight=1 if column in {0, 1, 4} else 0)
        self.shell_footer_guidance = StringVar(value="")
        self.shell_footer_cpu = StringVar(value="CPU …")
        self.shell_footer_ram = StringVar(value="RAM …")
        self.shell_footer_ffmpeg = StringVar(value="FFmpeg …")
        self.shell_footer_cache = StringVar(value="Cache …")
        self.shell_footer_project = StringVar(value="Projekt …")
        self.shell_footer_backup = StringVar(value="Backup …")

        ttk.Label(bar, textvariable=self.shell_footer_cpu, style="ShellHint.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(bar, textvariable=self.shell_footer_ram, style="ShellHint.TLabel").grid(row=0, column=1, sticky="w", padx=(10, 0))
        ttk.Label(bar, textvariable=self.shell_footer_ffmpeg, style="ShellHint.TLabel").grid(row=0, column=2, sticky="w", padx=(10, 0))
        ttk.Label(bar, textvariable=self.shell_footer_cache, style="ShellHint.TLabel").grid(row=0, column=3, sticky="w", padx=(10, 0))
        ttk.Label(bar, textvariable=self.shell_footer_project, style="ShellHint.TLabel").grid(row=0, column=4, sticky="ew", padx=(10, 0))
        ttk.Label(bar, textvariable=self.shell_footer_backup, style="ShellHint.TLabel").grid(row=0, column=5, sticky="w", padx=(10, 0))
        ttk.Label(bar, textvariable=self.status_text, style="Status.TLabel", anchor="e").grid(row=0, column=6, sticky="e", padx=(10, 0))
        self._refresh_footer_metrics()
        self._shell_footer_poll_id = self.root.after(3000, self._poll_footer_metrics)

    def _refresh_footer_metrics(self) -> None:
        if not hasattr(self, "shell_footer_cpu"):
            return
        metrics = collect_system_metrics()
        self.shell_footer_cpu.set("CPU unbekannt" if metrics.cpu_percent is None else f"CPU {metrics.cpu_percent:.0f} %")
        ram = "RAM unbekannt"
        if metrics.ram_used_bytes is not None and metrics.ram_total_bytes is not None:
            ram = f"RAM {format_bytes(metrics.ram_used_bytes)} / {format_bytes(metrics.ram_total_bytes)}"
        self.shell_footer_ram.set(ram)
        self.shell_footer_ffmpeg.set(f"FFmpeg {metrics.ffmpeg} · GPU {metrics.gpu_acceleration}")
        self.shell_footer_cache.set(f"Cache {format_bytes(metrics.cache_bytes)}")
        project = self.project_name.get().strip() if hasattr(self, "project_name") else ""
        self.shell_footer_project.set(f"Projekt {project or 'Neues Projekt'}")
        if hasattr(self, "_project_backup_status"):
            self.shell_footer_backup.set(self._project_backup_status())

    def _poll_footer_metrics(self) -> None:
        try:
            if not self.root.winfo_exists():
                return
            self._refresh_footer_metrics()
            self._shell_footer_poll_id = self.root.after(3000, self._poll_footer_metrics)
        except Exception:
            return
