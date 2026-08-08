from __future__ import annotations

from tkinter import StringVar, TclError, ttk

from .canonical_shell_contract import (
    CANONICAL_THEME_LABELS,
    SHELL_NAVIGATION,
    SIDEBAR_WIDTH,
)
from .startup_readiness import StartupStep, build_startup_readiness
from .theme import COLORS, best_text_color, safe_text_color


class CanonicalShellWorkspaceMixin:
    """Construct and coordinate the shell without owning dashboard internals."""

    _START_KEYS = ("project", "media", "effects", "output", "pairing", "render")

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
        content.rowconfigure(4, weight=1)

        self._build_shell_sidebar(sidebar)
        self._build_shell_header(content)
        self._build_shell_kpis(content)
        self._build_shell_actions(content)
        self._build_shell_start_check(content)
        self._build_shell_workspace(content)

        footer_host = ttk.Frame(shell, style="Shell.TFrame")
        footer_host.grid(row=1, column=0, columnspan=2, sticky="ew")
        self._build_canonical_status_bar(footer_host)
        self._restore_shell_selection()

    def _build_shell_workspace(self, parent) -> None:
        workspace = ttk.Frame(parent, style="Shell.TFrame")
        workspace.grid(row=4, column=0, sticky="nsew")
        workspace.rowconfigure(0, weight=1)
        workspace.columnconfigure(0, weight=1)

        self.main_notebook = ttk.Notebook(workspace, style="Shell.TNotebook")
        self.main_notebook.grid(row=0, column=0, sticky="nsew")
        self.main_notebook.bind(
            "<<NotebookTabChanged>>",
            self._on_main_tab_changed,
            add="+",
        )
        self.main_notebook.bind(
            "<<NotebookTabChanged>>",
            self._on_shell_tab_changed,
            add="+",
        )

        pages = [
            ttk.Frame(self.main_notebook, style="Card.TFrame", padding=6)
            for _ in range(6)
        ]
        for page, label in zip(
            pages,
            ("Dashboard", "Medien", "Vorschau", "Effekte", "Queue", "Hilfe"),
        ):
            self.main_notebook.add(page, text=label)

        self._build_dashboard_page(pages[0])
        self._build_media_page(pages[1])
        self._build_preview_page(pages[2])
        self._build_modes_page(pages[3])
        self._build_production_page(pages[4])
        self._build_canonical_help_page(pages[5])

    def _configure_start_check_styles(self) -> None:
        style = ttk.Style(self.root)
        scale = int(self.global_font_scale.get()) if hasattr(self, "global_font_scale") else 105
        factor = max(0.85, min(1.35, scale / 105.0))
        title_font = max(11, round(12 * factor))
        status_font = max(9, round(10 * factor))
        action_font = max(10, round(11 * factor))
        panel = COLORS["panel"]
        panel2 = COLORS["panel2"]
        style.configure(
            "StartCheck.TFrame",
            background=panel,
            relief="solid",
            borderwidth=2,
            bordercolor=COLORS["attention"],
        )
        style.configure(
            "StartCheckTitle.TLabel",
            background=panel,
            foreground=safe_text_color(panel, COLORS["text"]),
            font=("DejaVu Sans", title_font, "bold"),
        )
        self._configure_start_state_styles(style, panel2, status_font)
        action = COLORS["attention"]
        style.configure(
            "StartAction.TButton",
            background=action,
            foreground=best_text_color(action),
            padding=(14, 8),
            font=("DejaVu Sans", action_font, "bold"),
            borderwidth=1,
        )

    def _configure_start_state_styles(self, style, panel2: str, font_size: int) -> None:
        for name, color in (
            ("Ok", COLORS["success"]),
            ("Warning", COLORS["warning"]),
            ("Error", COLORS["danger"]),
            ("Idle", COLORS["disabled"]),
        ):
            style.configure(
                f"Start{name}.TFrame",
                background=panel2,
                relief="solid",
                borderwidth=2,
                bordercolor=color,
            )
            style.configure(
                f"Start{name}.TLabel",
                background=panel2,
                foreground=safe_text_color(panel2, color),
                font=("DejaVu Sans", font_size, "bold"),
            )
            style.configure(
                f"Start{name}Pill.TLabel",
                background=color,
                foreground=best_text_color(color),
                padding=(8, 4),
                font=("DejaVu Sans", font_size, "bold"),
            )

    def _build_shell_start_check(self, parent) -> None:
        self._configure_start_check_styles()
        card = ttk.Frame(parent, style="StartCheck.TFrame", padding=(10, 8))
        card.grid(row=3, column=0, sticky="ew", pady=(0, 9))
        card.columnconfigure(0, weight=1)
        self._shell_start_check = card
        self._build_start_check_header(card)
        self._build_start_check_steps(card)
        self._build_start_check_next_action(card)
        card.bind("<Configure>", self._layout_shell_start_check, add="+")
        self._refresh_shell_start_check()
        self._start_check_poll_id = self.root.after(1000, self._poll_shell_start_check)

    def _build_start_check_header(self, card) -> None:
        header = ttk.Frame(card, style="StartCheck.TFrame")
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(
            header,
            text="STARTRoutine / START-CHECK",
            style="StartCheckTitle.TLabel",
        ).grid(row=0, column=0, sticky="w")
        self._start_summary = StringVar(value="Prüfung wird aufgebaut")
        self._start_summary_label = ttk.Label(
            header,
            textvariable=self._start_summary,
            style="StartIdlePill.TLabel",
        )
        self._start_summary_label.grid(row=0, column=1, sticky="e", padx=(8, 0))

    def _build_start_check_steps(self, card) -> None:
        host = ttk.Frame(card, style="StartCheck.TFrame")
        host.grid(row=1, column=0, sticky="ew", pady=(7, 7))
        self._start_steps_host = host
        self._start_step_widgets = {}
        for index, key in enumerate(self._START_KEYS, start=1):
            frame = ttk.Frame(host, style="StartIdle.TFrame", padding=(8, 5))
            status = ttk.Label(frame, text="● PRÜFUNG", style="StartIdle.TLabel")
            status.pack(anchor="w")
            title = StringVar(value=f"{index}. Prüfung")
            ttk.Label(frame, textvariable=title, style="StartIdle.TLabel").pack(
                anchor="w", pady=(2, 0)
            )
            detail = StringVar(value="Wird geprüft")
            detail_label = ttk.Label(
                frame,
                textvariable=detail,
                style="StartIdle.TLabel",
                justify="left",
                wraplength=190,
            )
            detail_label.pack(anchor="w", fill="x", pady=(2, 0))
            self._start_step_widgets[key] = (frame, status, title, detail, detail_label)

    def _build_start_check_next_action(self, card) -> None:
        next_row = ttk.Frame(card, style="StartCheck.TFrame")
        next_row.grid(row=2, column=0, sticky="ew")
        next_row.columnconfigure(0, weight=1)
        self._start_next_action = StringVar(value="Nächster Schritt wird ermittelt")
        ttk.Label(next_row, text="NÄCHSTER SCHRITT", style="StartWarning.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            next_row,
            textvariable=self._start_next_action,
            style="StartCheckTitle.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(1, 0))
        self._start_next_button = ttk.Button(
            next_row,
            text="→ Aktion öffnen",
            style="StartAction.TButton",
            command=self._run_shell_next_action,
        )
        self._start_next_button.grid(row=0, column=1, rowspan=2, sticky="e", padx=(12, 0))

    def _layout_shell_start_check(self, event=None) -> None:
        width = max(1, int(getattr(event, "width", self._shell_start_check.winfo_width())))
        columns = 6 if width >= 720 else 3 if width >= 480 else 1
        for column in range(6):
            self._start_steps_host.columnconfigure(
                column, weight=1 if column < columns else 0, uniform="startcheck"
            )
        for index, key in enumerate(self._START_KEYS):
            frame = self._start_step_widgets[key][0]
            frame.grid_forget()
            frame.grid(
                row=index // columns,
                column=index % columns,
                sticky="nsew",
                padx=3,
                pady=3,
            )

    @staticmethod
    def _start_style(status: str) -> str:
        return {"ok": "Ok", "warning": "Warning", "error": "Error"}.get(status, "Idle")

    def _apply_start_step(self, index: int, step: StartupStep) -> None:
        frame, status, title, detail, detail_label = self._start_step_widgets[step.key]
        style = self._start_style(step.status)
        frame.configure(style=f"Start{style}.TFrame")
        status.configure(
            text={"ok": "● BEREIT", "warning": "● PRÜFEN", "error": "● BLOCKIERT"}[
                step.status
            ],
            style=f"Start{style}.TLabel",
        )
        title.set(f"{index}. {step.title}")
        detail.set(step.detail)
        detail_label.configure(style=f"Start{style}.TLabel")

    def _refresh_shell_start_check(self) -> None:
        if not hasattr(self, "_start_step_widgets"):
            return
        project_name = self.project_name.get().strip() if hasattr(self, "project_name") else ""
        model = build_startup_readiness(
            project_name=project_name,
            checks=self._preparation_checks(),
        )
        self._shell_start_readiness = model
        for index, step in enumerate(model.steps, start=1):
            self._apply_start_step(index, step)
        self._update_start_check_summary(model)

    def _update_start_check_summary(self, model) -> None:
        overall = self._start_style(model.overall_status)
        self._start_summary.set(
            f"{model.ready_count}/{len(model.steps)} bereit · "
            f"{model.warning_count} Warnung(en) · {model.error_count} Fehler"
        )
        self._start_summary_label.configure(style=f"Start{overall}Pill.TLabel")
        next_step = next(step for step in model.steps if step.key == model.next_step_key)
        if model.ready:
            self._start_next_action.set("Alle Startprüfungen grün · Queue kann gestartet werden")
            self._start_next_button.configure(text="▶ Queue starten")
            return
        self._start_next_action.set(f"{next_step.title}: {next_step.detail}")
        self._start_next_button.configure(text=f"→ {next_step.title} prüfen")

    def _run_shell_next_action(self) -> None:
        model = getattr(self, "_shell_start_readiness", None)
        if model is None:
            return
        if model.ready:
            self._start()
            return
        next_step = next(step for step in model.steps if step.key == model.next_step_key)
        self.guidance_text.set(f"Nächster Startpunkt: {next_step.title} · {next_step.detail}")
        self._focus_preparation_assistant()

    def _poll_shell_start_check(self) -> None:
        try:
            if not self.root.winfo_exists():
                return
            self._refresh_shell_start_check()
            self._start_check_poll_id = self.root.after(1000, self._poll_shell_start_check)
        except TclError:
            return

    def _refresh_theme_widgets(self) -> None:
        super()._refresh_theme_widgets()
        self._configure_start_check_styles()
        if hasattr(self, "_start_step_widgets"):
            self._refresh_shell_start_check()

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
            button.configure(
                style="ShellNavActive.TButton" if active else "ShellNav.TButton"
            )

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
                lambda *_args: self.root.after_idle(
                    self._refresh_canonical_dashboard
                ),
            )

    def _update_header_statistics(self) -> None:
        super()._update_header_statistics()
        if not hasattr(self, "shell_media_kpi"):
            return
        self._refresh_kpi_cards()
        self._refresh_canonical_dashboard()
        self._refresh_shell_start_check()
        if hasattr(self, "shell_theme_combo"):
            self.shell_theme_combo.set(
                CANONICAL_THEME_LABELS.get(self.theme_name.get(), "Midnight Blue")
            )
        if hasattr(self, "shell_font_combo"):
            self.shell_font_combo.set(
                self._font_profile_for_scale(self.global_font_scale.get())
            )
