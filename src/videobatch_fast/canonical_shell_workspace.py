from __future__ import annotations

from tkinter import ttk

from .canonical_shell_contract import (
    CANONICAL_THEME_LABELS,
    SHELL_NAVIGATION,
    SIDEBAR_WIDTH,
)


class CanonicalShellWorkspaceMixin:
    """Construct and coordinate the shell without owning dashboard internals."""

    def _build_ui(self) -> None:
        self.workflow_grids = {}
        self._build_menu_bar()
        self._configure_shell_styles()

        # A33: genau ein gewichteter Root-Container. Das verhindert ungenutzte
        # Randflächen bei KDE-Skalierung und hält die Oberfläche beim Resize vollflächig.
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        shell = ttk.Frame(self.root, style="Shell.TFrame")
        shell.grid(row=0, column=0, sticky="nsew")
        shell.columnconfigure(1, weight=1)
        shell.rowconfigure(0, weight=1)
        self._canonical_shell = shell

        sidebar = ttk.Frame(
            shell,
            style="ShellSidebar.TFrame",
            padding=(10, 12),
            width=SIDEBAR_WIDTH,
        )
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)

        # Weniger Randverbrauch = mehr gleichzeitig sichtbarer Arbeitsinhalt.
        content = ttk.Frame(shell, style="Shell.TFrame", padding=(10, 8, 10, 6))
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
        self.root.after_idle(self._verify_canonical_shell_fill)

    def _verify_canonical_shell_fill(self) -> None:
        shell = getattr(self, "_canonical_shell", None)
        if shell is None:
            return
        try:
            self.root.update_idletasks()
            root_width = int(self.root.winfo_width())
            root_height = int(self.root.winfo_height())
            shell_width = int(shell.winfo_width())
            shell_height = int(shell.winfo_height())
        except Exception:
            return
        width_gap = abs(root_width - shell_width)
        height_gap = abs(root_height - shell_height)
        if width_gap <= 2 and height_gap <= 2:
            return
        try:
            self._event(
                "SHELL_GEOMETRY_MISMATCH",
                "Fenster und Arbeitsfläche unterscheiden sich",
                f"Fenster {root_width}×{root_height}, Oberfläche {shell_width}×{shell_height}.",
                level="warning",
                solution="Fenster einmal wiederherstellen oder maximieren und Diagnose prüfen.",
            )
        except Exception:
            pass

    def _build_shell_workspace(self, parent) -> None:
        workspace = ttk.Frame(parent, style="Shell.TFrame")
        workspace.grid(row=3, column=0, sticky="nsew")
        workspace.rowconfigure(0, weight=1)
        workspace.columnconfigure(0, weight=1)

        self.main_notebook = ttk.Notebook(workspace, style="Shell.TNotebook")
        self.main_notebook.grid(row=0, column=0, sticky="nsew")
        self.main_notebook.bind("<<NotebookTabChanged>>", self._on_main_tab_changed, add="+")
        self.main_notebook.bind("<<NotebookTabChanged>>", self._on_shell_tab_changed, add="+")

        pages = [ttk.Frame(self.main_notebook, style="Card.TFrame", padding=5) for _ in range(6)]
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
        if page_index is None:
            return
        self.main_notebook.select(page_index)
        self.main_notebook.focus_set()
        area = {1: "media", 2: "preview", 3: "modes", 4: "production"}.get(page_index)
        grid = getattr(self, "workflow_grids", {}).get(area) if area else None
        if grid is not None:
            self.root.after_idle(grid.scroll_to_top)

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
            active = item.page_index == selected_index and item.action not in {"disabled", "settings"}
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
                self.guidance_text.set(f"Bereich für „{self.shell_search.get().strip()}“ geöffnet.")
                return
        self.guidance_text.set("Kein direkter Bereich gefunden. Dashboard wurde geöffnet.")
        self._select_shell_page(0)

    def _bind_header_statistics(self) -> None:
        super()._bind_header_statistics()
        for variable in (self.visual_effect, self.transition, self.quick_mode):
            variable.trace_add("write", lambda *_args: self.root.after_idle(self._refresh_kpi_cards))
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
            self.shell_theme_combo.set(CANONICAL_THEME_LABELS.get(self.theme_name.get(), "Midnight Blue"))
        if hasattr(self, "shell_font_combo"):
            self.shell_font_combo.set(self._font_profile_for_scale(self.global_font_scale.get()))
