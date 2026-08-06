from __future__ import annotations

from pathlib import Path
from tkinter import Canvas, StringVar, TclError, ttk

from .canonical_shell_contract import (
    CANONICAL_THEME_LABELS,
    DASHBOARD_COLUMN_WEIGHTS,
    DASHBOARD_STACKED_MAX,
    DASHBOARD_TWO_COLUMN_MAX,
    FONT_PROFILES,
    SHELL_NAVIGATION,
    SIDEBAR_WIDTH,
)
from .theme import COLORS


class CanonicalShellWorkspaceMixin:
    def _build_ui(self) -> None:
        self.workflow_grids = {}
        self._build_menu_bar()
        self._configure_shell_styles()
        shell = ttk.Frame(self.root, style="Shell.TFrame")
        shell.pack(fill="both", expand=True)
        shell.columnconfigure(1, weight=1)
        shell.rowconfigure(0, weight=1)

        sidebar = ttk.Frame(
            shell,
            style="ShellSidebar.TFrame",
            padding=(13, 15),
            width=SIDEBAR_WIDTH,
        )
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)

        content = ttk.Frame(shell, style="Shell.TFrame", padding=(15, 11, 15, 7))
        content.grid(row=0, column=1, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(3, weight=1)

        self._build_shell_sidebar(sidebar)
        self._build_shell_header(content)
        self._build_shell_kpis(content)
        self._build_shell_actions(content)
        self._build_shell_workspace(content)

        footer_host = ttk.Frame(shell, style="Shell.TFrame")
        footer_host.grid(row=1, column=0, columnspan=2, sticky="ew")
        self._build_canonical_status_bar(footer_host)
        self._restore_shell_selection()

    def _build_shell_workspace(self, parent) -> None:
        workspace = ttk.Frame(parent, style="Shell.TFrame")
        workspace.grid(row=3, column=0, sticky="nsew")
        workspace.rowconfigure(0, weight=1)
        workspace.columnconfigure(0, weight=1)

        self.main_notebook = ttk.Notebook(workspace, style="Shell.TNotebook")
        self.main_notebook.grid(row=0, column=0, sticky="nsew")
        self.main_notebook.bind("<<NotebookTabChanged>>", self._on_main_tab_changed, add="+")
        self.main_notebook.bind("<<NotebookTabChanged>>", self._on_shell_tab_changed, add="+")

        pages = [ttk.Frame(self.main_notebook, style="Card.TFrame", padding=6) for _ in range(6)]
        for page, label in zip(pages, ("Dashboard", "Medien", "Vorschau", "Effekte", "Queue", "Hilfe")):
            self.main_notebook.add(page, text=label)

        self._build_dashboard_page(pages[0])
        self._build_media_page(pages[1])
        self._build_preview_page(pages[2])
        self._build_modes_page(pages[3])
        self._build_production_page(pages[4])
        self._build_canonical_help_page(pages[5])

    def _build_dashboard_page(self, parent) -> None:
        """Keep the canonical overview and the complete legacy start assistant reachable."""
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        overview = ttk.Frame(parent, style="Shell.TFrame")
        assistant = ttk.Frame(parent, style="Card.TFrame")
        overview.grid(row=0, column=0, sticky="nsew")
        assistant.grid(row=0, column=0, sticky="nsew")
        self._dashboard_views = {"overview": overview, "assistant": assistant}

        self._build_canonical_dashboard_page(overview)

        assistant.columnconfigure(0, weight=1)
        assistant.rowconfigure(1, weight=1)
        assistant_bar = ttk.Frame(assistant, style="ShellHeader.TFrame", padding=(10, 7))
        assistant_bar.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        ttk.Label(assistant_bar, text="Geführter Startassistent", style="HeaderTitle.TLabel").pack(side="left")
        ttk.Button(
            assistant_bar,
            text="← Zur Dashboard-Übersicht",
            style="Ghost.TButton",
            command=lambda: self._show_dashboard_view("overview"),
        ).pack(side="right")
        assistant_body = ttk.Frame(assistant, style="Card.TFrame", padding=4)
        assistant_body.grid(row=1, column=0, sticky="nsew")
        self._build_start_page(assistant_body)
        assistant.grid_remove()

    def _show_dashboard_view(self, name: str) -> None:
        selected = self._dashboard_views.get(name)
        if selected is None:
            return
        for view in self._dashboard_views.values():
            view.grid_remove()
        selected.grid()
        selected.tkraise()
        if name == "overview":
            self._refresh_canonical_dashboard()

    def _build_canonical_dashboard_page(self, parent) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        canvas = Canvas(
            parent,
            background=COLORS["bg"],
            highlightthickness=0,
            borderwidth=0,
        )
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        surface = ttk.Frame(canvas, style="Shell.TFrame", padding=(2, 2, 5, 12))
        window_id = canvas.create_window((0, 0), window=surface, anchor="nw")
        self._dashboard_canvas = canvas
        self._dashboard_surface = surface
        self._dashboard_window_id = window_id
        self._dashboard_layout_mode = ""

        surface.bind(
            "<Configure>",
            lambda _event: canvas.configure(scrollregion=canvas.bbox("all")),
            add="+",
        )
        canvas.bind("<Configure>", self._on_dashboard_canvas_configure, add="+")
        canvas.bind("<MouseWheel>", self._scroll_dashboard, add="+")
        canvas.bind("<Button-4>", lambda _event: canvas.yview_scroll(-3, "units"), add="+")
        canvas.bind("<Button-5>", lambda _event: canvas.yview_scroll(3, "units"), add="+")

        self._dashboard_sources_card = self._build_dashboard_sources_card(surface)
        self._dashboard_queue_card = self._build_dashboard_queue_card(surface)
        self._dashboard_details_card = self._build_dashboard_details_card(surface)
        self._dashboard_scheduler_card = self._build_dashboard_scheduler_card(surface)
        self._dashboard_appearance_card = self._build_dashboard_appearance_card(surface)

        self.root.after_idle(
            lambda: self._layout_canonical_dashboard(max(1, canvas.winfo_width()))
        )
        self._refresh_canonical_dashboard()

    def _build_dashboard_sources_card(self, parent):
        card = ttk.Frame(parent, style="ShellCard.TFrame", padding=(14, 12))
        ttk.Label(card, text="Quellen & Projekt", style="SectionHeader.TLabel").pack(anchor="w")
        self._dashboard_source_summary = StringVar(value="Noch keine Medien ausgewählt")
        self._dashboard_project_summary = StringVar(value="Projekt wird geladen")
        self._dashboard_output_summary = StringVar(value="Ausgabeziel wird geprüft")

        source_label = ttk.Label(
            card,
            textvariable=self._dashboard_source_summary,
            style="Hint.TLabel",
            justify="left",
        )
        source_label.pack(anchor="w", fill="x", pady=(8, 3))
        project_label = ttk.Label(
            card,
            textvariable=self._dashboard_project_summary,
            style="Hint.TLabel",
            justify="left",
        )
        project_label.pack(anchor="w", fill="x", pady=3)
        output_label = ttk.Label(
            card,
            textvariable=self._dashboard_output_summary,
            style="Hint.TLabel",
            justify="left",
        )
        output_label.pack(anchor="w", fill="x", pady=3)
        self._dashboard_wrapped_labels = [source_label, project_label, output_label]

        actions = ttk.Frame(card, style="ShellCard.TFrame")
        actions.pack(fill="x", pady=(10, 0))
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)
        ttk.Button(actions, text="♫ Audio", command=self._add_audio).grid(
            row=0, column=0, sticky="ew", padx=(0, 3), pady=3
        )
        ttk.Button(actions, text="▧ Bilder / Videos", command=self._add_media).grid(
            row=0, column=1, sticky="ew", padx=(3, 0), pady=3
        )
        ttk.Button(
            actions,
            text="Geführten Start öffnen",
            style="Accent.TButton",
            command=lambda: self._show_dashboard_view("assistant"),
        ).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(5, 0))
        card.bind("<Configure>", self._update_dashboard_wraplengths, add="+")
        return card

    def _build_dashboard_queue_card(self, parent):
        card = ttk.Frame(parent, style="ShellCard.TFrame", padding=(14, 12))
        card.columnconfigure(0, weight=1)
        card.rowconfigure(2, weight=1)

        top = ttk.Frame(card, style="ShellCard.TFrame")
        top.grid(row=0, column=0, sticky="ew")
        ttk.Label(top, text="Render Queue", style="SectionHeader.TLabel").pack(side="left")
        self._dashboard_queue_summary = StringVar(value="Keine Aufträge")
        ttk.Label(top, textvariable=self._dashboard_queue_summary, style="Hint.TLabel").pack(side="right")

        ttk.Label(
            card,
            text="Reale Aufträge aus dem aktuellen Projekt; keine Musterwerte.",
            style="Hint.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(3, 7))

        tree = ttk.Treeview(
            card,
            columns=("job", "effect", "status", "progress"),
            show="headings",
            height=7,
        )
        tree.heading("job", text="Job")
        tree.heading("effect", text="Effekt / Modus")
        tree.heading("status", text="Status")
        tree.heading("progress", text="Fortschritt")
        tree.column("job", width=220, minwidth=130, stretch=True)
        tree.column("effect", width=150, minwidth=100, stretch=True)
        tree.column("status", width=105, minwidth=85, stretch=False)
        tree.column("progress", width=85, minwidth=70, stretch=False, anchor="e")
        tree.grid(row=2, column=0, sticky="nsew")
        self._dashboard_queue_tree = tree

        actions = ttk.Frame(card, style="ShellCard.TFrame")
        actions.grid(row=3, column=0, sticky="ew", pady=(9, 0))
        for column in range(3):
            actions.columnconfigure(column, weight=1)
        ttk.Button(actions, text="Queue öffnen", command=lambda: self._select_shell_page(4)).grid(
            row=0, column=0, sticky="ew", padx=(0, 3)
        )
        ttk.Button(actions, text="▶ Start", style="Success.TButton", command=self._start).grid(
            row=0, column=1, sticky="ew", padx=3
        )
        ttk.Button(actions, text="Abbrechen", style="Danger.TButton", command=self._cancel).grid(
            row=0, column=2, sticky="ew", padx=(3, 0)
        )
        return card

    def _build_dashboard_details_card(self, parent):
        card = ttk.Frame(parent, style="ShellCard.TFrame", padding=(14, 12))
        card.columnconfigure(0, weight=1)
        ttk.Label(card, text="Jobdetails & Vorschau", style="SectionHeader.TLabel").grid(
            row=0, column=0, sticky="w"
        )

        preview = Canvas(
            card,
            height=164,
            background=COLORS["preview"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
            borderwidth=0,
        )
        preview.grid(row=1, column=0, sticky="ew", pady=(8, 9))
        preview.bind("<Configure>", lambda _event: self._refresh_dashboard_preview(), add="+")
        self._dashboard_preview_canvas = preview

        self._dashboard_detail_summary = StringVar(value="Noch kein Auftrag ausgewählt")
        detail_label = ttk.Label(
            card,
            textvariable=self._dashboard_detail_summary,
            style="Hint.TLabel",
            justify="left",
        )
        detail_label.grid(row=2, column=0, sticky="ew")
        self._dashboard_wrapped_labels.append(detail_label)

        proof = ttk.Frame(card, style="ShellCard.TFrame", padding=(0, 9, 0, 0))
        proof.grid(row=3, column=0, sticky="ew")
        self._dashboard_renderproof = StringVar(value="RenderProof – nicht bestätigt")
        self._dashboard_renderproof_label = ttk.Label(
            proof,
            textvariable=self._dashboard_renderproof,
            style="Warning.TLabel",
        )
        self._dashboard_renderproof_label.pack(anchor="w")
        ttk.Button(
            card,
            text="Vorschau öffnen",
            command=lambda: self._select_shell_page(2),
        ).grid(row=4, column=0, sticky="ew", pady=(10, 0))
        card.bind("<Configure>", self._update_dashboard_wraplengths, add="+")
        return card

    def _build_dashboard_scheduler_card(self, parent):
        card = ttk.Frame(parent, style="ShellCard.TFrame", padding=(14, 12))
        ttk.Label(card, text="Startzeituhr", style="SectionHeader.TLabel").pack(anchor="w")
        self._dashboard_scheduler_summary = StringVar(
            value="Deaktiviert bis Checkpoint 5 · kein automatischer Start"
        )
        ttk.Label(
            card,
            textvariable=self._dashboard_scheduler_summary,
            style="Hint.TLabel",
            justify="left",
            wraplength=720,
        ).pack(anchor="w", fill="x", pady=(7, 8))
        ttk.Button(
            card,
            text="◷ Startzeituhr · Checkpoint 5",
            state="disabled",
        ).pack(fill="x")
        return card

    def _build_dashboard_appearance_card(self, parent):
        card = ttk.Frame(parent, style="ShellCard.TFrame", padding=(14, 12))
        card.columnconfigure(0, weight=1)
        ttk.Label(card, text="Darstellung", style="SectionHeader.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            card,
            text="Theme und Schrift wirken sofort und werden gespeichert.",
            style="Hint.TLabel",
            wraplength=360,
        ).grid(row=1, column=0, sticky="w", pady=(3, 8))

        theme_reverse = {label: key for key, label in CANONICAL_THEME_LABELS.items()}
        self.shell_theme_combo = ttk.Combobox(
            card,
            values=list(theme_reverse),
            state="readonly",
        )
        self.shell_theme_combo.set(
            CANONICAL_THEME_LABELS.get(self.theme_name.get(), "Midnight Blue")
        )
        self.shell_theme_combo.grid(row=2, column=0, sticky="ew", pady=(0, 7))
        self.shell_theme_combo.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._set_canonical_theme(
                theme_reverse[self.shell_theme_combo.get()]
            ),
        )

        self.shell_font_combo = ttk.Combobox(
            card,
            values=list(FONT_PROFILES),
            state="readonly",
        )
        self.shell_font_combo.set(self._font_profile_for_scale(self.global_font_scale.get()))
        self.shell_font_combo.grid(row=3, column=0, sticky="ew")
        self.shell_font_combo.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._set_global_zoom(
                FONT_PROFILES[self.shell_font_combo.get()]
            ),
        )
        return card

    def _on_dashboard_canvas_configure(self, event) -> None:
        width = max(1, int(event.width))
        self._dashboard_canvas.itemconfigure(self._dashboard_window_id, width=width)
        self._layout_canonical_dashboard(width)

    def _scroll_dashboard(self, event) -> None:
        delta = int(getattr(event, "delta", 0))
        if delta:
            self._dashboard_canvas.yview_scroll(-1 if delta > 0 else 1, "units")

    def _layout_canonical_dashboard(self, width: int) -> None:
        if not hasattr(self, "_dashboard_surface"):
            return
        if width <= DASHBOARD_STACKED_MAX:
            mode = "stacked"
        elif width <= DASHBOARD_TWO_COLUMN_MAX:
            mode = "two_columns"
        else:
            mode = "three_columns"

        cards = (
            self._dashboard_sources_card,
            self._dashboard_queue_card,
            self._dashboard_details_card,
            self._dashboard_scheduler_card,
            self._dashboard_appearance_card,
        )
        for card in cards:
            card.grid_forget()
        for column in range(3):
            self._dashboard_surface.columnconfigure(column, weight=0, minsize=0)

        if mode == "three_columns":
            for column, weight in enumerate(DASHBOARD_COLUMN_WEIGHTS):
                self._dashboard_surface.columnconfigure(column, weight=weight)
            self._dashboard_sources_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=(0, 7))
            self._dashboard_queue_card.grid(row=0, column=1, sticky="nsew", padx=6, pady=(0, 7))
            self._dashboard_details_card.grid(row=0, column=2, sticky="nsew", padx=(6, 0), pady=(0, 7))
            self._dashboard_scheduler_card.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=(0, 6))
            self._dashboard_appearance_card.grid(row=1, column=2, sticky="nsew", padx=(6, 0))
        elif mode == "two_columns":
            self._dashboard_surface.columnconfigure(0, weight=35)
            self._dashboard_surface.columnconfigure(1, weight=65)
            self._dashboard_sources_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=(0, 7))
            self._dashboard_queue_card.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=(0, 7))
            self._dashboard_details_card.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=7)
            self._dashboard_scheduler_card.grid(row=2, column=0, sticky="nsew", padx=(0, 6), pady=(7, 0))
            self._dashboard_appearance_card.grid(row=2, column=1, sticky="nsew", padx=(6, 0), pady=(7, 0))
        else:
            self._dashboard_surface.columnconfigure(0, weight=1)
            for row, card in enumerate(cards):
                card.grid(row=row, column=0, sticky="nsew", pady=(0 if row == 0 else 7, 0))

        self._dashboard_layout_mode = mode
        self._update_dashboard_wraplengths()
        self.root.after_idle(
            lambda: self._dashboard_canvas.configure(
                scrollregion=self._dashboard_canvas.bbox("all")
            )
        )

    def _update_dashboard_wraplengths(self, _event=None) -> None:
        if not hasattr(self, "_dashboard_wrapped_labels"):
            return
        for label in self._dashboard_wrapped_labels:
            try:
                width = max(160, label.master.winfo_width() - 30)
                label.configure(wraplength=width)
            except TclError:
                return

    def _refresh_canonical_dashboard(self) -> None:
        if not hasattr(self, "_dashboard_source_summary"):
            return
        audios = tuple(getattr(self, "audios", ()))
        media = tuple(getattr(self, "media", ()))
        jobs = tuple(getattr(self, "jobs", ()))
        results = tuple(getattr(self, "last_results", ()))
        missing = sum(1 for path in (*audios, *media) if not path.is_file())

        self._dashboard_source_summary.set(
            f"Audio: {len(audios)} · Bilder/Videos: {len(media)} · Fehlend: {missing}"
        )
        project_name = self.project_name.get().strip() if hasattr(self, "project_name") else "Neues Projekt"
        self._dashboard_project_summary.set(f"Projekt: {project_name or 'Neues Projekt'}")
        output_value = self.output_dir.get().strip() if hasattr(self, "output_dir") else ""
        self._dashboard_output_summary.set(
            f"Ausgabe: {output_value or 'Noch nicht gewählt'}"
        )

        finished = sum(1 for result in results if bool(getattr(result, "success", False)))
        failed = sum(1 for result in results if not bool(getattr(result, "success", False)))
        self._dashboard_queue_summary.set(
            f"{len(jobs)} Aufträge · {finished} fertig · {failed} fehlerhaft"
        )
        self._refresh_dashboard_queue(jobs, results)

        effect = self.visual_effect.get() if hasattr(self, "visual_effect") else "none"
        quick_mode = self.quick_mode.get() if hasattr(self, "quick_mode") else "custom"
        resolution = self.resolution.get() if hasattr(self, "resolution") else "Original"
        codec = self.codec.get() if hasattr(self, "codec") else "libx264"
        preview_meta = self.preview_meta.get() if hasattr(self, "preview_meta") else "Noch keine Vorschau"
        self._dashboard_detail_summary.set(
            f"Vorschau: {preview_meta}\nEffekt: {effect} · Modus: {quick_mode}\n"
            f"Ausgabe: {resolution} · {codec}"
        )

        if results and failed == 0:
            self._dashboard_renderproof.set("RenderProof – Bestanden")
            self._dashboard_renderproof_label.configure(style="Success.TLabel")
        elif failed:
            self._dashboard_renderproof.set("RenderProof – nicht bestätigt · Fehler vorhanden")
            self._dashboard_renderproof_label.configure(style="Error.TLabel")
        else:
            self._dashboard_renderproof.set("RenderProof – nicht bestätigt")
            self._dashboard_renderproof_label.configure(style="Warning.TLabel")

        self._dashboard_scheduler_summary.set(
            f"Deaktiviert bis Checkpoint 5 · {len(jobs)} Aufträge vorbereitet · "
            "kein automatischer Start"
        )
        self._refresh_dashboard_preview()

    def _refresh_dashboard_queue(self, jobs, results) -> None:
        tree = self._dashboard_queue_tree
        for item in tree.get_children():
            tree.delete(item)
        results_by_index = {
            int(getattr(result.job, "index", -1)): result
            for result in results
            if getattr(result, "job", None) is not None
        }
        for job in jobs[:100]:
            result = results_by_index.get(int(getattr(job, "index", -1)))
            if result is None:
                status = "Wartend"
                progress = "0 %"
            elif bool(getattr(result, "success", False)):
                status = "Fertig"
                progress = "100 %"
            else:
                status = "Fehler"
                progress = "–"
            name = getattr(getattr(job, "output", None), "name", "") or getattr(
                getattr(job, "audio", None), "name", "Auftrag"
            )
            effect = self.visual_effect.get() if hasattr(self, "visual_effect") else "none"
            tree.insert("", "end", values=(name, effect, status, progress))
        if len(jobs) > 100:
            tree.insert("", "end", values=(f"… {len(jobs) - 100} weitere", "", "", ""))

    def _refresh_dashboard_preview(self) -> None:
        if not hasattr(self, "_dashboard_preview_canvas"):
            return
        canvas = self._dashboard_preview_canvas
        try:
            canvas.delete("all")
            width = max(220, canvas.winfo_width())
            height = max(120, canvas.winfo_height())
            photo = getattr(self, "preview_photo", None)
            if photo is not None:
                canvas.create_image(width / 2, height / 2, image=photo, anchor="center")
            else:
                status = self.preview_status.get() if hasattr(self, "preview_status") else "Noch keine Vorschau"
                canvas.create_text(
                    width / 2,
                    height / 2,
                    text=status,
                    fill=COLORS["muted"],
                    width=max(160, width - 40),
                    justify="center",
                    font=("DejaVu Sans", 11, "bold"),
                )
        except TclError:
            return

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
            ("Erstes Video erstellen", 1, "Zuerst Audio und Medien hinzufügen. Danach Queue prüfen und Produktion starten."),
            ("Fehlende Datei beheben", 1, "Im Medienbereich nicht erreichbare Verweise prüfen und kontrolliert entfernen oder neu zuordnen."),
            ("Queuefehler wiederholen", 4, "Im Queuebereich den ursprünglichen Fehler lesen und nur wiederanlaufbare Quellen erneut laden."),
            ("Cache leeren", 5, "Unter Hilfe die Vorschau-Cache-Diagnose öffnen. Es werden ausschließlich VideoBatch-Vorschaudateien entfernt."),
            ("Update rückgängig machen", 5, "Den bestätigten A/B-Slot beibehalten oder auf ihn zurückfallen. Projekt- und Originaldateien bleiben unverändert."),
        )
        self.help_intent_buttons = {}
        for label, page_index, guidance in entries:
            button = ttk.Button(
                intent,
                text=label,
                command=lambda target=page_index, note=guidance: self._open_help_intent(target, note),
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
        columns = max(1, min(5, available // max(170, requested))) if available else 1
        frame = self._help_intent_frame
        for column in range(5):
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
            self.shell_footer_guidance.set(value if len(value) <= 180 else value[:177] + "…")

        self.guidance_text.trace_add("write", sync_guidance)
        sync_guidance()
        ttk.Label(
            bar,
            textvariable=self.shell_footer_guidance,
            style="Hint.TLabel",
            width=1,
            anchor="w",
        ).grid(row=0, column=0, sticky="ew")
        ttk.Label(
            bar,
            textvariable=self.status_text,
            style="Status.TLabel",
            anchor="e",
        ).grid(row=0, column=1, sticky="e", padx=(10, 0))

    def _restore_shell_selection(self) -> None:
        self._main_tab_restore_in_progress = True
        try:
            selected = min(
                self.main_notebook.index("end") - 1,
                max(0, int(self.config.get("active_tab", 0))),
            )
            self.main_notebook.select(selected)
            self._sync_shell_navigation(selected)
        except Exception:
            self.main_notebook.select(0)
            self._sync_shell_navigation(0)
        finally:
            self._main_tab_restore_in_progress = False

    def _select_shell_page(self, page_index: int | None) -> None:
        if page_index is not None:
            self.main_notebook.select(page_index)
            self.main_notebook.focus_set()

    def _on_shell_tab_changed(self, _event=None) -> None:
        if not self._shell_navigation_ready():
            return
        try:
            selected = int(self.main_notebook.index(self.main_notebook.select()))
        except Exception:
            return
        self._sync_shell_navigation(selected)

    def _shell_navigation_ready(self) -> bool:
        return (
            hasattr(self, "main_notebook")
            and hasattr(self, "shell_section_title")
            and hasattr(self, "_shell_nav_buttons")
            and len(self._shell_nav_buttons) == len(SHELL_NAVIGATION)
        )

    def _sync_shell_navigation(self, selected_index: int) -> None:
        if not self._shell_navigation_ready():
            return
        titles = {
            0: "Dashboard",
            1: "Medien",
            2: "Vorschau",
            3: "Effekte & Einstellungen",
            4: "Queue & Produktion",
            5: "Diagnose & Hilfe",
        }
        self.shell_section_title.set(titles.get(selected_index, "VideoBatch Fast"))
        for item in SHELL_NAVIGATION:
            button = self._shell_nav_buttons.get(item.key)
            if button is None:
                continue
            active = item.page_index == selected_index and item.action != "disabled"
            button.configure(style="ShellNavActive.TButton" if active else "ShellNav.TButton")

    def _run_shell_search(self, _event=None) -> None:
        query = self.shell_search.get().strip().casefold()
        routes = (
            (("medien", "audio", "bild", "video", "import"), 1),
            (("vorschau", "preview", "wellenform", "playlist"), 2),
            (("effekt", "theme", "schrift", "einstellung"), 3),
            (("queue", "render", "produktion", "auftrag"), 4),
            (("hilfe", "diagnose", "fehler", "log"), 5),
        )
        for keywords, index in routes:
            if query and any(keyword in query for keyword in keywords):
                self._select_shell_page(index)
                self.guidance_text.set(
                    f"Bereich für „{self.shell_search.get().strip()}“ geöffnet."
                )
                return
        self.guidance_text.set("Kein direkter Bereich gefunden. Dashboard wurde geöffnet.")
        self._select_shell_page(0)

    def _bind_header_statistics(self) -> None:
        super()._bind_header_statistics()
        for variable in (self.visual_effect, self.transition, self.quick_mode):
            variable.trace_add(
                "write",
                lambda *_args: self.root.after_idle(self._refresh_kpi_cards),
            )
        for variable in (
            self.output_dir,
            self.resolution,
            self.codec,
            self.project_name,
            self.preview_meta,
            self.preview_status,
        ):
            variable.trace_add(
                "write",
                lambda *_args: self.root.after_idle(self._refresh_canonical_dashboard),
            )

    def _update_header_statistics(self) -> None:
        super()._update_header_statistics()
        if not hasattr(self, "shell_media_kpi"):
            return
        self._refresh_kpi_cards()
        self._refresh_canonical_dashboard()
        if hasattr(self, "shell_theme_combo"):
            self.shell_theme_combo.set(
                CANONICAL_THEME_LABELS.get(self.theme_name.get(), "Midnight Blue")
            )
        if hasattr(self, "shell_font_combo"):
            self.shell_font_combo.set(
                self._font_profile_for_scale(self.global_font_scale.get())
            )
