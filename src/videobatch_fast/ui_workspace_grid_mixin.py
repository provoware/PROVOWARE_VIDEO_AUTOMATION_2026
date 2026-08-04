from __future__ import annotations

from pathlib import Path
from tkinter import Canvas, Menu, TclError, ttk

from .command_builder import PROFILES
from .preparation_assistant import build_preparation_checks, preparation_ready
from .quick_modes import QUICK_MODES, mode_spec
from .selection_summary import build_selection_summary
from .slideshow import SLIDESHOW_MODE_ALL_IMAGES, SLIDESHOW_MODE_PAIRWISE, TRANSITION_LABELS
from .text_resources import text
from .theme import COLORS, apply_theme, available_themes
from .ui_components import Tooltip
from .versioning import build_label
from .workflow_grid import DEFAULT_WORKFLOW_LAYOUT_MODE, ScrollableWorkflowGrid, normalize_workflow_layout_mode

LEGACY_WORKSPACE_CONTRACT_KEY = "ui.workspace_grid.mittiger_hauptarbeitsbereich_flexibles_22_raster"


class UiWorkspaceGridMixin:
    def _build_ui(self) -> None:
        self.workflow_grids: dict[str, ScrollableWorkflowGrid] = {}
        self._build_menu_bar()
        shell = ttk.Frame(self.root, padding=7)
        shell.pack(fill="both", expand=True)
        self._build_global_toolbar(shell)
        self.main_notebook = ttk.Notebook(shell)
        self.main_notebook.pack(fill="both", expand=True)
        self.main_notebook.bind("<<NotebookTabChanged>>", self._on_main_tab_changed, add="+")

        pages = []
        for key in ("start", "media", "preview", "modes", "production", "help"):
            page = ttk.Frame(self.main_notebook, style="Card.TFrame", padding=6)
            pages.append(page)
        labels = (
            text("ui.workspace_grid.start_laienmodus_einfach"),
            text("ui.tabs.media"),
            text("ui.tabs.preview"),
            text("ui.tabs.modes"),
            text("ui.tabs.production"),
            text("ui.tabs.help"),
        )
        for page, label in zip(pages, labels):
            self.main_notebook.add(page, text=label)

        self._build_start_page(pages[0])
        self._build_media_page(pages[1])
        self._build_preview_page(pages[2])
        self._build_modes_page(pages[3])
        self._build_production_page(pages[4])
        self._build_help_page(pages[5])
        self._build_status_bar(shell)

        self._main_tab_restore_in_progress = True
        try:
            selected = min(self.main_notebook.index("end") - 1, max(0, int(self.config.get("active_tab", 0))))
            self.main_notebook.select(selected)
        except Exception:
            pass
        finally:
            self._main_tab_restore_in_progress = False

    def _scrollable_dashboard_body(self, page) -> ScrollableWorkflowGrid:
        """Create the dynamic two-column body used by every main workflow tab."""
        mode = normalize_workflow_layout_mode(self.config.get("workflow_layout_mode", DEFAULT_WORKFLOW_LAYOUT_MODE))
        return ScrollableWorkflowGrid(page, background=COLORS["panel"], min_cell_height=285, layout_mode=mode)

    def _workflow_page(self, page, area: str) -> ScrollableWorkflowGrid:
        self._area_header(page, area, text(f"ui.tabs.{area}", area.title()), text(f"ui.tabs.{area}_subtitle", "2×2-Workflow · bei Bedarf nach unten scrollbar"))
        grid = self._scrollable_dashboard_body(page)
        self.workflow_grids[area] = grid
        self._register_area(area, page)
        return grid

    def _build_global_toolbar(self, parent) -> None:
        toolbar = ttk.Frame(parent, style="Header.TFrame", padding=(14, 11))
        toolbar.pack(fill="x", pady=(0, 7))

        identity = ttk.Frame(toolbar, style="Header.TFrame")
        identity.pack(fill="x")
        ttk.Label(identity, text=text("app.title"), style="HeaderTitle.TLabel").pack(side="left")
        ttk.Label(identity, text=f"Version {build_label()}", style="VersionBadge.TLabel").pack(side="left", padx=(10, 0))
        ttk.Label(identity, text=text("ui.rc22.header.brand"), style="HeaderHint.TLabel").pack(side="left", padx=(12, 0))

        controls = ttk.Frame(toolbar, style="Header.TFrame", padding=(0, 7, 0, 6))
        controls.pack(fill="x")
        theme_labels = available_themes()
        reverse = {label: key for key, label in theme_labels.items()}
        ttk.Label(controls, text=text("ui.rc22.header.theme"), style="Recommended.TLabel").pack(side="left", padx=(0, 7))
        theme_combo = ttk.Combobox(controls, values=list(reverse), state="readonly", width=18)
        theme_combo.set(theme_labels.get(self.theme_name.get(), theme_labels["neon_gravity"]))
        theme_combo.bind("<<ComboboxSelected>>", lambda _e: self._set_theme(reverse[theme_combo.get()]))
        theme_combo.pack(side="left", padx=(0, 18))
        ttk.Label(controls, text=text("ui.header.font_size", "Schriftgröße"), style="Recommended.TLabel").pack(side="left", padx=(0, 7))
        ttk.Button(controls, text=text("ui.rc22.header.font_smaller_symbol"), style="HeaderControl.TButton", width=4, command=lambda: self._set_global_zoom(self.global_font_scale.get() - 10)).pack(side="left")
        self.header_font_label = ttk.Label(controls, textvariable=self.global_font_scale, style="HeaderValue.TLabel", width=5, anchor="center")
        self.header_font_label.pack(side="left", padx=(5, 1))
        ttk.Label(controls, text=text("ui.rc22.header.percent_symbol"), style="HeaderValue.TLabel").pack(side="left", padx=(0, 5))
        ttk.Button(controls, text=text("ui.rc22.header.font_larger_symbol"), style="HeaderControl.TButton", width=4, command=lambda: self._set_global_zoom(self.global_font_scale.get() + 10)).pack(side="left")
        ttk.Button(controls, text=text("ui.rc22.header.font_reset"), style="HeaderControl.TButton", command=lambda: self._set_global_zoom(100)).pack(side="left", padx=(7, 0))
        ttk.Label(controls, text=text("ui.rc22.header.zoom_hint"), style="HeaderHint.TLabel").pack(side="left", padx=(16, 0))

        stats = ttk.Frame(toolbar, style="Header.TFrame", padding=(0, 5, 0, 6))
        stats.pack(fill="x")
        ttk.Label(stats, text=text("ui.header.current_selection"), style="Recommended.TLabel").pack(side="left", padx=(0, 8))
        ttk.Label(stats, textvariable=self.header_selection_stats, style="HeaderHint.TLabel", anchor="w", justify="left", wraplength=1500).pack(side="left", fill="x", expand=True)

        output_path = ttk.Frame(toolbar, style="Header.TFrame")
        output_path.pack(fill="x")
        ttk.Label(output_path, text=text("ui.rc22.header.output_folder"), style="Recommended.TLabel").pack(side="left", padx=(0, 8))
        self.header_output_entry = ttk.Entry(output_path, textvariable=self.output_dir)
        self.header_output_entry.pack(side="left", fill="x", expand=True)

        output_actions = ttk.Frame(toolbar, style="Header.TFrame", padding=(0, 6, 0, 0))
        output_actions.pack(fill="x")
        ttk.Button(output_actions, text=text("ui.rc22.action.choose_folder"), style="HeaderControl.TButton", command=lambda: self._choose_directory(self.output_dir)).pack(side="left")
        ttk.Button(output_actions, text=text("ui.rc22.action.open_folder"), style="HeaderControl.TButton", command=self._open_output).pack(side="left", padx=(6, 0))
        ttk.Button(output_actions, text=text("ui.rc22.action.create_safe_folder"), style="HeaderControl.TButton", command=self._create_output_folder_and_retry).pack(side="left", padx=(6, 0))
        ttk.Checkbutton(output_actions, text=text("ui.rc22.header.auto_open"), variable=self.auto_open_output).pack(side="left", padx=(12, 0))

    def _bind_header_statistics(self) -> None:
        for variable in (
            self.assignment_mode,
            self.slideshow_transition,
            self.slideshow_scene_sync,
            self.quick_mode,
            self.output_dir,
            self.output_mode,
        ):
            variable.trace_add("write", lambda *_args: self.root.after_idle(self._update_header_statistics))
        self.output_dir.trace_add("write", lambda *_args: self.root.after_idle(self._refresh_preparation_assistant))

    def _update_header_statistics(self) -> None:
        if not hasattr(self, "header_selection_stats"):
            return
        try:
            quick_label = mode_spec(self.quick_mode.get()).short_label
        except Exception:
            quick_label = "Automatik"
        summary = build_selection_summary(
            self.audios,
            self.media,
            job_count=len(self.jobs),
            assignment_mode=self.assignment_mode.get(),
            transition=self.slideshow_transition.get(),
            scene_sync=bool(self.slideshow_scene_sync.get()),
            quick_mode_label=quick_label,
        )
        self.header_selection_stats.set(f"{summary} · Ziel: {Path(self.output_dir.get()).name or self.output_dir.get()}")
        self._refresh_preparation_assistant()

    def _set_theme(self, name: str) -> None:
        if name not in available_themes():
            name = "neon_gravity"
        self.theme_name.set(name)
        self.config["theme"] = name
        apply_theme(self.root, self.global_font_scale.get(), name)
        self._refresh_theme_widgets()
        self._save_settings()
        self.guidance_text.set(f"Farbtheme aktiviert: {available_themes()[name]}.")

    def _refresh_theme_widgets(self) -> None:
        def visit(widget) -> None:
            try:
                if widget.winfo_class() == "Canvas":
                    widget.configure(background=COLORS["panel"], highlightbackground=COLORS["border"])
                elif widget.winfo_class() == "Listbox":
                    widget.configure(bg=COLORS["panel"], fg=COLORS["text"], selectbackground=COLORS["selection"])
                for child in widget.winfo_children():
                    visit(child)
            except TclError:
                return
        visit(self.root)
        for grid in getattr(self, "workflow_grids", {}).values():
            grid.canvas.configure(background=COLORS["panel"])
            grid.refresh()
        if hasattr(self, "_refresh_calendar"):
            self._refresh_calendar()
        if hasattr(self, "_draw_waveform"):
            try:
                self._draw_waveform()
            except Exception:
                pass

    def _build_menu_bar(self) -> None:
        menu = Menu(self.root)
        file_menu = Menu(menu, tearoff=False)
        file_menu.add_command(label=text("ui.menu.new_project"), command=self._new_project, accelerator="Ctrl+N")
        file_menu.add_command(label=text("ui.menu.open_project"), command=self._open_project_file, accelerator="Ctrl+O")
        file_menu.add_command(label=text("ui.menu.save_project"), command=self._save_project_dialog, accelerator="Ctrl+S")
        file_menu.add_separator()
        file_menu.add_command(label=text("ui.rc22.action.open_settings"), command=self._open_settings, accelerator="Ctrl+,")
        file_menu.add_command(label=text("ui.menu.exit"), command=self._close, accelerator="Ctrl+Q")
        menu.add_cascade(label=text("ui.menu.file"), menu=file_menu)

        media_menu = Menu(menu, tearoff=False)
        media_menu.add_command(label=text("ui.menu.add_audio"), command=self._add_audio, accelerator="Ctrl+Shift+A")
        media_menu.add_command(label=text("ui.menu.add_media"), command=self._add_media, accelerator="Ctrl+Shift+M")
        media_menu.add_command(label=text("ui.rc22.action.scan_large_folder"), command=self._add_media_folder)
        media_menu.add_separator()
        media_menu.add_command(label=text("ui.menu.clear_lists"), command=self._clear_lists)
        media_menu.add_command(label=text("ui.menu.open_downloads"), command=self._open_downloads)
        menu.add_cascade(label=text("ui.menu.media"), menu=media_menu)

        view_menu = Menu(menu, tearoff=False)
        for index, key in enumerate(("ui.workspace_grid.start_laienmodus_einfach", "ui.tabs.media", "ui.tabs.preview", "ui.tabs.modes", "ui.tabs.production", "ui.tabs.help")):
            view_menu.add_command(label=text(key), command=lambda selected=index: self.main_notebook.select(selected))
        view_menu.add_separator()
        view_menu.add_command(label=text("ui.menu.reset_zoom"), command=self._reset_all_area_zoom)
        layout_menu = Menu(view_menu, tearoff=False)
        layout_menu.add_command(label="Workflow: 2 Spalten", command=lambda: self._set_workflow_layout_mode("two_columns"))
        layout_menu.add_command(label="Workflow: 1 Spalte breit", command=lambda: self._set_workflow_layout_mode("wide"))
        layout_menu.add_command(label="Workflow: kompakt", command=lambda: self._set_workflow_layout_mode("compact"))
        view_menu.add_cascade(label="Workflow-Layout", menu=layout_menu)
        view_menu.add_command(label=text("ui.rc22.action.font_smaller"), command=lambda: self._set_global_zoom(self.global_font_scale.get() - 10), accelerator="Ctrl+-")
        view_menu.add_command(label=text("ui.rc22.action.font_larger"), command=lambda: self._set_global_zoom(self.global_font_scale.get() + 10), accelerator="Ctrl++")
        menu.add_cascade(label=text("ui.menu.view"), menu=view_menu)

        production_menu = Menu(menu, tearoff=False)
        production_menu.add_command(label=text("ui.rc22.action.check_preparation"), command=self._focus_preparation_assistant)
        production_menu.add_command(label=text("ui.menu.start"), command=self._start, accelerator="F9")
        production_menu.add_command(label=text("ui.menu.cancel"), command=self._cancel, accelerator="Esc")
        production_menu.add_command(label=text("ui.rc22.action.open_output"), command=self._open_output)
        menu.add_cascade(label=text("ui.menu.production"), menu=production_menu)

        tools_menu = Menu(menu, tearoff=False)
        tools_menu.add_command(label=text("ui.menu.system_test"), command=self._run_assurance)
        tools_menu.add_command(label=text("ui.menu.permissions"), command=self._show_permission_status)
        tools_menu.add_command(label=text("ui.menu.logs"), command=self._open_logs)
        menu.add_cascade(label=text("ui.menu.tools"), menu=tools_menu)

        help_menu = Menu(menu, tearoff=False)
        help_menu.add_command(label=text("ui.menu.help"), command=self._show_help_center, accelerator="F1")
        help_menu.add_command(label=text("ui.menu.about"), command=self._show_about)
        menu.add_cascade(label=text("ui.menu.help"), menu=help_menu)
        self.root.configure(menu=menu)
        self.root.bind_all("<Control-n>", lambda _e: self._new_project())
        self.root.bind_all("<Control-o>", lambda _e: self._open_project_file())
        self.root.bind_all("<Control-s>", lambda _e: self._save_project_dialog())
        self.root.bind_all("<Control-comma>", lambda _e: self._open_settings())
        self.root.bind_all("<Control-q>", lambda _e: self._close())
        self.root.bind_all("<Control-Shift-A>", lambda _e: self._add_audio())
        self.root.bind_all("<Control-Shift-M>", lambda _e: self._add_media())
        self.root.bind_all("<F9>", lambda _e: self._start())
        self.root.bind_all("<F1>", lambda _e: self._show_help_center())
        self.root.bind_all("<Control-minus>", lambda _e: self._set_global_zoom(self.global_font_scale.get() - 10))
        self.root.bind_all("<Control-plus>", lambda _e: self._set_global_zoom(self.global_font_scale.get() + 10))
        self.root.bind_all("<Control-equal>", lambda _e: self._set_global_zoom(self.global_font_scale.get() + 10))

    def _set_workflow_layout_mode(self, mode: str) -> None:
        selected = normalize_workflow_layout_mode(mode)
        self.config["workflow_layout_mode"] = selected
        for grid in getattr(self, "workflow_grids", {}).values():
            grid.set_layout_mode(selected)
        self._save_settings()
        self.guidance_text.set(f"Workflow-Layout aktiviert: {selected}.")

    def _build_start_page(self, page) -> None:
        grid = self._workflow_page(page, "start")
        grid.add_card(title=text("ui.rc22.card.project"), subtitle="Name, Notiz und sicherer Projektstand", builder=self._start_project_card, row=0, column=0)
        grid.add_card(title=text("ui.rc22.card.quick_access"), subtitle="Die wichtigsten Aktionen ohne Umwege", builder=self._start_quick_card, row=0, column=1)
        grid.add_card(title=text("ui.rc22.card.calendar"), subtitle="Termine, Aufgaben und Projektmarkierungen", builder=lambda parent: self._build_calendar(parent), row=1, column=0)
        grid.add_card(title=text("ui.rc22.card.workflow"), subtitle="Vom Import bis zum fertigen Ausgabeordner", builder=self._start_workflow_card, row=1, column=1)

    def _start_project_card(self, parent):
        ttk.Label(parent, textvariable=self.project_name, style="SectionHeader.TLabel").pack(anchor="w")
        ttk.Label(parent, text=text("ui.rc22.label.project_note"), style="Hint.TLabel").pack(anchor="w", pady=(8, 2))
        ttk.Entry(parent, textvariable=self.quick_note).pack(fill="x")
        row = ttk.Frame(parent, style="WorkflowCard.TFrame")
        row.pack(fill="x", pady=(10, 0))
        ttk.Button(row, text=text("ui.rc22.action.new"), command=self._new_project).pack(side="left")
        ttk.Button(row, text=text("ui.rc22.action.open"), command=self._open_project_file).pack(side="left", padx=5)
        ttk.Button(row, text=text("ui.rc22.action.save"), style="Accent.TButton", command=self._save_project_dialog).pack(side="left")
        ttk.Label(parent, textvariable=self.status_text, style="Status.TLabel", wraplength=560).pack(anchor="w", pady=(12, 0))
        return parent

    def _start_quick_card(self, parent):
        actions = (
            (text("ui.rc22.action.add_audio"), self._add_audio, "TileBlue.TButton"),
            (text("ui.rc22.action.add_media"), self._add_media, "TilePink.TButton"),
            (text("ui.rc22.card.settings"), self._open_settings, "TileGold.TButton"),
            (text("ui.rc22.action.check_production"), self._focus_preparation_assistant, "TileGreen.TButton"),
        )
        for index, (label, command, style) in enumerate(actions):
            button = ttk.Button(parent, text=label, style=style, command=command)
            button.grid(row=index // 2, column=index % 2, sticky="nsew", padx=4, pady=4)
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)
        return parent

    def _start_workflow_card(self, parent):
        lines = (
            text("ui.rc22.workflow.step1"),
            text("ui.rc22.workflow.step2"),
            text("ui.rc22.workflow.step3"),
            text("ui.rc22.workflow.step4"),
        )
        for line in lines:
            ttk.Label(parent, text=line, style="Hint.TLabel", wraplength=600).pack(anchor="w", pady=5)
        ttk.Button(parent, text=text("ui.rc22.action.check_now"), style="Accent.TButton", command=self._focus_preparation_assistant).pack(anchor="w", pady=(12, 0))
        return parent

    def _build_media_page(self, page) -> None:
        grid = self._workflow_page(page, "media")
        grid.add_card(title=text("ui.rc22.card.files"), subtitle="Audio, Bilder und Videos verwalten", builder=self._library_card, row=0, column=0)
        grid.add_card(title=text("ui.rc22.card.large_folder_import"), subtitle="Blockweise laden, filtern und jederzeit abbrechen", builder=self._media_import_card, row=0, column=1)
        grid.add_card(title=text("ui.rc22.card.output"), subtitle="Zielordner direkt festlegen, prüfen und öffnen", builder=self._output_card, row=1, column=0)
        grid.add_card(title=text("ui.rc22.card.selection_status"), subtitle="Aktuelle Mengen und Produktionszuordnung", builder=self._selection_card, row=1, column=1)

    def _media_import_card(self, parent):
        ttk.Label(parent, text=text("ui.rc22.large_folder.explanation"), style="Hint.TLabel", wraplength=600).pack(anchor="w")
        ttk.Button(parent, text=text("ui.rc22.action.scan_audio_folder"), style="Accent.TButton", command=self._add_audio).pack(fill="x", pady=(12, 5))
        ttk.Button(parent, text=text("ui.rc22.action.scan_media_folder"), style="Accent.TButton", command=self._add_media).pack(fill="x", pady=5)
        ttk.Button(parent, text=text("ui.rc22.action.open_folder_incremental"), command=self._add_media_folder).pack(fill="x", pady=5)
        ttk.Label(parent, text=text("ui.rc22.large_folder.features"), style="Hint.TLabel", wraplength=600).pack(anchor="w", pady=(10, 0))
        return parent

    def _output_card(self, parent):
        ttk.Label(parent, text=text("ui.rc22.label.active_output"), style="Section.TLabel").pack(anchor="w")
        ttk.Entry(parent, textvariable=self.output_dir).pack(fill="x", pady=(6, 8))
        row = ttk.Frame(parent, style="WorkflowCard.TFrame")
        row.pack(fill="x")
        ttk.Button(row, text=text("ui.rc22.action.choose_folder"), style="Accent.TButton", command=lambda: self._choose_directory(self.output_dir)).pack(side="left")
        ttk.Button(row, text=text("ui.rc22.action.open_folder"), command=self._open_output).pack(side="left", padx=6)
        ttk.Button(row, text=text("ui.rc22.action.create_safe_folder"), command=self._create_output_folder_and_retry).pack(side="left")
        ttk.Checkbutton(parent, text=text("ui.rc22.option.auto_open_success"), variable=self.auto_open_output).pack(anchor="w", pady=(12, 0))
        return parent

    def _selection_card(self, parent):
        ttk.Label(parent, textvariable=self.header_selection_stats, style="Status.TLabel", wraplength=600, justify="left").pack(anchor="w")
        ttk.Separator(parent).pack(fill="x", pady=10)
        ttk.Button(parent, text=text("ui.rc22.action.open_preview"), command=lambda: self.main_notebook.select(2)).pack(fill="x", pady=3)
        ttk.Button(parent, text=text("ui.rc22.action.assignment_settings"), command=self._open_settings).pack(fill="x", pady=3)
        ttk.Button(parent, text=text("ui.rc22.card.preparation_assistant"), style="Accent.TButton", command=self._focus_preparation_assistant).pack(fill="x", pady=3)
        return parent

    def _build_preview_page(self, page) -> None:
        grid = self._workflow_page(page, "preview")
        self.preview_card = grid.add_card(title=text("ui.rc22.card.large_preview"), subtitle="Bild oder Video prüfen", builder=self._preview_card, row=0, column=0)
        self.slideshow_order_card = grid.add_card(title=text("ui.rc22.card.image_order"), subtitle="Drag-and-drop, Sortierung und Start-/Endbild", builder=lambda parent: self._build_slideshow_order_panel(parent), row=0, column=1)
        self.waveform_card = grid.add_card(title=text("ui.rc22.card.audio_waveform"), subtitle="Szenenmarken und musikalische Bildwechsel", builder=lambda parent: self._build_waveform_panel(parent), row=1, column=0)
        self.playlist_card = grid.add_card(title=text("ui.rc22.card.audio_preview"), subtitle="Playlist unabhängig von der Produktionsreihenfolge", builder=self._playlist_tab, row=1, column=1)

    def _build_assignment_panel(self, parent):
        panel = ttk.Frame(parent, style="WorkflowCard.TFrame")
        panel.pack(fill="both", expand=True)
        ttk.Label(panel, text=text("ui.rc22.assignment.question"), style="Section.TLabel").pack(anchor="w")
        ttk.Radiobutton(
            panel,
            text=text("ui.rc22.assignment.pairwise"),
            variable=self.assignment_mode,
            value=SLIDESHOW_MODE_PAIRWISE,
            command=lambda: self._set_assignment_mode(SLIDESHOW_MODE_PAIRWISE),
        ).pack(anchor="w", pady=(8, 3))
        ttk.Label(panel, text=text("ui.rc22.assignment.pairwise_help"), style="Hint.TLabel", wraplength=580).pack(anchor="w", padx=(24, 0))
        ttk.Radiobutton(
            panel,
            text=text("ui.rc22.assignment.all_images"),
            variable=self.assignment_mode,
            value=SLIDESHOW_MODE_ALL_IMAGES,
            command=lambda: self._set_assignment_mode(SLIDESHOW_MODE_ALL_IMAGES),
        ).pack(anchor="w", pady=(10, 3))
        ttk.Label(panel, text=text("ui.rc22.assignment.all_images_help"), style="Hint.TLabel", wraplength=580).pack(anchor="w", padx=(24, 0))

        ttk.Separator(panel).pack(fill="x", pady=10)
        transition_row = ttk.Frame(panel, style="WorkflowCard.TFrame")
        transition_row.pack(fill="x")
        ttk.Label(transition_row, text=text("ui.rc22.assignment.transition")).pack(side="left")
        self.slideshow_transition_display = {key: label for key, label in TRANSITION_LABELS.items()}
        reverse = {label: key for key, label in self.slideshow_transition_display.items()}
        self.slideshow_transition_combo = ttk.Combobox(
            transition_row, values=list(reverse), state="readonly", width=31
        )
        selected = self.slideshow_transition_display.get(self.slideshow_transition.get(), self.slideshow_transition_display["auto"])
        self.slideshow_transition_combo.set(selected)
        self.slideshow_transition_combo.pack(side="left", fill="x", expand=True, padx=(8, 0))
        self.slideshow_transition_combo.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._set_slideshow_transition(reverse.get(self.slideshow_transition_combo.get(), "auto")),
        )
        ttk.Checkbutton(
            panel,
            text=text("ui.rc22.assignment.scene_sync"),
            variable=self.slideshow_scene_sync,
            command=self._set_scene_sync,
        ).pack(anchor="w", pady=(10, 0))
        ttk.Label(panel, textvariable=self.slideshow_summary_text, style="Status.TLabel", wraplength=580).pack(anchor="w", pady=(10, 0))
        return parent

    def _build_modes_page(self, page) -> None:
        grid = self._workflow_page(page, "modes")
        grid.add_card(title=text("ui.rc22.card.assignment"), subtitle="1:1 oder alle Bilder auf jedes Audio", builder=lambda parent: self._build_assignment_panel(parent), row=0, column=0)
        grid.add_card(title=text("ui.rc22.card.quick_modes"), subtitle="Laientaugliche geprüfte Profile", builder=self._quick_modes_tab, row=0, column=1)
        self.settings_card = grid.add_card(title=text("ui.rc22.card.settings"), subtitle="Anzeige, Ordner, Qualität und Dateiablage", builder=self._settings_tab, row=1, column=0)
        grid.add_card(title=text("ui.rc22.card.option_explanation"), subtitle="Was die gewählten Werte bewirken", builder=self._mode_details_card, row=1, column=1)

    def _mode_details_card(self, parent):
        ttk.Label(parent, textvariable=self.quick_mode_detail, style="Hint.TLabel", wraplength=600, justify="left").pack(anchor="w")
        ttk.Label(parent, textvariable=self.effect_speed_note, style="Status.TLabel", wraplength=600).pack(anchor="w", pady=(10, 0))
        ttk.Separator(parent).pack(fill="x", pady=10)
        ttk.Button(parent, text=text("ui.rc22.action.open_settings_targeted"), style="Accent.TButton", command=self._open_settings).pack(fill="x")
        ttk.Button(parent, text=text("ui.rc22.action.reset_all_zoom"), command=self._reset_all_area_zoom).pack(fill="x", pady=(6, 0))
        return parent

    def _open_settings(self) -> None:
        try:
            self.main_notebook.select(3)
            grid = self.workflow_grids.get("modes")
            if grid is not None and hasattr(self, "settings_card"):
                self.root.after_idle(lambda: grid.scroll_to_widget(self.settings_card))
            self.guidance_text.set("Einstellungen geöffnet. Anzeige, Ordner und Ausgabeoptionen sind direkt sichtbar.")
        except Exception:
            pass

    def _build_production_page(self, page) -> None:
        grid = self._workflow_page(page, "production")
        grid.add_card(title=text("ui.rc22.card.assignment"), subtitle="Geplante Aufträge vor dem Start", builder=self._pairing_card, row=0, column=0)
        self.preparation_card = grid.add_card(title=text("ui.rc22.card.preparation_assistant"), subtitle="Alle fehlenden Angaben gesammelt lösen", builder=self._preparation_assistant_card, row=0, column=1)
        self.monitor_card = grid.add_card(title=text("ui.rc22.card.production"), subtitle="Fortschritt, Restzeit und Aktivität", builder=self._monitor_card, row=1, column=0)
        grid.add_card(title=text("ui.rc22.card.start_result"), subtitle="Produktion steuern und Ausgabe öffnen", builder=self._production_actions_card, row=1, column=1)

    def _preparation_assistant_card(self, parent):
        table = ttk.Frame(parent, style="WorkflowCard.TFrame")
        table.pack(fill="both", expand=True)
        self.preparation_tree = ttk.Treeview(table, columns=("state", "check", "detail"), show="headings", height=7)
        for key, label, width in (("state", text("ui.rc22.table.status"), 80), ("check", text("ui.rc22.table.check"), 150), ("detail", text("ui.rc22.table.result"), 330)):
            self.preparation_tree.heading(key, text=label)
            self.preparation_tree.column(key, width=width, minwidth=70, stretch=key == "detail")
        scroll = ttk.Scrollbar(table, orient="vertical", command=self.preparation_tree.yview)
        self.preparation_tree.configure(yscrollcommand=scroll.set)
        self.preparation_tree.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        table.rowconfigure(0, weight=1)
        table.columnconfigure(0, weight=1)
        row = ttk.Frame(parent, style="WorkflowCard.TFrame")
        row.pack(fill="x", pady=(7, 0))
        ttk.Button(row, text=text("ui.rc22.action.resolve_selected"), command=self._resolve_selected_preparation).pack(side="left")
        ttk.Button(row, text=text("ui.rc22.action.auto_complete_safe"), command=self._auto_complete_preparation).pack(side="left", padx=5)
        ttk.Button(row, text=text("ui.rc22.action.recheck"), command=self._refresh_preparation_assistant).pack(side="right")
        self._refresh_preparation_assistant()
        return parent

    def _preparation_checks(self):
        return build_preparation_checks(
            audios=self.audios,
            media=self.media,
            output_dir=Path(self.output_dir.get()),
            quick_mode=self.quick_mode.get(),
            assignment_mode=self.assignment_mode.get(),
            archive_enabled=self.archive_used.get(),
            archive_dir=self.archive_project_dir.get(),
            analysis_pending=bool(self.slideshow_analysis_pending),
            job_count=len(self.jobs),
        )

    def _refresh_preparation_assistant(self) -> None:
        tree = getattr(self, "preparation_tree", None)
        if tree is None:
            return
        try:
            tree.delete(*tree.get_children())
            self._preparation_action_map = {}
            marker = {"ok": "✓", "warning": "!", "error": "✕"}
            for item in self._preparation_checks():
                tree.insert("", "end", iid=item.key, values=(marker.get(item.status, "•"), item.title, item.detail))
                self._preparation_action_map[item.key] = item.action
        except TclError:
            pass

    def _resolve_selected_preparation(self) -> None:
        selected = self.preparation_tree.selection() if hasattr(self, "preparation_tree") else ()
        if not selected:
            self.guidance_text.set("Im Vorbereitungsassistenten zuerst einen offenen Punkt markieren.")
            return
        action = getattr(self, "_preparation_action_map", {}).get(selected[0], "")
        actions = {
            "add_audio": self._add_audio,
            "add_media": self._add_media,
            "choose_output": lambda: self._choose_directory(self.output_dir),
            "repair_settings": self._repair_settings_and_retry,
            "switch_to_slideshow": self._switch_to_slideshow,
            "show_pairing": self._focus_pairing,
            "create_project_folder": self._create_project_folder,
            "focus_waveform": lambda: self.main_notebook.select(2),
        }
        callback = actions.get(action)
        if callback:
            callback()
            self.root.after_idle(self._refresh_preparation_assistant)
        else:
            self.guidance_text.set("Dieser Punkt ist bereits erledigt oder benötigt keine Aktion.")

    def _auto_complete_preparation(self) -> None:
        self._prepare_start_intelligently()
        if self.audios and self.media and not self.jobs:
            self._rebuild_pairs()
        self._refresh_preparation_assistant()
        self.guidance_text.set("Sichere Standardwerte wurden ergänzt. Offene Medienentscheidungen bleiben sichtbar.")

    def _focus_preparation_assistant(self) -> None:
        try:
            self.main_notebook.select(4)
            self._refresh_preparation_assistant()
            grid = self.workflow_grids.get("production")
            if grid is not None and hasattr(self, "preparation_card"):
                self.root.after_idle(lambda: grid.scroll_to_widget(self.preparation_card))
        except Exception:
            pass

    def _production_actions_card(self, parent):
        self.start_button = ttk.Button(parent, text=text("ui.workspace_grid.videos_automatisch_erstellen"), style="Accent.TButton", command=self._start)
        self.start_button.pack(fill="x", pady=(0, 7))
        self.cancel_button = ttk.Button(parent, text=text("ui.workspace_grid.sicher_abbrechen"), style="Danger.TButton", command=self._cancel, state="disabled")
        self.cancel_button.pack(fill="x", pady=4)
        ttk.Button(parent, text=text("ui.rc22.action.open_output_now"), command=self._open_output).pack(fill="x", pady=4)
        ttk.Button(parent, text=text("ui.rc22.action.clear_lists"), command=self._clear_lists).pack(fill="x", pady=4)
        ttk.Button(parent, text=text("ui.rc22.action.system_test"), command=self._run_assurance).pack(fill="x", pady=4)
        ttk.Checkbutton(parent, text=text("ui.rc22.option.auto_open_output"), variable=self.auto_open_output).pack(anchor="w", pady=(10, 0))
        Tooltip(self.start_button, text("ui.workspace_grid.pruft_eingaben_ausgabeordner_schnellmodus_und_freien_speicher_bevor"))
        return parent

    def _build_help_page(self, page) -> None:
        grid = self._workflow_page(page, "help")
        grid.add_card(title=text("ui.rc22.card.quick_help"), subtitle="Direkte Hilfe und Programminformationen", builder=self._help_actions_card, row=0, column=0)
        grid.add_card(title=text("ui.rc22.card.system_permissions"), subtitle="Diagnose, Berechtigungen und Fehlerlabor", builder=self._system_actions_card, row=0, column=1)
        grid.add_card(title=text("ui.rc22.card.logs"), subtitle="Menschlich und technisch nachvollziehbar", builder=self._build_debug_footer, row=1, column=0)
        grid.add_card(title=text("ui.rc22.card.shortcuts_workflow"), subtitle="Schneller arbeiten ohne versteckte Funktionen", builder=self._shortcuts_card, row=1, column=1)

    def _help_actions_card(self, parent):
        for label, command in ((text("ui.rc22.action.open_help"), self._show_help_center), (text("ui.rc22.action.open_settings"), self._open_settings), (text("ui.rc22.action.open_downloads"), self._open_downloads), (text("ui.rc22.action.about"), self._show_about)):
            ttk.Button(parent, text=label, command=command).pack(fill="x", pady=4)
        return parent

    def _system_actions_card(self, parent):
        for label, command in ((text("ui.rc22.action.start_system_test"), self._run_assurance), (text("ui.rc22.action.check_permissions"), self._show_permission_status), (text("ui.rc22.action.start_fault_lab"), self._run_fault_lab), (text("ui.rc22.action.open_logs"), self._open_logs)):
            ttk.Button(parent, text=label, command=command).pack(fill="x", pady=4)
        return parent

    def _shortcuts_card(self, parent):
        content = text("ui.rc22.shortcuts.content")
        ttk.Label(parent, text=content, style="Hint.TLabel", justify="left", wraplength=600).pack(anchor="nw")
        return parent

    def _build_status_bar(self, parent) -> None:
        bar = ttk.Frame(parent, style="Toolbar.TFrame", padding=(8, 5))
        bar.pack(fill="x", pady=(6, 0))
        ttk.Label(bar, textvariable=self.guidance_text, style="Hint.TLabel", wraplength=1100).pack(side="left", fill="x", expand=True)
        ttk.Label(bar, textvariable=self.status_text, style="Status.TLabel").pack(side="right", padx=(8, 0))

    def _apply_workspace_grid_defaults(self) -> None:
        """Kompatibilitätsaufruf: lädt das aktuelle Anzeigeprofil oder sichere Standards."""
        self._restore_workspace_layout_profile()


    def _grid_cell(self, parent, title: str, builder):
        wrapper = ttk.Frame(parent, style="GoldCard.TFrame", padding=4)
        ttk.Label(wrapper, text=title, style="Hint.TLabel").pack(anchor="w", padx=4, pady=(0, 3))
        content = builder(wrapper)
        content.pack(fill="both", expand=True)
        return wrapper

    def _production_cell(self, parent):
        cell = ttk.Frame(parent, style="Card.TFrame", padding=2)
        notebook = ttk.Notebook(cell)
        self.production_notebook = notebook
        notebook.pack(fill="both", expand=True)
        notebook.add(self._pairing_card(notebook), text=text('ui.workspace_grid.zuordnung'))
        notebook.add(self._monitor_card(notebook), text=text('ui.workspace_grid.produktion'))
        return cell

    def _assistant_card(self, parent):
        card = ttk.Frame(parent, style="Card.TFrame", padding=8)
        notebook = ttk.Notebook(card)
        self.assistant_notebook = notebook
        notebook.pack(fill="both", expand=True)
        notebook.add(self._quick_modes_tab(notebook), text=text('ui.workspace_grid.schnellmodi'))
        notebook.add(self._playlist_tab(notebook), text=text('ui.workspace_grid.playlist'))
        notebook.add(self._settings_tab(notebook), text=text('ui.workspace_grid.einstellungen'))
        notebook.add(self._help_tab(notebook), text=text('ui.workspace_grid.hilfe'))
        return card

    def _quick_modes_tab(self, parent):
        tab = ttk.Frame(parent, style="Card.TFrame", padding=5)
        container = ttk.Frame(tab, style="Card.TFrame")
        container.pack(fill="both", expand=True)
        canvas = Canvas(container, background=COLORS["panel"], highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        grid = ttk.Frame(canvas, style="Card.TFrame")
        window_id = canvas.create_window((0, 0), window=grid, anchor="nw")
        grid.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(window_id, width=event.width))
        canvas.bind("<MouseWheel>", lambda event: canvas.yview_scroll(int(-1 * (event.delta / 120)), "units") if canvas.winfo_ismapped() and not (getattr(event, "state", 0) & 0x4) else None, add="+")
        visible_modes = [key for key in QUICK_MODES if key != "custom"]
        for index, key in enumerate(visible_modes):
            spec = QUICK_MODES[key]
            label = f"{'★ ' if spec.recommended else ''}{spec.short_label} · {spec.label}"
            button = ttk.Button(grid, text=label, style="QuickMode.TButton", command=lambda selected=key: self._apply_quick_mode(selected))
            button.grid(row=index, column=0, sticky="ew", padx=3, pady=2)
            grid.columnconfigure(0, weight=1)
            self.mode_buttons[key] = button
            Tooltip(button, f"{spec.description}\nGeschwindigkeit: {spec.speed_class}")
        ttk.Label(tab, textvariable=self.quick_mode_note, style="Status.TLabel", wraplength=420).pack(fill="x", pady=(5, 0))
        return tab

    def _settings_tab(self, parent):
        tab = ttk.Frame(parent, style="Card.TFrame", padding=7)
        ttk.Label(tab, text=text("ui.settings.display"), style="Section.TLabel").pack(anchor="w")
        zoom_row = ttk.Frame(tab, style="Card.TFrame")
        zoom_row.pack(fill="x", pady=(4, 6))
        ttk.Label(zoom_row, text=text("ui.settings.global_zoom")).pack(side="left")
        ttk.Button(zoom_row, text=text("ui.symbol.minus"), width=3, command=lambda: self._set_global_zoom(self.global_font_scale.get() - 10)).pack(side="left", padx=(8, 2))
        ttk.Label(zoom_row, textvariable=self.global_font_scale, width=5, anchor="center").pack(side="left")
        ttk.Button(zoom_row, text=text("ui.symbol.plus"), width=3, command=lambda: self._set_global_zoom(self.global_font_scale.get() + 10)).pack(side="left", padx=2)
        ttk.Button(zoom_row, text=text("ui.area_zoom.reset"), command=lambda: self._set_global_zoom(100)).pack(side="left", padx=(6, 0))
        ttk.Label(tab, text=text("ui.settings.zoom_note"), style="Hint.TLabel", wraplength=700).pack(anchor="w", pady=(0, 8))
        ttk.Separator(tab).pack(fill="x", pady=6)
        ttk.Label(tab, text=text("ui.settings.import_dirs"), style="Section.TLabel").pack(anchor="w")
        self._label_entry(tab, text("ui.settings.audio_dir"), self.last_audio_dir, browse=True, project=True)
        self._label_entry(tab, text("ui.settings.media_dir"), self.last_media_dir, browse=True, project=True)
        ttk.Separator(tab).pack(fill="x", pady=8)
        self._label_entry(tab, "Ausgabeordner", self.output_dir, browse=True)
        self._combo(tab, "Ablage", self.output_mode, ("Gemeinsamer Ordner", "Neben Mediendatei"))
        ttk.Separator(tab).pack(fill="x", pady=8)
        ttk.Label(tab, text=text('ui.workspace_grid.automatisches_aufraumen'), style="Section.TLabel").pack(anchor="w")
        ttk.Checkbutton(tab, text=text('ui.workspace_grid.erfolgreich_verwendete_dateien_nach_prufung_sicher_verschieben'), variable=self.archive_used).pack(anchor="w")
        self._label_entry(tab, "Projektordner für Verwendet/", self.archive_project_dir, browse=True, project=True)
        self._combo(tab, "Namenszusatz", self.archive_suffix, ("__verwendet", "__fertig", "__benutzt"))
        ttk.Label(tab, text=text("help.archive"), style="Hint.TLabel", wraplength=420).pack(anchor="w", pady=(5, 0))
        ttk.Separator(tab).pack(fill="x", pady=8)
        ttk.Label(tab, text=text('ui.workspace_grid.optionale_details'), style="Section.TLabel").pack(anchor="w")
        self._combo(tab, "Auflösung", self.resolution, ("Original", "1280×720", "1920×1080"))
        self._combo(tab, "Videocodec", self.codec, ("libx264", "libx265"))
        self._combo(tab, "Geschwindigkeit", self.profile, tuple(PROFILES), formatter=lambda key: f"{PROFILES[key].label} · {PROFILES[key].description}")
        self._combo(tab, "Ergebnisprüfung", self.verification, ("Schnell", "Vollständig"))
        ttk.Checkbutton(tab, text=text('ui.workspace_grid.listen_nach_abschluss_behalten'), variable=self.keep_lists).pack(anchor="w", pady=6)
        return tab

    def _help_tab(self, parent):
        tab = ttk.Frame(parent, style="Card.TFrame", padding=10)
        content = (
            "Was mache ich hier?\n\n"
            "1. Dateien auswählen und nur bei Bedarf die Ansicht sortieren.\n"
            "2. Bild, Video und Audio direkt prüfen.\n"
            "3. Schnellmodus auswählen.\n"
            "4. Produktion starten und Fortschritt beobachten.\n"
            "5. Ereignisse im Debug-Footer menschlich oder als JSONL nachvollziehen.\n\n"
            "Originaldateien bleiben während der Videoerstellung unverändert."
        )
        ttk.Label(tab, text=content, style="Hint.TLabel", wraplength=430, justify="left").pack(anchor="nw")
        return tab

    def _pairing_card(self, parent):
        card = ttk.Frame(parent, style="Card.TFrame", padding=7)
        top = ttk.Frame(card, style="Card.TFrame")
        top.pack(fill="x")
        ttk.Label(top, text=text('ui.workspace_grid.zuordnung_und_fast_path_prufung'), style="Section.TLabel").pack(side="left")
        ttk.Label(top, textvariable=self.pair_status, style="Hint.TLabel", wraplength=420).pack(side="right")
        table = ttk.Frame(card, style="Card.TFrame")
        table.pack(fill="both", expand=True, pady=(5, 0))
        self.pair_tree = ttk.Treeview(table, columns=("nr", "audio", "media", "mode", "reason"), show="headings", height=3)
        for key, title, width in (("nr", "#", 32), ("audio", "Audio", 125), ("media", "Bild/Video", 125), ("mode", "Pfad", 95), ("reason", "Begründung", 190)):
            self.pair_tree.heading(key, text=title)
            self.pair_tree.column(key, width=width, minwidth=55, stretch=key in {"audio", "media", "reason"})
        scroll_x = ttk.Scrollbar(table, orient="horizontal", command=self.pair_tree.xview)
        scroll_y = ttk.Scrollbar(table, orient="vertical", command=self.pair_tree.yview)
        self.pair_tree.configure(xscrollcommand=scroll_x.set, yscrollcommand=scroll_y.set)
        self.pair_tree.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")
        table.rowconfigure(0, weight=1)
        table.columnconfigure(0, weight=1)
        return card

    def _monitor_card(self, parent):
        card = ttk.Frame(parent, style="Card.TFrame", padding=7)
        top = ttk.Frame(card, style="Card.TFrame")
        top.pack(fill="x")
        ttk.Label(top, text=text('ui.workspace_grid.echtzeitstatus_und_losungen'), style="Section.TLabel").pack(side="left")
        ttk.Label(top, textvariable=self.phase, style="Status.TLabel").pack(side="right")
        ttk.Label(card, textvariable=self.current_job, wraplength=620).pack(anchor="w", pady=(4, 3))
        ttk.Label(card, text=text('ui.workspace_grid.gesamtfortschritt'), style="Hint.TLabel").pack(anchor="w")
        ttk.Progressbar(card, variable=self.total_progress, maximum=100).pack(fill="x")
        ttk.Label(card, text=text('ui.workspace_grid.aktueller_auftrag'), style="Hint.TLabel").pack(anchor="w", pady=(4, 0))
        ttk.Progressbar(card, variable=self.job_progress, maximum=100, style="Job.Horizontal.TProgressbar").pack(fill="x")
        metrics = ttk.Frame(card, style="Card.TFrame")
        metrics.pack(fill="x", pady=(5, 0))
        for column in range(2):
            metrics.columnconfigure(column, weight=1, uniform="monitor-columns")
        for index, (label, variable) in enumerate((("Laufzeit", self.elapsed), ("Restzeit", self.eta), ("Tempo", self.speed), (text("ui.rc22.card.output"), self.output_size), ("Aktivität", self.activity))):
            box = ttk.Frame(metrics, style="Card.TFrame", padding=(5, 3))
            box.grid(row=index // 2, column=index % 2, sticky="ew", padx=3, pady=2)
            ttk.Label(box, text=label, style="Hint.TLabel").pack()
            ttk.Label(box, textvariable=variable).pack()
        return card
