from __future__ import annotations

from tkinter import StringVar, TclError, ttk
from typing import Callable

from .canonical_kpi import build_kpi_snapshots
from .icon_assets import load_ui_icon
from .canonical_shell_contract import CANONICAL_THEME_LABELS, FONT_PROFILES, SHELL_NAVIGATION
from .theme import COLORS, apply_theme, available_themes, best_text_color, safe_text_color
from .ui_components import Tooltip
from .versioning import build_label
from .system_metrics import collect_system_metrics, format_bytes


class CanonicalShellChromeMixin:
    @staticmethod
    def _set_wraplength_if_changed(label, target: int) -> None:
        try:
            current = int(float(label.cget("wraplength") or 0))
            if current != target:
                label.configure(wraplength=target)
        except (TclError, ValueError):
            return

    def _request_shell_header_layout(self) -> None:
        """Coalesce header relayouts after text/font metrics changed without a resize."""
        if not hasattr(self, "_shell_header"):
            return
        pending = getattr(self, "_shell_header_layout_after_id", None)
        if pending is not None:
            return

        def relayout() -> None:
            self._shell_header_layout_after_id = None
            try:
                if self._shell_header.winfo_exists():
                    self._layout_shell_header(width=self._shell_header.winfo_width())
            except TclError:
                return

        try:
            self._shell_header_layout_after_id = self.root.after_idle(relayout)
        except TclError:
            self._shell_header_layout_after_id = None

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
            bordercolor=COLORS["border_subtle"],
        )
        for style_name, accent in (
            ("ShellKpiMedia.TFrame", COLORS["tile_blue"]),
            ("ShellKpiQueue.TFrame", COLORS["tile_magenta"]),
            ("ShellKpiEffects.TFrame", COLORS["tile_green"]),
            ("ShellKpiScheduler.TFrame", COLORS["tile_gold"]),
        ):
            style.configure(style_name, background=COLORS["panel"], relief="solid", borderwidth=1, bordercolor=accent)
        style.configure(
            "ShellBrand.TLabel",
            background=COLORS["toolbar"],
            foreground=toolbar_text,
            font=("DejaVu Sans", max(14, round(16 * factor)), "bold"),
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
            font=("DejaVu Sans", max(16, round(18 * factor)), "bold"),
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
            padding=(7, 2),
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

        nav_padding_y = max(5, round(6 * factor))
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
        brand = ttk.Frame(parent, style="ShellSidebar.TFrame")
        brand.pack(fill="x", pady=(0, 10))
        brand_icon = load_ui_icon(self, "brand", size=40)
        ttk.Label(
            brand,
            image=brand_icon,
            text="VB" if brand_icon is None else "",
            style="ShellBrand.TLabel",
        ).pack(side="left", padx=(0, 8))
        brand_text = ttk.Frame(brand, style="ShellSidebar.TFrame")
        brand_text.pack(side="left", fill="x", expand=True)
        ttk.Label(brand_text, text="VideoBatch Fast", style="ShellBrand.TLabel").pack(anchor="w")
        ttk.Label(brand_text, text="Video Automation", style="ShellHint.TLabel").pack(anchor="w")
        self._shell_nav_buttons = {}
        for item in SHELL_NAVIGATION:
            icon = load_ui_icon(self, item.key, size=20)
            label = item.label + ("  · gesperrt" if item.action == "disabled" else "")
            options = {
                "text": label,
                "image": icon,
                "compound": "left",
                "style": "ShellNav.TButton",
            }
            if item.action == "disabled":
                options["state"] = "disabled"
            elif item.action == "settings":
                options["command"] = self._open_settings
            elif item.action == "scheduler":
                options["command"] = self._open_scheduler_dialog
            else:
                options["command"] = lambda index=item.page_index: self._select_shell_page(index)
            button = ttk.Button(parent, **options)
            button.pack(fill="x", pady=2)
            self._shell_nav_buttons[item.key] = button

        ttk.Frame(parent, style="ShellSidebar.TFrame").pack(fill="both", expand=True)
        status = ttk.Frame(parent, style="ShellCard.TFrame", padding=8)
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
            lambda event: self._set_wraplength_if_changed(sidebar_status, max(130, event.width - 4)),
            add="+",
        )
        ttk.Label(
            status,
            text=f"v{build_label()} · RC",
            style="ShellKpiHint.TLabel",
        ).pack(anchor="w")

    def _build_shell_header(self, parent) -> None:
        header = ttk.Frame(parent, style="ShellHeader.TFrame", padding=(10, 6))
        header.grid(row=0, column=0, sticky="ew", pady=(0, 7))
        self._shell_header = header

        identity = ttk.Frame(header, style="ShellHeader.TFrame")
        self._shell_header_identity = identity
        self.shell_section_title = StringVar(value="Dashboard")
        ttk.Label(identity, text="VideoBatch Fast", style="ShellBrand.TLabel").pack(anchor="w")
        ttk.Label(identity, textvariable=self.shell_section_title, style="ShellHint.TLabel").pack(anchor="w")

        search_host = ttk.Frame(header, style="ShellHeader.TFrame")
        self._shell_header_search_host = search_host
        search_host.columnconfigure(0, weight=1)
        self.shell_search = StringVar(value="")
        search = ttk.Entry(search_host, textvariable=self.shell_search)
        search.grid(row=0, column=0, sticky="ew")
        search.bind("<Return>", self._run_shell_search)
        Tooltip(search, "Medien, Jobs, Effekte oder Hilfe suchen. Eingabe mit Enter öffnen.")

        badges = ttk.Frame(header, style="ShellHeader.TFrame")
        self._shell_header_badges = badges
        self._shell_ffmpeg_badge = StringVar(value="FFmpeg …")
        self._shell_gpu_badge = StringVar(value="GPU …")
        self._shell_cache_badge = StringVar(value="Cache …")
        for variable in (self._shell_ffmpeg_badge, self._shell_gpu_badge, self._shell_cache_badge):
            ttk.Label(badges, textvariable=variable, style="StatusPill.TLabel").pack(side="left", padx=2)

        controls = ttk.Frame(header, style="ShellHeader.TFrame")
        self._shell_header_controls = controls
        self.shell_header_status = StringVar(value="")

        def sync_status(*_args) -> None:
            value = self.status_text.get().replace("\n", " ").strip()
            self.shell_header_status.set(value if len(value) <= 34 else value[:31] + "…")
            self._request_shell_header_layout()

        self.status_text.trace_add("write", sync_status)
        sync_status()
        status_label = ttk.Label(controls, textvariable=self.shell_header_status, style="ShellHeaderStatus.TLabel")
        status_label.pack(side="left", padx=(0, 7))
        self._shell_header_status_label = status_label
        help_button = ttk.Button(controls, text="?", width=3, style="HeaderControl.TButton", command=self._show_help_center)
        help_button.pack(side="left", padx=(0, 4))
        self._shell_header_help_button = help_button
        Tooltip(help_button, "Hilfe und sichere nächste Schritte öffnen.")
        settings_button = ttk.Button(controls, text="⚙", width=3, style="HeaderControl.TButton", command=self._open_settings)
        settings_button.pack(side="left")
        self._shell_header_settings_button = settings_button
        Tooltip(settings_button, "Darstellung und Einstellungen öffnen.")

        header.bind("<Configure>", self._layout_shell_header, add="+")
        if hasattr(self, "global_font_scale"):
            self.global_font_scale.trace_add("write", lambda *_args: self._request_shell_header_layout())
        self.root.after_idle(lambda: self._layout_shell_header(width=header.winfo_width()))

    def _layout_shell_header(self, event=None, *, width: int | None = None) -> None:
        """Lay out the topbar by priority without ever sacrificing search or utility controls.

        Priority from highest to lowest is: identity, search, Help/Settings, runtime badges,
        redundant prose status. The same status remains available in sidebar/footer when hidden.
        """
        available = int(width if width is not None else getattr(event, "width", 0))
        if available <= 1:
            return
        header = self._shell_header
        identity = self._shell_header_identity
        search_host = self._shell_header_search_host
        badges = self._shell_header_badges
        controls = self._shell_header_controls

        identity_req = max(118, identity.winfo_reqwidth())
        utility_req = max(78, self._shell_header_help_button.winfo_reqwidth() + self._shell_header_settings_button.winfo_reqwidth() + 12)
        status_req = max(0, self._shell_header_status_label.winfo_reqwidth())
        badges_req = max(0, badges.winfo_reqwidth())
        # Keep the search usable even at large font profiles. It may shrink, but never disappear.
        min_search = 170 if available < 1180 else 220
        fixed_core = identity_req + utility_req + min_search + 30
        spare = max(0, available - fixed_core)

        # Runtime badges are useful but duplicated in the footer. Status prose is the first thing
        # to disappear because it is fully redundant with sidebar/footer status.
        show_badges = badges_req > 0 and spare >= badges_req + 28
        spare_after_badges = spare - (badges_req + 8 if show_badges else 0)
        show_status = status_req > 0 and spare_after_badges >= status_req + 52

        layout_key = (show_badges, show_status, min_search)
        if getattr(self, "_shell_header_layout_key", None) != layout_key:
            self._shell_header_layout_key = layout_key
            if show_status:
                if not self._shell_header_status_label.winfo_manager():
                    self._shell_header_status_label.pack(side="left", padx=(0, 7), before=self._shell_header_help_button)
            else:
                self._shell_header_status_label.pack_forget()
            for widget in (identity, search_host, badges, controls):
                widget.grid_forget()
            for column in range(4):
                header.columnconfigure(column, weight=0, minsize=0)
            header.columnconfigure(1, weight=1, minsize=min_search)
            identity.grid(row=0, column=0, sticky="w", padx=(0, 10))
            search_host.grid(row=0, column=1, sticky="ew", padx=(0, 10))
            if show_badges:
                badges.grid(row=0, column=2, sticky="e", padx=(0, 8))
            controls.grid(row=0, column=3, sticky="e")

    def _refresh_shell_runtime_badges(self) -> None:
        if not hasattr(self, "_shell_ffmpeg_badge"):
            return
        metrics = collect_system_metrics()
        self._shell_ffmpeg_badge.set(f"FFmpeg {metrics.ffmpeg}")
        self._shell_gpu_badge.set(f"GPU {metrics.gpu_acceleration}")
        self._shell_cache_badge.set(f"Cache {format_bytes(metrics.cache_bytes)}")
        self._request_shell_header_layout()

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
            ("media", "Medien", 1, "Öffnen  →"),
            ("queue", "Queue", 4, "Öffnen  →"),
            ("effects", "Effekte", 3, "Öffnen  →"),
            ("scheduler", "Startzeituhr", None, "Planen  →"),
        )
        for key, title, page_index, action_label in cards:
            card = ttk.Frame(row, style=f"ShellKpi{key.title()}.TFrame", padding=(10, 7))
            self._shell_kpi_cards.append(card)
            ttk.Label(card, text=title, style="ShellKpiHint.TLabel").pack(anchor="w")
            ttk.Label(
                card,
                textvariable=self._shell_kpi_value_vars[key],
                style="ShellKpi.TLabel",
            ).pack(anchor="w", pady=(1, 0))
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
            status.pack(anchor="w", pady=(2, 2))
            self._shell_kpi_status_labels[key] = status
            button = ttk.Button(
                card,
                text=action_label,
                style="ShellKpiLink.TButton",
                command=(
                    (lambda index=page_index: self._select_shell_page(index))
                    if page_index is not None
                    else self._open_scheduler_dialog
                ),
            )
            button.pack(fill="x")
            self._shell_kpi_buttons[key] = button
            card.bind("<Configure>", self._update_shell_kpi_wraplengths, add="+")

        row.bind("<Configure>", self._layout_shell_kpis, add="+")
        self.root.after_idle(lambda: self._layout_shell_kpis(width=row.winfo_width()))
        self._refresh_kpi_cards()
        self._refresh_shell_runtime_badges()
        self._shell_kpi_poll_id = self.root.after(2000, self._poll_shell_kpis)

    def _layout_shell_kpis(self, event=None, *, width: int | None = None) -> None:
        if not getattr(self, "_shell_kpi_cards", None):
            return
        available = int(width if width is not None else getattr(event, "width", 0))
        if available >= 880:
            columns = 4
        elif available >= 520:
            columns = 2
        else:
            columns = 1
        row = self._shell_kpi_row
        if getattr(self, "_shell_kpi_layout_columns", None) == columns:
            self._update_shell_kpi_wraplengths()
            return
        self._shell_kpi_layout_columns = columns
        for column in range(4):
            active = column < columns
            row.columnconfigure(column, weight=1 if active else 0, uniform="kpi" if active else "", minsize=0)
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
                target = max(130, label.master.winfo_width() - 26)
                current = int(float(label.cget("wraplength") or 0))
                if current != target:
                    label.configure(wraplength=target)
            except (TclError, ValueError):
                return

    def _refresh_kpi_cards(self) -> None:
        if not hasattr(self, "_shell_kpi_value_vars"):
            return
        audios = tuple(getattr(self, "audios", ()))
        media = tuple(getattr(self, "media", ()))
        paths = audios + media
        missing_sources = sum(1 for path in paths if not path.is_file())
        image_suffixes = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}
        video_suffixes = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v"}
        image_count = sum(1 for path in media if path.suffix.lower() in image_suffixes)
        video_count = sum(1 for path in media if path.suffix.lower() in video_suffixes)
        last_results = tuple(getattr(self, "last_results", ()))
        failed_jobs = sum(
            1 for result in last_results if not bool(getattr(result, "success", False))
        )
        active_tasks = self.tasks.active_names() if hasattr(self, "tasks") else ()
        snapshots = build_kpi_snapshots(
            audio_count=len(audios),
            media_count=len(media),
            image_count=image_count,
            video_count=video_count,
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
            self._refresh_shell_runtime_badges()
            if hasattr(self, "_refresh_canonical_dashboard"):
                self._refresh_canonical_dashboard()
            self._shell_kpi_poll_id = self.root.after(2000, self._poll_shell_kpis)
        except TclError:
            return

    def _build_shell_actions(self, parent) -> None:
        bar = ttk.Frame(parent, style="ShellHeader.TFrame", padding=(6, 4))
        bar.grid(row=2, column=0, sticky="ew", pady=(0, 7))
        actions: tuple[tuple[str, str, Callable[[], object], str, str], ...] = (
            ("new", "Neuer Auftrag", self._new_project, "Accent.TButton", "normal"),
            ("import", "Medien importieren", self._add_media, "Ghost.TButton", "normal"),
            ("effects", "Effekte prüfen", self._open_settings, "Ghost.TButton", "normal"),
            ("scheduler", "Startzeit", self._open_scheduler_dialog, "Ghost.TButton", "normal"),
            ("start", "Queue starten", self._start, "Success.TButton", "normal"),
            ("backup", "Sicherungen", self._open_backup_manager, "Ghost.TButton", "normal"),
        )
        self._shell_action_buttons = [
            ttk.Button(
                bar,
                text=label,
                image=load_ui_icon(self, icon_name, size=20),
                compound="left",
                command=command,
                style=style,
                state=state,
            )
            for icon_name, label, command, style, state in actions
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
        if getattr(self, "_shell_action_layout_columns", None) == columns:
            return
        self._shell_action_layout_columns = columns
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
