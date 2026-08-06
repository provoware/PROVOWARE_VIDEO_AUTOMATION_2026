from __future__ import annotations

from tkinter import StringVar, TclError, ttk
from typing import Callable

from .canonical_kpi import build_kpi_snapshots
from .canonical_shell_contract import CANONICAL_THEME_LABELS, FONT_PROFILES, SHELL_NAVIGATION
from .theme import COLORS, apply_theme, available_themes, best_text_color, safe_text_color
from .versioning import build_label


class CanonicalShellChromeMixin:
    def _configure_shell_styles(self) -> None:
        style = ttk.Style(self.root)
        scale = int(self.global_font_scale.get()) if hasattr(self, "global_font_scale") else 105
        factor = max(0.85, min(1.35, scale / 105.0))
        toolbar_text = safe_text_color(COLORS["toolbar"], COLORS["text"])
        toolbar_muted = safe_text_color(COLORS["toolbar"], COLORS["muted"])
        panel_text = safe_text_color(COLORS["panel"], COLORS["text"])
        panel_muted = safe_text_color(COLORS["panel"], COLORS["muted"])

        style.configure("Shell.TFrame", background=COLORS["bg"])
        style.configure(
            "ShellSidebar.TFrame",
            background=COLORS["toolbar"],
            relief="solid",
            borderwidth=1,
        )
        style.configure(
            "ShellHeader.TFrame",
            background=COLORS["toolbar"],
            relief="solid",
            borderwidth=1,
        )
        style.configure(
            "ShellCard.TFrame",
            background=COLORS["panel"],
            relief="solid",
            borderwidth=1,
        )
        style.configure(
            "ShellBrand.TLabel",
            background=COLORS["toolbar"],
            foreground=toolbar_text,
            font=("DejaVu Sans", max(15, round(17 * factor)), "bold"),
        )
        style.configure(
            "ShellHint.TLabel",
            background=COLORS["toolbar"],
            foreground=toolbar_muted,
            font=("DejaVu Sans", max(9, round(10 * factor))),
        )
        style.configure(
            "ShellHeaderStatus.TLabel",
            background=COLORS["toolbar"],
            foreground=safe_text_color(COLORS["toolbar"], COLORS["success"]),
            font=("DejaVu Sans", max(9, round(10 * factor)), "bold"),
            anchor="e",
        )
        style.configure(
            "ShellKpi.TLabel",
            background=COLORS["panel"],
            foreground=panel_text,
            font=("DejaVu Sans", max(18, round(21 * factor)), "bold"),
        )
        style.configure(
            "ShellKpiHint.TLabel",
            background=COLORS["panel"],
            foreground=panel_muted,
            font=("DejaVu Sans", max(9, round(10 * factor))),
        )
        style.configure(
            "ShellKpiLink.TButton",
            background=COLORS["panel2"],
            foreground=safe_text_color(COLORS["panel2"], COLORS["text"]),
            padding=(7, 3),
            font=("DejaVu Sans", max(9, round(9 * factor)), "bold"),
            borderwidth=1,
        )

        state_colors = {
            "empty": COLORS["muted"],
            "ready": COLORS["accent2"],
            "loading": COLORS["warning"],
            "success": COLORS["success"],
            "warning": COLORS["warning"],
            "error": COLORS["danger"],
            "disabled": COLORS["disabled"],
        }
        for state, color in state_colors.items():
            style.configure(
                f"ShellKpiState{state.title()}.TLabel",
                background=COLORS["panel"],
                foreground=safe_text_color(COLORS["panel"], color),
                font=("DejaVu Sans", max(9, round(10 * factor)), "bold"),
            )

        nav_padding_y = max(7, round(8 * factor))
        style.configure(
            "ShellNav.TButton",
            background=COLORS["toolbar"],
            foreground=toolbar_text,
            padding=(12, nav_padding_y),
            anchor="w",
            relief="flat",
            borderwidth=0,
        )
        style.configure(
            "ShellNavActive.TButton",
            background=COLORS["selection"],
            foreground=best_text_color(COLORS["selection"]),
            padding=(12, nav_padding_y),
            anchor="w",
            relief="flat",
            borderwidth=0,
        )
        style.configure("Shell.TNotebook", background=COLORS["bg"], borderwidth=0)
        style.layout("Shell.TNotebook.Tab", [])

    def _build_shell_sidebar(self, parent) -> None:
        ttk.Label(parent, text="▣  VideoBatch Fast", style="ShellBrand.TLabel").pack(anchor="w")
        ttk.Label(parent, text="Batch Video Processing", style="ShellHint.TLabel").pack(
            anchor="w",
            padx=(27, 0),
            pady=(2, 16),
        )
        self._shell_nav_buttons = {}
        for item in SHELL_NAVIGATION:
            if item.action == "disabled":
                button = ttk.Button(
                    parent,
                    text=item.label + " · Checkpoint 5",
                    style="ShellNav.TButton",
                    state="disabled",
                )
            elif item.action == "settings":
                button = ttk.Button(
                    parent,
                    text=item.label,
                    style="ShellNav.TButton",
                    command=self._open_settings,
                )
            else:
                button = ttk.Button(
                    parent,
                    text=item.label,
                    style="ShellNav.TButton",
                    command=lambda index=item.page_index: self._select_shell_page(index),
                )
            button.pack(fill="x", pady=2)
            self._shell_nav_buttons[item.key] = button

        ttk.Frame(parent, style="ShellSidebar.TFrame").pack(fill="both", expand=True)
        status = ttk.Frame(parent, style="ShellCard.TFrame", padding=10)
        status.pack(fill="x", pady=(10, 0))
        ttk.Label(status, text="Systemstatus", style="ShellKpiHint.TLabel").pack(anchor="w")
        sidebar_status = ttk.Label(
            status,
            textvariable=self.status_text,
            style="Success.TLabel",
            justify="left",
        )
        sidebar_status.pack(anchor="w", fill="x", pady=(6, 3))
        sidebar_status.bind(
            "<Configure>",
            lambda event: sidebar_status.configure(wraplength=max(130, event.width - 4)),
            add="+",
        )
        ttk.Label(
            status,
            text=f"Version {build_label()}",
            style="ShellKpiHint.TLabel",
        ).pack(anchor="w")

    def _build_shell_header(self, parent) -> None:
        header = ttk.Frame(parent, style="ShellHeader.TFrame", padding=(12, 8))
        header.grid(row=0, column=0, sticky="ew", pady=(0, 9))
        self._shell_header = header

        identity = ttk.Frame(header, style="ShellHeader.TFrame")
        self._shell_header_identity = identity
        self.shell_section_title = StringVar(value="Dashboard")
        ttk.Label(
            identity,
            textvariable=self.shell_section_title,
            style="HeaderTitle.TLabel",
        ).pack(anchor="w")
        ttk.Label(
            identity,
            text="VideoBatch Fast · VB-GFX-1.0",
            style="ShellHint.TLabel",
        ).pack(anchor="w")

        search_host = ttk.Frame(header, style="ShellHeader.TFrame")
        self._shell_header_search_host = search_host
        search_host.columnconfigure(1, weight=1)
        ttk.Label(search_host, text="Suche", style="ShellHint.TLabel").grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 7),
        )
        self.shell_search = StringVar(value="")
        search = ttk.Entry(search_host, textvariable=self.shell_search)
        search.grid(row=0, column=1, sticky="ew")
        search.bind("<Return>", self._run_shell_search)

        controls = ttk.Frame(header, style="ShellHeader.TFrame")
        self._shell_header_controls = controls
        self.shell_header_status = StringVar(value="")

        def sync_status(*_args) -> None:
            value = self.status_text.get().replace("\n", " ").strip()
            self.shell_header_status.set(value if len(value) <= 46 else value[:43] + "…")

        self.status_text.trace_add("write", sync_status)
        sync_status()
        ttk.Label(
            controls,
            textvariable=self.shell_header_status,
            style="ShellHeaderStatus.TLabel",
        ).pack(side="left", padx=(0, 8))
        ttk.Button(
            controls,
            text="Hilfe",
            style="HeaderControl.TButton",
            command=self._show_help_center,
        ).pack(side="left", padx=(0, 5))
        ttk.Button(
            controls,
            text="⚙",
            width=3,
            style="HeaderControl.TButton",
            command=self._open_settings,
        ).pack(side="left")

        header.bind("<Configure>", self._layout_shell_header, add="+")
        self.root.after_idle(lambda: self._layout_shell_header(width=header.winfo_width()))

    def _layout_shell_header(self, event=None, *, width: int | None = None) -> None:
        available = int(width if width is not None else getattr(event, "width", 0))
        header = self._shell_header
        identity = self._shell_header_identity
        search_host = self._shell_header_search_host
        controls = self._shell_header_controls
        for widget in (identity, search_host, controls):
            widget.grid_forget()
        for column in range(3):
            header.columnconfigure(column, weight=0, minsize=0)

        required = (
            identity.winfo_reqwidth()
            + search_host.winfo_reqwidth()
            + controls.winfo_reqwidth()
            + 48
        )
        if available and available < max(780, required):
            header.columnconfigure(0, weight=1)
            header.columnconfigure(1, weight=0)
            identity.grid(row=0, column=0, sticky="w")
            controls.grid(row=0, column=1, sticky="e")
            search_host.grid(
                row=1,
                column=0,
                columnspan=2,
                sticky="ew",
                pady=(7, 0),
            )
        else:
            header.columnconfigure(0, weight=0)
            header.columnconfigure(1, weight=1)
            header.columnconfigure(2, weight=0)
            identity.grid(row=0, column=0, sticky="w", padx=(0, 14))
            search_host.grid(row=0, column=1, sticky="ew", padx=(0, 14))
            controls.grid(row=0, column=2, sticky="e")

    def _build_shell_kpis(self, parent) -> None:
        row = ttk.Frame(parent, style="Shell.TFrame")
        row.grid(row=1, column=0, sticky="ew", pady=(0, 9))
        self._shell_kpi_row = row

        self._shell_kpi_value_vars = {
            key: StringVar(value="–")
            for key in ("media", "queue", "effects", "scheduler")
        }
        self._shell_kpi_detail_vars = {
            key: StringVar(value="Wird ermittelt")
            for key in self._shell_kpi_value_vars
        }
        self._shell_kpi_status_vars = {
            key: StringVar(value="Prüfung")
            for key in self._shell_kpi_value_vars
        }
        self.shell_media_kpi = self._shell_kpi_value_vars["media"]
        self.shell_queue_kpi = self._shell_kpi_value_vars["queue"]
        self.shell_effect_kpi = self._shell_kpi_value_vars["effects"]
        self.shell_scheduler_kpi = self._shell_kpi_value_vars["scheduler"]
        self._shell_kpi_status_labels = {}
        self._shell_kpi_buttons = {}
        self._shell_kpi_cards = []
        self._shell_kpi_detail_labels = []

        cards = (
            ("media", "Medien", 1, "Medien öffnen"),
            ("queue", "Queue", 4, "Queue öffnen"),
            ("effects", "Effekte", 3, "Effekte öffnen"),
            ("scheduler", "Startzeituhr", None, "Checkpoint 5"),
        )
        for key, title, page_index, action_label in cards:
            card = ttk.Frame(row, style="ShellCard.TFrame", padding=(13, 9))
            self._shell_kpi_cards.append(card)
            ttk.Label(card, text=title, style="ShellKpiHint.TLabel").pack(anchor="w")
            ttk.Label(
                card,
                textvariable=self._shell_kpi_value_vars[key],
                style="ShellKpi.TLabel",
            ).pack(anchor="w", pady=(3, 0))
            detail = ttk.Label(
                card,
                textvariable=self._shell_kpi_detail_vars[key],
                style="ShellKpiHint.TLabel",
                justify="left",
            )
            detail.pack(anchor="w", fill="x", pady=(1, 0))
            self._shell_kpi_detail_labels.append(detail)
            status = ttk.Label(
                card,
                textvariable=self._shell_kpi_status_vars[key],
                style="ShellKpiStateEmpty.TLabel",
            )
            status.pack(anchor="w", pady=(4, 3))
            self._shell_kpi_status_labels[key] = status
            button = ttk.Button(
                card,
                text=action_label,
                style="ShellKpiLink.TButton",
                command=(
                    (lambda index=page_index: self._select_shell_page(index))
                    if page_index is not None
                    else None
                ),
            )
            button.pack(fill="x")
            self._shell_kpi_buttons[key] = button
            card.bind("<Configure>", self._update_shell_kpi_wraplengths, add="+")

        row.bind("<Configure>", self._layout_shell_kpis, add="+")
        self.root.after_idle(lambda: self._layout_shell_kpis(width=row.winfo_width()))
        self._refresh_kpi_cards()
        self._shell_kpi_poll_id = self.root.after(1000, self._poll_shell_kpis)

    def _layout_shell_kpis(self, event=None, *, width: int | None = None) -> None:
        if not getattr(self, "_shell_kpi_cards", None):
            return
        available = int(width if width is not None else getattr(event, "width", 0))
        if available >= 1040:
            columns = 4
        elif available >= 600:
            columns = 2
        else:
            columns = 1
        row = self._shell_kpi_row
        for column in range(4):
            row.columnconfigure(column, weight=1 if column < columns else 0, uniform="kpi")
        for card in self._shell_kpi_cards:
            card.grid_forget()
        for index, card in enumerate(self._shell_kpi_cards):
            card.grid(
                row=index // columns,
                column=index % columns,
                sticky="nsew",
                padx=4,
                pady=4,
            )
        self._update_shell_kpi_wraplengths()

    def _update_shell_kpi_wraplengths(self, _event=None) -> None:
        for label in getattr(self, "_shell_kpi_detail_labels", ()): 
            try:
                label.configure(wraplength=max(130, label.master.winfo_width() - 26))
            except TclError:
                return

    def _refresh_kpi_cards(self) -> None:
        if not hasattr(self, "_shell_kpi_value_vars"):
            return
        paths = tuple(getattr(self, "audios", ())) + tuple(getattr(self, "media", ()))
        missing_sources = sum(1 for path in paths if not path.is_file())
        last_results = tuple(getattr(self, "last_results", ()))
        failed_jobs = sum(
            1 for result in last_results if not bool(getattr(result, "success", False))
        )
        active_tasks = self.tasks.active_names() if hasattr(self, "tasks") else ()
        snapshots = build_kpi_snapshots(
            audio_count=len(getattr(self, "audios", ())),
            media_count=len(getattr(self, "media", ())),
            missing_sources=missing_sources,
            job_count=len(getattr(self, "jobs", ())),
            completed_jobs=len(last_results),
            failed_jobs=failed_jobs,
            active_tasks=active_tasks,
            visual_effect=self.visual_effect.get(),
            transition=self.transition.get(),
            quick_mode=self.quick_mode.get(),
        )
        for key, snapshot in snapshots.items():
            self._shell_kpi_value_vars[key].set(snapshot.value)
            self._shell_kpi_detail_vars[key].set(snapshot.detail)
            self._shell_kpi_status_vars[key].set(snapshot.status)
            self._shell_kpi_status_labels[key].configure(
                style=f"ShellKpiState{snapshot.state.title()}.TLabel"
            )
            self._shell_kpi_buttons[key].configure(
                state="normal" if snapshot.action_enabled else "disabled"
            )

    def _poll_shell_kpis(self) -> None:
        try:
            if not self.root.winfo_exists():
                return
            self._refresh_kpi_cards()
            if hasattr(self, "_refresh_canonical_dashboard"):
                self._refresh_canonical_dashboard()
            self._shell_kpi_poll_id = self.root.after(1000, self._poll_shell_kpis)
        except TclError:
            return

    def _build_shell_actions(self, parent) -> None:
        bar = ttk.Frame(parent, style="ShellHeader.TFrame", padding=(7, 5))
        bar.grid(row=2, column=0, sticky="ew", pady=(0, 9))
        actions: tuple[tuple[str, Callable[[], object], str, str], ...] = (
            ("＋ Neuer Auftrag", self._new_project, "Accent.TButton", "normal"),
            ("♫ Audio importieren", self._add_audio, "Ghost.TButton", "normal"),
            ("▧ Medien importieren", self._add_media, "Ghost.TButton", "normal"),
            ("✦ Effekte prüfen", self._open_settings, "Ghost.TButton", "normal"),
            ("▶ Queue starten", self._start, "Success.TButton", "normal"),
            ("▣ Zielordner", lambda: self._choose_directory(self.output_dir), "Ghost.TButton", "normal"),
            ("◷ Startzeituhr · Checkpoint 5", lambda: None, "Ghost.TButton", "disabled"),
        )
        self._shell_action_buttons = [
            ttk.Button(bar, text=label, command=command, style=style, state=state)
            for label, command, style, state in actions
        ]
        bar.bind("<Configure>", self._layout_shell_actions, add="+")
        self.root.after_idle(lambda: self._layout_shell_actions(width=bar.winfo_width()))

    def _layout_shell_actions(self, event=None, *, width: int | None = None) -> None:
        buttons = getattr(self, "_shell_action_buttons", ())
        if not buttons:
            return
        available = int(width if width is not None else getattr(event, "width", 0))
        requested = max((button.winfo_reqwidth() for button in buttons), default=170) + 12
        columns = max(1, min(len(buttons), available // max(145, requested))) if available else 1
        parent = buttons[0].master
        for column in range(len(buttons)):
            parent.columnconfigure(column, weight=1 if column < columns else 0)
        for index, button in enumerate(buttons):
            button.grid_forget()
            button.grid(
                row=index // columns,
                column=index % columns,
                sticky="ew",
                padx=3,
                pady=3,
            )

    def _set_canonical_theme(self, name: str) -> None:
        if name not in available_themes():
            name = "neon_gravity"
        self.theme_name.set(name)
        self.config["theme"] = name
        apply_theme(self.root, self.global_font_scale.get(), name)
        self._refresh_theme_widgets()
        if hasattr(self, "shell_theme_combo"):
            self.shell_theme_combo.set(CANONICAL_THEME_LABELS[name])
        self._save_settings()
        self.guidance_text.set(f"Farbtheme aktiviert: {CANONICAL_THEME_LABELS[name]}.")

    @staticmethod
    def _font_profile_for_scale(scale: int) -> str:
        return min(FONT_PROFILES, key=lambda label: abs(FONT_PROFILES[label] - int(scale)))

    def _refresh_theme_widgets(self) -> None:
        super()._refresh_theme_widgets()
        self._configure_shell_styles()
        if hasattr(self, "_dashboard_canvas"):
            self._dashboard_canvas.configure(background=COLORS["bg"])
        if hasattr(self, "_dashboard_preview_canvas"):
            self._dashboard_preview_canvas.configure(
                background=COLORS["preview"],
                highlightbackground=COLORS["border"],
            )
        self._refresh_kpi_cards()
        if hasattr(self, "_refresh_canonical_dashboard"):
            self._refresh_canonical_dashboard()
