from __future__ import annotations

from tkinter import Menu, ttk

from .text_resources import text
from .theme import COLORS, available_themes
from .versioning import build_label
from .workflow_grid import (
    DEFAULT_WORKFLOW_LAYOUT_MODE,
    ScrollableWorkflowGrid,
    normalize_workflow_layout_mode,
)


class UiWorkspaceShellLayoutMixin:
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
        layout_menu.add_command(label=text("ui.workspace_grid.layout_two_columns"), command=lambda: self._set_workflow_layout_mode("two_columns"))
        layout_menu.add_command(label=text("ui.workspace_grid.layout_wide"), command=lambda: self._set_workflow_layout_mode("wide"))
        layout_menu.add_command(label=text("ui.workspace_grid.layout_compact"), command=lambda: self._set_workflow_layout_mode("compact"))
        view_menu.add_cascade(label=text("ui.workspace_grid.layout_menu"), menu=layout_menu)
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

    def _build_status_bar(self, parent) -> None:
        bar = ttk.Frame(parent, style="Toolbar.TFrame", padding=(8, 5))
        bar.pack(fill="x", pady=(6, 0))
        ttk.Label(bar, textvariable=self.guidance_text, style="Hint.TLabel", wraplength=1100).pack(side="left", fill="x", expand=True)
        ttk.Label(bar, textvariable=self.status_text, style="Status.TLabel").pack(side="right", padx=(8, 0))
