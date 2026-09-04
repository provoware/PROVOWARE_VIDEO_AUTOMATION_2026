from __future__ import annotations

from tkinter import StringVar, ttk

from .canonical_shell_contract import responsive_column_count


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
        bar = ttk.Frame(parent, style="Toolbar.TFrame", padding=(10, 5))
        bar.pack(fill="x")
        bar.columnconfigure(0, weight=1)
        self.shell_footer_guidance = StringVar(value="")

        def sync_guidance(*_args) -> None:
            value = self.guidance_text.get().replace("\n", " ").strip()
            self.shell_footer_guidance.set(
                value if len(value) <= 180 else value[:177] + "…"
            )

        self.guidance_text.trace_add("write", sync_guidance)
        sync_guidance()
        ttk.Label(
            bar,
            textvariable=self.shell_footer_guidance,
            style="ShellHint.TLabel",
            width=1,
            anchor="w",
        ).grid(row=0, column=0, sticky="ew")
        ttk.Label(
            bar,
            textvariable=self.status_text,
            style="Status.TLabel",
            anchor="e",
        ).grid(row=0, column=1, sticky="e", padx=(10, 0))
