from __future__ import annotations

from pathlib import Path

from tkinter import Canvas, StringVar, TclError, ttk

from .icon_assets import load_ui_icon
from .theme import COLORS, best_text_color, safe_text_color


HOME_GOLD = "#C79A16"
HOME_GOLD_DARK = "#4A3A08"
HOME_MAGENTA = "#D54C98"
HOME_MAGENTA_DARK = "#4A2038"
HOME_GREEN = "#7FC94B"
HOME_GREEN_DARK = "#23451D"
HOME_BLUE = "#45B9E8"
HOME_BLUE_DARK = "#163D52"
HOME_BG = "#070D0B"
HOME_PANEL = "#0E1717"
HOME_PANEL_ALT = "#111B1B"
HOME_MUTED = "#9DA6A3"
HOME_TEXT = "#F3F2E9"


class ProjectHomeDashboardMixin:
    """First-step project home matching the approved four-zone dashboard mockup.

    The existing canonical workspace remains fully built underneath. The home surface is an
    intentionally sparse launch layer: only general status/settings are active; the four lower
    content areas remain explicit placeholders for iterative expansion.
    """

    def _build_ui(self) -> None:
        super()._build_ui()
        self._build_project_home_overlay()

    def _configure_project_home_styles(self) -> None:
        style = ttk.Style(self.root)
        scale = int(self.global_font_scale.get()) if hasattr(self, "global_font_scale") else 105
        factor = max(0.85, min(1.35, scale / 105.0))
        base = max(10, round(11 * factor))
        section = max(13, round(14 * factor))
        title = max(22, round(28 * factor))

        style.configure("ProjectHome.TFrame", background=HOME_BG)
        style.configure("ProjectHomePanel.TFrame", background=HOME_PANEL, relief="solid", borderwidth=1, bordercolor=HOME_GOLD)
        style.configure("ProjectHomePanelAlt.TFrame", background=HOME_PANEL_ALT, relief="solid", borderwidth=1, bordercolor=HOME_GOLD)
        style.configure("ProjectHomePanelBody.TFrame", background=HOME_PANEL, relief="flat", borderwidth=0)
        style.configure("ProjectHomePlaceholder.TFrame", background=HOME_PANEL, relief="solid", borderwidth=1, bordercolor=HOME_GOLD_DARK)
        style.configure("ProjectHomeHeader.TFrame", background=HOME_BG)
        style.configure("ProjectHomeFooter.TFrame", background="#09100F", relief="solid", borderwidth=1, bordercolor=HOME_GOLD_DARK)

        style.configure("ProjectHomeTitle.TLabel", background=HOME_BG, foreground=HOME_TEXT, font=("DejaVu Sans", title, "bold"))
        style.configure("ProjectHomeSubtitle.TLabel", background=HOME_BG, foreground=HOME_MUTED, font=("DejaVu Sans", max(11, round(13 * factor))))
        style.configure("ProjectHomeSection.TLabel", background=HOME_PANEL, foreground=HOME_TEXT, font=("DejaVu Sans", section, "bold"))
        style.configure("ProjectHomePanelText.TLabel", background=HOME_PANEL, foreground=HOME_TEXT, font=("DejaVu Sans", base))
        style.configure("ProjectHomeStatus.TLabel", background=HOME_PANEL, foreground=HOME_GREEN, font=("DejaVu Sans", base, "bold"))
        style.configure("ProjectHomeTip.TLabel", background=HOME_PANEL, foreground=HOME_TEXT, font=("DejaVu Sans", base))
        style.configure("ProjectHomePlaceholderTitle.TLabel", background=HOME_PANEL, foreground=HOME_TEXT, font=("DejaVu Sans", section, "bold"))
        style.configure("ProjectHomePlaceholderBody.TLabel", background=HOME_PANEL, foreground=HOME_MUTED, font=("DejaVu Sans", base))
        style.configure("ProjectHomeFooter.TLabel", background="#09100F", foreground=HOME_MUTED, font=("DejaVu Sans", base))

        tile_specs = (
            ("ProjectHomeGold.TButton", HOME_GOLD_DARK, HOME_GOLD),
            ("ProjectHomeMagenta.TButton", HOME_MAGENTA_DARK, HOME_MAGENTA),
            ("ProjectHomeGreen.TButton", HOME_GREEN_DARK, HOME_GREEN),
            ("ProjectHomeBlue.TButton", HOME_BLUE_DARK, HOME_BLUE),
        )
        for name, background, border in tile_specs:
            style.configure(
                name,
                background=background,
                foreground=best_text_color(background),
                padding=(12, max(12, round(15 * factor))),
                font=("DejaVu Sans", max(12, round(13 * factor)), "bold"),
                borderwidth=2,
                bordercolor=border,
                relief="solid",
                anchor="center",
            )
            style.map(name, background=[("active", border)], foreground=[("active", best_text_color(border))])

        style.configure(
            "ProjectHomeAction.TButton",
            background="#171C16",
            foreground=HOME_TEXT,
            padding=(12, max(8, round(10 * factor))),
            font=("DejaVu Sans", base, "bold"),
            borderwidth=1,
            bordercolor=HOME_GOLD,
            relief="solid",
        )
        style.map("ProjectHomeAction.TButton", background=[("active", HOME_GOLD_DARK)])
        style.configure(
            "ProjectHomeHelp.TButton",
            background="#171C16",
            foreground=HOME_TEXT,
            padding=(10, 7),
            borderwidth=1,
            bordercolor=HOME_GOLD,
        )
        style.configure(
            "ProjectHomeFont.TButton",
            background="#111817",
            foreground=HOME_MUTED,
            padding=(7, 4),
            borderwidth=1,
            bordercolor="#35433C",
        )
        style.configure(
            "ProjectHomeFontActive.TButton",
            background=HOME_GREEN_DARK,
            foreground=safe_text_color(HOME_GREEN_DARK, HOME_GREEN),
            padding=(7, 4),
            borderwidth=1,
            bordercolor=HOME_GREEN,
        )

    def _build_project_home_overlay(self) -> None:
        self._configure_project_home_styles()
        shell = getattr(self, "_project_home_shell_host", None)
        if shell is None:
            shell = getattr(self, "_canonical_shell", None)
        if shell is None:
            return

        overlay = ttk.Frame(shell, style="ProjectHome.TFrame")
        overlay.grid(row=0, column=0, rowspan=2, columnspan=2, sticky="nsew")
        overlay.rowconfigure(0, weight=1)
        overlay.columnconfigure(0, weight=1)
        self._project_home_overlay = overlay

        canvas = Canvas(overlay, background=HOME_BG, highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(overlay, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self._project_home_scrollbar = scrollbar
        surface = ttk.Frame(canvas, style="ProjectHome.TFrame", padding=(18, 14, 18, 12))
        window_id = canvas.create_window((0, 0), window=surface, anchor="nw")
        self._project_home_canvas = canvas
        self._project_home_surface = surface

        def sync_surface(_event=None) -> None:
            try:
                bounds = canvas.bbox("all")
                canvas.configure(scrollregion=bounds)
                content_height = bounds[3] - bounds[1] if bounds else 0
                if content_height <= canvas.winfo_height() + 2:
                    scrollbar.grid_remove()
                elif not scrollbar.winfo_manager():
                    scrollbar.grid(row=0, column=1, sticky="ns")
            except TclError:
                return

        def fit_width(event) -> None:
            try:
                canvas.itemconfigure(window_id, width=max(1, event.width))
                self.root.after_idle(sync_surface)
            except TclError:
                return

        surface.bind("<Configure>", sync_surface, add="+")
        canvas.bind("<Configure>", fit_width, add="+")
        canvas.bind("<MouseWheel>", lambda event: canvas.yview_scroll(-1 if event.delta > 0 else 1, "units"), add="+")
        canvas.bind("<Button-4>", lambda _event: canvas.yview_scroll(-2, "units"), add="+")
        canvas.bind("<Button-5>", lambda _event: canvas.yview_scroll(2, "units"), add="+")

        self._build_project_home_header(surface)
        self._build_project_home_tiles(surface)
        self._build_project_home_information(surface)
        self._build_project_home_placeholders(surface)
        self._build_project_home_actions(surface)
        self._build_project_home_footer(surface)
        self._refresh_project_home_status()
        overlay.tkraise()
        self._project_home_visible = True

        if hasattr(self, "global_font_scale"):
            self.global_font_scale.trace_add("write", lambda *_args: self.root.after_idle(self._configure_project_home_styles))

    def _build_project_home_header(self, parent) -> None:
        header = ttk.Frame(parent, style="ProjectHomeHeader.TFrame")
        header.pack(fill="x", pady=(0, 12))
        icon = load_ui_icon(self, "start", size=40)
        if icon is not None:
            ttk.Label(header, image=icon, style="ProjectHomeTitle.TLabel").pack(side="left", padx=(4, 12))
        identity = ttk.Frame(header, style="ProjectHomeHeader.TFrame")
        identity.pack(side="left", fill="x", expand=True)
        ttk.Label(identity, text="PROVOWARE VIDEO AUTOMATION", style="ProjectHomeTitle.TLabel").pack(anchor="w")
        ttk.Label(identity, text="Schritt 1 – Projektstart & Grundkontext", style="ProjectHomeSubtitle.TLabel").pack(anchor="w", pady=(1, 0))
        ttk.Button(header, text="?  Hilfe", style="ProjectHomeHelp.TButton", command=self._show_help_center).pack(side="right", padx=(10, 3))

    def _build_project_home_tiles(self, parent) -> None:
        row = ttk.Frame(parent, style="ProjectHome.TFrame")
        row.pack(fill="x", pady=(0, 12))
        for column in range(4):
            row.columnconfigure(column, weight=1, uniform="project-home-tiles")
        specs = (
            ("Projektbasis", "Name, Pfade, Struktur", "new", "ProjectHomeGold.TButton", self._open_project_basis),
            ("Medienquellen", "Audio, Bilder, Vorlagen", "media", "ProjectHomeMagenta.TButton", lambda: self._open_project_workspace(1)),
            ("Automationsregeln", "Abläufe, Logik, Trigger", "scheduler", "ProjectHomeGreen.TButton", self._open_scheduler_dialog),
            ("Render & Export", "Ausgabe, Profile, Ziele", "start", "ProjectHomeBlue.TButton", lambda: self._open_project_workspace(4)),
        )
        for column, (title, subtitle, icon_name, style, command) in enumerate(specs):
            button = ttk.Button(
                row,
                text=f"{title}\n{subtitle}",
                image=load_ui_icon(self, icon_name, size=40),
                compound="top",
                style=style,
                command=command,
            )
            button.grid(row=0, column=column, sticky="nsew", padx=5)

    def _build_project_home_information(self, parent) -> None:
        row = ttk.Frame(parent, style="ProjectHome.TFrame")
        row.pack(fill="x", pady=(0, 12))
        row.columnconfigure(0, weight=6, uniform="project-home-info")
        row.columnconfigure(1, weight=5, uniform="project-home-info")

        dashboard = ttk.Frame(row, style="ProjectHomePanel.TFrame", padding=(18, 14))
        dashboard.grid(row=0, column=0, sticky="nsew", padx=(5, 6))
        dashboard.columnconfigure(0, weight=1)
        ttk.Label(dashboard, text="Infodashboard", style="ProjectHomeSection.TLabel").grid(row=0, column=0, sticky="w", columnspan=2)
        self._project_home_project_status = StringVar(value="Initial")
        self._project_home_ui_mode = StringVar(value="Standard")
        self._project_home_automation_status = StringVar(value="Vorbereitung")
        self._project_home_scheduler_status = StringVar(value="Inaktiv")
        statuses = (
            ("Projektstatus", self._project_home_project_status),
            ("UI-Modus", self._project_home_ui_mode),
            ("Automationsstatus", self._project_home_automation_status),
            ("Scheduler", self._project_home_scheduler_status),
        )
        for index, (label, value) in enumerate(statuses, start=1):
            line = ttk.Frame(dashboard, style="ProjectHomePanelBody.TFrame")
            line.grid(row=index, column=0, sticky="ew", pady=4)
            ttk.Label(line, text="●", style="ProjectHomeStatus.TLabel").pack(side="left", padx=(0, 8))
            ttk.Label(line, text=f"{label}:", style="ProjectHomePanelText.TLabel").pack(side="left")
            ttk.Label(line, textvariable=value, style="ProjectHomeStatus.TLabel").pack(side="left", padx=(8, 0))
        icon = load_ui_icon(self, "dashboard", size=40)
        ttk.Label(
            dashboard,
            image=icon,
            text="▥" if icon is None else "",
            style="ProjectHomeStatus.TLabel",
        ).grid(row=1, column=1, rowspan=4, sticky="e", padx=(18, 10))

        tips = ttk.Frame(row, style="ProjectHomePanel.TFrame", padding=(18, 14))
        tips.grid(row=0, column=1, sticky="nsew", padx=(6, 5))
        ttk.Label(tips, text="Tipps", style="ProjectHomeSection.TLabel").pack(anchor="w")
        for message in (
            "Zuerst Projektbasis festlegen.",
            "Später Module schrittweise ergänzen.",
            "Leere Felder sind für Ausbau reserviert.",
        ):
            line = ttk.Frame(tips, style="ProjectHomePanelBody.TFrame")
            line.pack(fill="x", pady=6)
            ttk.Label(line, text="●", style="ProjectHomeStatus.TLabel").pack(side="left", padx=(0, 9))
            ttk.Label(line, text=message, style="ProjectHomeTip.TLabel", wraplength=430, justify="left").pack(side="left", fill="x", expand=True)

    def _build_project_home_placeholders(self, parent) -> None:
        row = ttk.Frame(parent, style="ProjectHome.TFrame")
        row.pack(fill="x", pady=(0, 12))
        for column in range(4):
            row.columnconfigure(column, weight=1, uniform="project-home-placeholders")

        self._build_project_home_sources_overview(row, 0)
        self._build_project_home_workflow_overview(row, 1)
        for column, (title, icon_name) in enumerate((
            ("Render-Profile", "preview"),
            ("Historie / Logs", "diagnostics"),
        ), start=2):
            if title == "Render-Profile":
                self._build_project_home_render_overview(row, column)
                continue
            card = ttk.Frame(row, style="ProjectHomePlaceholder.TFrame", padding=(14, 13))
            card.grid(row=0, column=column, sticky="nsew", padx=5)
            ttk.Label(card, text=title, style="ProjectHomePlaceholderTitle.TLabel").pack(anchor="w")
            icon = load_ui_icon(self, icon_name, size=40)
            ttk.Label(
                card,
                image=icon,
                text="○" if icon is None else "",
                style="ProjectHomePlaceholderBody.TLabel",
            ).pack(pady=(18, 10))
            ttk.Label(card, text="Noch leer", style="ProjectHomePanelText.TLabel").pack()
            ttk.Label(card, text="Für spätere Inhalte", style="ProjectHomePlaceholderBody.TLabel").pack(pady=(3, 7))

    def _build_project_home_sources_overview(self, parent, column: int) -> None:
        card = ttk.Frame(parent, style="ProjectHomePanel.TFrame", padding=(14, 13))
        card.grid(row=0, column=column, sticky="nsew", padx=5)
        ttk.Label(card, text="Quellenübersicht", style="ProjectHomePlaceholderTitle.TLabel").pack(anchor="w")
        self._project_home_sources_total = StringVar(value="0 Quellen")
        self._project_home_sources_audio = StringVar(value="Audio: 0")
        self._project_home_sources_media = StringVar(value="Bilder / Videos: 0")
        self._project_home_sources_missing = StringVar(value="Nicht verfügbar: 0")
        icon = load_ui_icon(self, "media", size=34)
        ttk.Label(
            card,
            image=icon,
            text="◉" if icon is None else "",
            style="ProjectHomeStatus.TLabel",
        ).pack(pady=(10, 5))
        ttk.Label(card, textvariable=self._project_home_sources_total, style="ProjectHomeSection.TLabel").pack()
        ttk.Label(card, textvariable=self._project_home_sources_audio, style="ProjectHomePlaceholderBody.TLabel").pack(pady=(6, 0))
        ttk.Label(card, textvariable=self._project_home_sources_media, style="ProjectHomePlaceholderBody.TLabel").pack(pady=(2, 0))
        ttk.Label(card, textvariable=self._project_home_sources_missing, style="ProjectHomePlaceholderBody.TLabel").pack(pady=(2, 8))
        ttk.Button(
            card,
            text="Medienbibliothek öffnen",
            style="ProjectHomeAction.TButton",
            command=lambda: self._open_project_workspace(1),
        ).pack(fill="x", pady=(5, 0))

    def _refresh_project_home_sources(self) -> None:
        if not hasattr(self, "_project_home_sources_total"):
            return
        audios = tuple(getattr(self, "audios", ()) or ())
        media = tuple(getattr(self, "media", ()) or ())
        sources = audios + media
        missing = 0
        for source in sources:
            try:
                if not Path(source).exists():
                    missing += 1
            except (TypeError, OSError):
                missing += 1
        total = len(sources)
        self._project_home_sources_total.set(f"{total} Quelle" if total == 1 else f"{total} Quellen")
        self._project_home_sources_audio.set(f"Audio: {len(audios)}")
        self._project_home_sources_media.set(f"Bilder / Videos: {len(media)}")
        self._project_home_sources_missing.set(f"Nicht verfügbar: {missing}")

    def _build_project_home_workflow_overview(self, parent, column: int) -> None:
        card = ttk.Frame(parent, style="ProjectHomePanel.TFrame", padding=(14, 13))
        card.grid(row=0, column=column, sticky="nsew", padx=5)
        ttk.Label(card, text="Workflow-Module", style="ProjectHomePlaceholderTitle.TLabel").pack(anchor="w")
        self._project_home_workflow_mode = StringVar(value="Schnellmodus: —")
        self._project_home_workflow_effect = StringVar(value="Effekt: —")
        self._project_home_workflow_transition = StringVar(value="Übergang: —")
        self._project_home_workflow_jobs = StringVar(value="0 Aufträge vorbereitet")
        icon = load_ui_icon(self, "effects", size=34)
        ttk.Label(
            card,
            image=icon,
            text="◆" if icon is None else "",
            style="ProjectHomeStatus.TLabel",
        ).pack(pady=(10, 5))
        ttk.Label(card, textvariable=self._project_home_workflow_jobs, style="ProjectHomeSection.TLabel").pack()
        ttk.Label(card, textvariable=self._project_home_workflow_mode, style="ProjectHomePlaceholderBody.TLabel").pack(pady=(6, 0))
        ttk.Label(card, textvariable=self._project_home_workflow_effect, style="ProjectHomePlaceholderBody.TLabel").pack(pady=(2, 0))
        ttk.Label(card, textvariable=self._project_home_workflow_transition, style="ProjectHomePlaceholderBody.TLabel").pack(pady=(2, 8))
        ttk.Button(
            card,
            text="Workflow & Queue öffnen",
            style="ProjectHomeAction.TButton",
            command=lambda: self._open_project_workspace(4),
        ).pack(fill="x", pady=(5, 0))

    def _refresh_project_home_workflow(self) -> None:
        if not hasattr(self, "_project_home_workflow_mode"):
            return

        def value_of(name: str, fallback: str = "—") -> str:
            variable = getattr(self, name, None)
            if variable is None:
                return fallback
            try:
                value = str(variable.get() or "").strip()
            except (AttributeError, TclError):
                return fallback
            return value or fallback

        jobs = tuple(getattr(self, "jobs", ()) or ())
        count = len(jobs)
        self._project_home_workflow_jobs.set(
            "1 Auftrag vorbereitet" if count == 1 else f"{count} Aufträge vorbereitet"
        )
        self._project_home_workflow_mode.set(f"Schnellmodus: {value_of('quick_mode')}")
        self._project_home_workflow_effect.set(f"Effekt: {value_of('visual_effect')}")
        self._project_home_workflow_transition.set(f"Übergang: {value_of('transition')}")

    def _build_project_home_render_overview(self, parent, column: int) -> None:
        card = ttk.Frame(parent, style="ProjectHomePanel.TFrame", padding=(14, 13))
        card.grid(row=0, column=column, sticky="nsew", padx=5)
        ttk.Label(card, text="Render-Profile", style="ProjectHomePlaceholderTitle.TLabel").pack(anchor="w")
        self._project_home_render_resolution = StringVar(value="Auflösung: —")
        self._project_home_render_codec = StringVar(value="Codec: —")
        self._project_home_render_profile = StringVar(value="Profil: —")
        self._project_home_render_target = StringVar(value="Ziel: —")
        icon = load_ui_icon(self, "preview", size=34)
        ttk.Label(
            card,
            image=icon,
            text="▶" if icon is None else "",
            style="ProjectHomeStatus.TLabel",
        ).pack(pady=(10, 5))
        ttk.Label(card, textvariable=self._project_home_render_profile, style="ProjectHomeSection.TLabel").pack()
        ttk.Label(card, textvariable=self._project_home_render_resolution, style="ProjectHomePlaceholderBody.TLabel").pack(pady=(6, 0))
        ttk.Label(card, textvariable=self._project_home_render_codec, style="ProjectHomePlaceholderBody.TLabel").pack(pady=(2, 0))
        ttk.Label(card, textvariable=self._project_home_render_target, style="ProjectHomePlaceholderBody.TLabel").pack(pady=(2, 8))
        ttk.Button(
            card,
            text="Render & Export öffnen",
            style="ProjectHomeAction.TButton",
            command=lambda: self._open_project_workspace(4),
        ).pack(fill="x", pady=(5, 0))

    def _refresh_project_home_render(self) -> None:
        if not hasattr(self, "_project_home_render_resolution"):
            return

        def value_of(name: str, fallback: str = "—") -> str:
            variable = getattr(self, name, None)
            if variable is None:
                return fallback
            try:
                value = str(variable.get() or "").strip()
            except (AttributeError, TclError):
                return fallback
            return value or fallback

        output_value = value_of("output_dir")
        target = output_value
        if output_value != "—":
            try:
                output_path = Path(output_value).expanduser()
                target = output_path.name or str(output_path)
            except (TypeError, OSError):
                target = output_value

        self._project_home_render_resolution.set(f"Auflösung: {value_of('resolution')}")
        self._project_home_render_codec.set(f"Codec: {value_of('codec')}")
        self._project_home_render_profile.set(f"Profil: {value_of('profile')}")
        self._project_home_render_target.set(f"Ziel: {target}")

    def _build_project_home_actions(self, parent) -> None:
        row = ttk.Frame(parent, style="ProjectHome.TFrame")
        row.pack(fill="x", pady=(0, 12))
        for column in range(4):
            row.columnconfigure(column, weight=1, uniform="project-home-actions")
        specs = (
            ("Allgemeine Einstellungen", "settings", self._open_general_settings),
            ("Projektregeln", "effects", self._open_project_rules),
            ("Benachrichtigungen", "diagnostics", self._open_notification_settings),
            ("Systempfade", "new", self._open_system_paths),
        )
        for column, (label, icon_name, command) in enumerate(specs):
            ttk.Button(
                row,
                text=label,
                image=load_ui_icon(self, icon_name, size=20),
                compound="left",
                style="ProjectHomeAction.TButton",
                command=command,
            ).grid(row=0, column=column, sticky="ew", padx=5)

    def _build_project_home_footer(self, parent) -> None:
        footer = ttk.Frame(parent, style="ProjectHomeFooter.TFrame", padding=(12, 7))
        footer.pack(fill="x", pady=(0, 2))
        ttk.Label(footer, text="Klar. Robust. Automatisiert.", style="ProjectHomeFooter.TLabel").pack(side="left")
        controls = ttk.Frame(footer, style="ProjectHomeFooter.TFrame")
        controls.pack(side="right")
        ttk.Label(controls, text="Schriftgröße Groß", style="ProjectHomeFooter.TLabel").pack(side="left", padx=(0, 8))
        for label, value in (("A", 90), ("A", 105), ("A", 125)):
            active = abs(int(self.global_font_scale.get()) - value) <= 5
            ttk.Button(
                controls,
                text=label,
                width=3,
                style="ProjectHomeFontActive.TButton" if active else "ProjectHomeFont.TButton",
                command=lambda selected=value: self._set_project_home_zoom(selected),
            ).pack(side="left", padx=2)

    def _set_project_home_zoom(self, value: int) -> None:
        self._set_global_zoom(value)
        self._configure_project_home_styles()

    def _refresh_project_home_status(self) -> None:
        if not hasattr(self, "_project_home_project_status"):
            return
        media_count = len(getattr(self, "audios", ())) + len(getattr(self, "media", ()))
        self._project_home_project_status.set("Bereit" if media_count else "Initial")
        self._project_home_ui_mode.set("Standard")
        self._project_home_automation_status.set("Bereit" if getattr(self, "jobs", ()) else "Vorbereitung")
        active = None
        if hasattr(self, "_active_scheduler_record"):
            try:
                active = self._active_scheduler_record()
            except Exception:
                active = None
        self._project_home_scheduler_status.set("Aktiv" if active is not None else "Inaktiv")
        self._refresh_project_home_sources()
        self._refresh_project_home_workflow()
        self._refresh_project_home_render()

    def _show_project_home(self) -> None:
        overlay = getattr(self, "_project_home_overlay", None)
        if overlay is None:
            return
        self._refresh_project_home_status()
        overlay.grid()
        overlay.tkraise()
        self._project_home_visible = True

    def _hide_project_home(self) -> None:
        overlay = getattr(self, "_project_home_overlay", None)
        if overlay is not None:
            overlay.grid_remove()
        self._project_home_visible = False

    def _open_project_workspace(self, page_index: int) -> None:
        self._hide_project_home()
        self.main_notebook.select(page_index)
        self._sync_shell_navigation(page_index)

    def _open_project_basis(self) -> None:
        self._hide_project_home()
        self.main_notebook.select(0)
        self._sync_shell_navigation(0)
        if hasattr(self, "_show_dashboard_view"):
            self._show_dashboard_view("assistant")

    def _open_general_settings(self) -> None:
        self._hide_project_home()
        self._open_settings()

    def _open_project_rules(self) -> None:
        self._hide_project_home()
        self._open_scheduler_dialog()

    def _open_notification_settings(self) -> None:
        self._hide_project_home()
        self._open_settings()
        if hasattr(self, "guidance_text"):
            self.guidance_text.set("Benachrichtigungen werden schrittweise ergänzt. Allgemeine Einstellungen sind geöffnet.")

    def _open_system_paths(self) -> None:
        self._hide_project_home()
        self._open_settings()
        if hasattr(self, "guidance_text"):
            self.guidance_text.set("System- und Ausgabeordner können in den Einstellungen geprüft werden.")
