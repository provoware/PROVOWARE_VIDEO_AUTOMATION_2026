from __future__ import annotations

from tkinter import Canvas, StringVar, TclError, ttk

from .canonical_shell_contract import (
    CANONICAL_THEME_LABELS,
    DASHBOARD_COLUMN_WEIGHTS,
    FONT_PROFILES,
    dashboard_layout_mode,
)
from .theme import COLORS

class CanonicalDashboardMixin:
    """Responsive, scrollable dashboard backed only by real application state."""

    def _build_dashboard_page(self, parent) -> None:
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
        ttk.Label(
            assistant_bar,
            text="Geführter Startassistent",
            style="HeaderTitle.TLabel",
        ).pack(side="left")
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
        self._dashboard_scrollbar = scrollbar

        surface = ttk.Frame(canvas, style="Shell.TFrame", padding=(2, 2, 5, 12))
        window_id = canvas.create_window((0, 0), window=surface, anchor="nw")
        self._dashboard_canvas = canvas
        self._dashboard_surface = surface
        self._dashboard_window_id = window_id
        self._dashboard_layout_mode = ""

        self._dashboard_scrollregion = None
        self._dashboard_canvas_width = None
        surface.bind("<Configure>", self._sync_dashboard_scrollregion, add="+")
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
        card.columnconfigure(0, weight=1)
        card.rowconfigure(6, weight=1)
        ttk.Label(
            card,
            text="Quellen & Projekt",
            style="SectionHeader.TLabel",
        ).grid(row=0, column=0, sticky="w")
        self._dashboard_source_summary = StringVar(value="Noch keine Medien ausgewählt")
        self._dashboard_project_summary = StringVar(value="Projekt wird geladen")
        self._dashboard_output_summary = StringVar(value="Ausgabeziel wird geprüft")

        source_label = ttk.Label(
            card,
            textvariable=self._dashboard_source_summary,
            style="Hint.TLabel",
            justify="left",
        )
        source_label.grid(row=1, column=0, sticky="ew", pady=(8, 3))
        project_label = ttk.Label(
            card,
            textvariable=self._dashboard_project_summary,
            style="Hint.TLabel",
            justify="left",
        )
        project_label.grid(row=2, column=0, sticky="ew", pady=3)
        output_label = ttk.Label(
            card,
            textvariable=self._dashboard_output_summary,
            style="Hint.TLabel",
            justify="left",
        )
        output_label.grid(row=3, column=0, sticky="ew", pady=3)
        self._dashboard_wrapped_labels = [source_label, project_label, output_label]

        self._dashboard_source_filter = StringVar(value="Alle")
        filters = ttk.Frame(card, style="ShellCard.TFrame")
        filters.grid(row=4, column=0, sticky="ew", pady=(5, 2))
        for index, label in enumerate(("Alle", "Bilder", "Videos", "Audio", "Unbenutzt")):
            filters.columnconfigure(index, weight=1)
            ttk.Radiobutton(
                filters,
                text=label,
                value=label,
                variable=self._dashboard_source_filter,
                command=self._refresh_canonical_dashboard,
            ).grid(row=0, column=index, sticky="ew", padx=1)

        tag_row = ttk.Frame(card, style="ShellCard.TFrame")
        tag_row.grid(row=5, column=0, sticky="ew", pady=(3, 2))
        tag_row.columnconfigure(0, weight=1)
        self._dashboard_tag_filter = StringVar(value="Alle Tags")
        self._dashboard_tag_filter_combo = ttk.Combobox(
            tag_row,
            textvariable=self._dashboard_tag_filter,
            state="readonly",
            values=("Alle Tags",),
            width=16,
        )
        self._dashboard_tag_filter_combo.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self._dashboard_tag_filter_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_canonical_dashboard())
        ttk.Button(tag_row, text="Tag +", command=self._add_dashboard_tag).grid(row=0, column=1, padx=2)
        ttk.Button(tag_row, text="Tag −", command=self._remove_dashboard_tag).grid(row=0, column=2, padx=(2, 0))

        sources = ttk.Treeview(
            card,
            columns=("type", "name", "tags", "state"),
            show="headings",
            height=10,
            selectmode="extended",
        )
        sources.heading("type", text="Typ")
        sources.heading("name", text="Datei")
        sources.heading("tags", text="Tags")
        sources.heading("state", text="Status")
        sources.column("type", width=58, minwidth=50, stretch=False)
        sources.column("name", width=180, minwidth=110, stretch=True)
        sources.column("tags", width=120, minwidth=80, stretch=True)
        sources.column("state", width=72, minwidth=64, stretch=False)
        sources.grid(row=6, column=0, sticky="nsew", pady=(5, 7))
        self._dashboard_source_tree = sources
        self._dashboard_source_path_map = {}

        actions = ttk.Frame(card, style="ShellCard.TFrame")
        actions.grid(row=7, column=0, sticky="ew")
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)
        ttk.Button(actions, text="♫ Audio", command=self._add_audio).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 3),
            pady=3,
        )
        ttk.Button(actions, text="▧ Bilder / Videos", command=self._add_media).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(3, 0),
            pady=3,
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
        card.rowconfigure(3, weight=1)

        top = ttk.Frame(card, style="ShellCard.TFrame")
        top.grid(row=0, column=0, sticky="ew")
        ttk.Label(top, text="Render Queue", style="SectionHeader.TLabel").pack(side="left")
        self._dashboard_queue_summary = StringVar(value="Keine Aufträge")
        ttk.Label(
            top,
            textvariable=self._dashboard_queue_summary,
            style="Hint.TLabel",
        ).pack(side="right")

        self._dashboard_queue_filter = StringVar(value="")
        self._dashboard_queue_status_filter = StringVar(value="Alle")
        queue_filters = ttk.Frame(card, style="ShellCard.TFrame")
        queue_filters.grid(row=1, column=0, sticky="ew", pady=(7, 4))
        queue_filters.columnconfigure(0, weight=1)
        search = ttk.Entry(queue_filters, textvariable=self._dashboard_queue_filter)
        search.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        search.bind("<KeyRelease>", lambda _event: self._refresh_canonical_dashboard())
        status_filter = ttk.Combobox(
            queue_filters,
            textvariable=self._dashboard_queue_status_filter,
            values=("Alle", "Wartend", "Fertig", "Fehler"),
            state="readonly",
            width=10,
        )
        status_filter.grid(row=0, column=1, sticky="e")
        status_filter.bind("<<ComboboxSelected>>", lambda _event: self._refresh_canonical_dashboard())
        ttk.Separator(card).grid(row=2, column=0, sticky="ew", pady=(0, 5))

        tree = ttk.Treeview(
            card,
            columns=("job", "mode", "effect", "schedule", "status", "progress", "output"),
            show=("tree", "headings"),
            height=10,
        )
        tree.heading("#0", text="")
        tree.column("#0", width=62, minwidth=62, stretch=False, anchor="center")
        tree.heading("job", text="Job")
        tree.heading("mode", text="Modus")
        tree.heading("effect", text="Effekt")
        tree.heading("schedule", text="Zeitplan")
        tree.heading("status", text="Status")
        tree.heading("progress", text="Fortschritt")
        tree.heading("output", text="Ausgabe")
        tree.column("job", width=190, minwidth=120, stretch=True)
        tree.column("mode", width=90, minwidth=70, stretch=False)
        tree.column("effect", width=110, minwidth=80, stretch=True)
        tree.column("schedule", width=90, minwidth=76, stretch=False)
        tree.column("status", width=90, minwidth=78, stretch=False)
        tree.column("progress", width=88, minwidth=72, stretch=False, anchor="e")
        tree.column("output", width=135, minwidth=90, stretch=True)
        tree.grid(row=3, column=0, sticky="nsew")
        tree.bind("<<TreeviewSelect>>", self._select_dashboard_job, add="+")
        self._dashboard_queue_tree = tree
        self._dashboard_tree_job_map = {}

        actions = ttk.Frame(card, style="ShellCard.TFrame")
        actions.grid(row=4, column=0, sticky="ew", pady=(9, 0))
        for column in range(3):
            actions.columnconfigure(column, weight=1)
        ttk.Button(actions, text="Queue öffnen", command=lambda: self._select_shell_page(4)).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 3),
        )
        ttk.Button(actions, text="▶ Start", style="Success.TButton", command=self._start).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=3,
        )
        ttk.Button(actions, text="Abbrechen", style="Danger.TButton", command=self._cancel).grid(
            row=0,
            column=2,
            sticky="ew",
            padx=(3, 0),
        )
        return card

    def _build_dashboard_appearance_card(self, parent):
        card = ttk.Frame(parent, style="ShellCard.TFrame", padding=(14, 12))
        card.columnconfigure(0, weight=1)
        ttk.Label(card, text="Darstellung", style="SectionHeader.TLabel").grid(
            row=0,
            column=0,
            sticky="w",
        )
        appearance_hint = ttk.Label(
            card,
            text="Theme und Schrift wirken sofort und werden gespeichert.",
            style="Hint.TLabel",
        )
        appearance_hint.grid(row=1, column=0, sticky="ew", pady=(3, 8))
        appearance_hint.bind(
            "<Configure>",
            lambda event: appearance_hint.configure(wraplength=max(180, event.width - 4)),
            add="+",
        )

        theme_reverse = {label: key for key, label in CANONICAL_THEME_LABELS.items()}
        self.shell_theme_combo = ttk.Combobox(card, values=list(theme_reverse), state="readonly")
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

    def _sync_dashboard_scrollregion(self, _event=None) -> None:
        try:
            region = self._dashboard_canvas.bbox("all")
            if region == self._dashboard_scrollregion:
                return
            self._dashboard_scrollregion = region
            self._dashboard_canvas.configure(scrollregion=region)
        except TclError:
            return

    def _on_dashboard_canvas_configure(self, event) -> None:
        width = max(1, int(event.width))
        if self._dashboard_canvas_width != width:
            self._dashboard_canvas_width = width
            self._dashboard_canvas.itemconfigure(self._dashboard_window_id, width=width)
        self._layout_canonical_dashboard(width)

    def _scroll_dashboard(self, event) -> None:
        delta = int(getattr(event, "delta", 0))
        if delta:
            self._dashboard_canvas.yview_scroll(-1 if delta > 0 else 1, "units")

    def _layout_canonical_dashboard(self, width: int) -> None:
        if not hasattr(self, "_dashboard_surface"):
            return
        mode = dashboard_layout_mode(width)
        if self._dashboard_layout_mode == mode:
            self._update_dashboard_wraplengths()
            return
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
            self._dashboard_sources_card.grid(
                row=0,
                column=0,
                sticky="nsew",
                padx=(0, 6),
                pady=(0, 7),
            )
            self._dashboard_queue_card.grid(
                row=0,
                column=1,
                sticky="nsew",
                padx=6,
                pady=(0, 7),
            )
            self._dashboard_details_card.grid(
                row=0,
                column=2,
                sticky="nsew",
                padx=(6, 0),
                pady=(0, 7),
            )
            self._dashboard_surface.rowconfigure(0, weight=1)
            self._dashboard_surface.rowconfigure(1, weight=0)
            self._dashboard_scheduler_card.grid(
                row=1,
                column=0,
                columnspan=3,
                sticky="ew",
                pady=(5, 0),
            )
            if hasattr(self, "_dashboard_scrollbar"):
                self._dashboard_scrollbar.grid_remove()
        elif mode == "two_columns":
            self._dashboard_surface.columnconfigure(0, weight=35)
            self._dashboard_surface.columnconfigure(1, weight=65)
            self._dashboard_sources_card.grid(
                row=0,
                column=0,
                sticky="nsew",
                padx=(0, 6),
                pady=(0, 7),
            )
            self._dashboard_queue_card.grid(
                row=0,
                column=1,
                sticky="nsew",
                padx=(6, 0),
                pady=(0, 7),
            )
            self._dashboard_details_card.grid(
                row=1,
                column=0,
                columnspan=2,
                sticky="nsew",
                pady=7,
            )
            self._dashboard_scheduler_card.grid(
                row=2,
                column=0,
                sticky="nsew",
                padx=(0, 6),
                pady=(7, 0),
            )
            if hasattr(self, "_dashboard_scrollbar"):
                self._dashboard_scrollbar.grid()
        else:
            self._dashboard_surface.columnconfigure(0, weight=1)
            if hasattr(self, "_dashboard_scrollbar"):
                self._dashboard_scrollbar.grid()
            for row, card in enumerate(cards[:-1]):
                card.grid(
                    row=row,
                    column=0,
                    sticky="nsew",
                    pady=(0 if row == 0 else 7, 0),
                )

        self._dashboard_layout_mode = mode
        self._update_dashboard_wraplengths()
        self.root.after_idle(self._sync_dashboard_scrollregion)

    def _update_dashboard_wraplengths(self, _event=None) -> None:
        for label in getattr(self, "_dashboard_wrapped_labels", ()):
            try:
                width = max(160, label.master.winfo_width() - 30)
                current = int(float(label.cget("wraplength") or 0))
                if current != width:
                    label.configure(wraplength=width)
            except (TclError, ValueError):
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
        project_name = (
            self.project_name.get().strip()
            if hasattr(self, "project_name")
            else "Neues Projekt"
        )
        self._dashboard_project_summary.set(f"Projekt: {project_name or 'Neues Projekt'}")
        output_value = self.output_dir.get().strip() if hasattr(self, "output_dir") else ""
        self._dashboard_output_summary.set(f"Ausgabe: {output_value or 'Noch nicht gewählt'}")
        self._refresh_dashboard_sources(audios, media)

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
        preview_meta = (
            self.preview_meta.get()
            if hasattr(self, "preview_meta")
            else "Noch keine Vorschau"
        )
        self._dashboard_detail_summary.set(
            f"Effekt: {effect} · Modus: {quick_mode}\nVorschau: {preview_meta}"
        )
        if hasattr(self, "_dashboard_output_detail"):
            self._dashboard_output_detail.set(
                f"Auflösung: {resolution}\nCodec: {codec}\nOrdner: {output_value or 'Noch nicht gewählt'}"
            )

        if results and failed == 0:
            self._dashboard_renderproof.set("RenderProof – Bestanden")
            self._dashboard_renderproof_label.configure(style="Success.TLabel")
        elif failed:
            self._dashboard_renderproof.set(
                "RenderProof – nicht bestätigt · Fehler vorhanden"
            )
            self._dashboard_renderproof_label.configure(style="Error.TLabel")
        else:
            self._dashboard_renderproof.set("RenderProof – nicht bestätigt")
            self._dashboard_renderproof_label.configure(style="Warning.TLabel")

        active_schedule = self._active_scheduler_record() if hasattr(self, "_active_scheduler_record") else None
        if active_schedule is not None:
            when = str(active_schedule.get("scheduled_at", "–")).replace("T", " ")[:16]
            self._dashboard_scheduler_summary.set(f"Geplant: {when} · {active_schedule.get('status', 'pending')}")
        else:
            self._dashboard_scheduler_summary.set(f"Nicht geplant · {len(jobs)} Auftrag/Aufträge bereit")
        self._refresh_dashboard_preview()

    def _refresh_dashboard_queue(self, jobs, results) -> None:
        tree = self._dashboard_queue_tree
        selected_index = getattr(self, "_dashboard_selected_job_index", None)
        for item in tree.get_children():
            tree.delete(item)
        self._dashboard_tree_job_map = {}
        self._dashboard_queue_thumbnail_items = {}
        results_by_index = {
            int(getattr(result.job, "index", -1)): result
            for result in results
            if getattr(result, "job", None) is not None
        }
        query = self._dashboard_queue_filter.get().strip().casefold()
        status_filter = (
            self._dashboard_queue_status_filter.get()
            if hasattr(self, "_dashboard_queue_status_filter")
            else "Alle"
        )
        visible = []
        for job in jobs:
            index = int(getattr(job, "index", -1))
            result = results_by_index.get(index)
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
                getattr(job, "audio", None),
                "name",
                "Auftrag",
            )
            effect = self.visual_effect.get() if hasattr(self, "visual_effect") else "none"
            if query and query not in f"{name} {effect} {status}".casefold():
                continue
            if status_filter != "Alle" and status != status_filter:
                continue
            visible.append((job, name, effect, status, progress))

        for job, name, effect, status, progress in visible[:100]:
            index = int(getattr(job, "index", -1))
            source = self._queue_thumbnail_source(job) if hasattr(self, "_queue_thumbnail_source") else None
            photo = self._queue_thumbnail_photo(source) if hasattr(self, "_queue_thumbnail_photo") else None
            insert_options = {
                "values": (
                    name,
                    self.quick_mode.get() if hasattr(self, "quick_mode") else "Auto",
                    effect,
                    "Nicht geplant",
                    status,
                    progress,
                    getattr(getattr(job, "output", None), "name", ""),
                )
            }
            if photo is not None:
                insert_options["image"] = photo
            item_id = tree.insert("", "end", **insert_options)
            self._dashboard_tree_job_map[item_id] = job
            if hasattr(self, "_request_queue_thumbnail"):
                self._request_queue_thumbnail(item_id, job)
            if selected_index == index:
                tree.selection_set(item_id)
                tree.focus(item_id)
        if hasattr(self, "_prune_queue_thumbnail_refs"):
            active_sources = {
                source
                for job, _name, _effect, _status, _progress in visible[:100]
                if (source := self._queue_thumbnail_source(job)) is not None
            }
            self._prune_queue_thumbnail_refs(active_sources)
        if len(visible) > 100:
            tree.insert(
                "",
                "end",
                values=(f"… {len(visible) - 100} weitere", "", "", "", "", "", ""),
            )

    def _select_dashboard_job(self, _event=None) -> None:
        selected = self._dashboard_queue_tree.selection()
        if not selected:
            return
        job = self._dashboard_tree_job_map.get(selected[0])
        if job is None:
            return
        self._dashboard_selected_job_index = int(getattr(job, "index", -1))
        audio_name = getattr(getattr(job, "audio", None), "name", "–")
        media_names = ", ".join(
            path.name for path in tuple(getattr(job, "source_media", ()))[:3]
        ) or "–"
        output_name = getattr(getattr(job, "output", None), "name", "–")
        if hasattr(self, "_dashboard_detail_title"):
            self._dashboard_detail_title.set(f"Job Details: {output_name}")
        self._dashboard_detail_summary.set(
            f"Audio: {audio_name}\nMedien: {media_names}\nAusgabe: {output_name}"
        )
        preview_source = (
            self._queue_thumbnail_source(job)
            if hasattr(self, "_queue_thumbnail_source")
            else None
        )
        if preview_source is not None and hasattr(self, "_request_preview"):
            self._request_preview(preview_source)
        if hasattr(self, "_set_dashboard_transport_source"):
            self._set_dashboard_transport_source(preview_source)

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
                status = (
                    self.preview_status.get()
                    if hasattr(self, "preview_status")
                    else "Noch keine Vorschau"
                )
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
