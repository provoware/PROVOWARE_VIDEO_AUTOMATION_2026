from __future__ import annotations

from tkinter import StringVar, ttk
from typing import Callable

from .canonical_shell_contract import CANONICAL_THEME_LABELS, FONT_PROFILES, SHELL_NAVIGATION
from .theme import COLORS, apply_theme, available_themes, best_text_color, safe_text_color
from .versioning import build_label


class CanonicalShellChromeMixin:
    def _configure_shell_styles(self) -> None:
        style = ttk.Style(self.root)
        scale = int(self.global_font_scale.get()) if hasattr(self, "global_font_scale") else 105
        factor = max(0.85, min(1.5, scale / 105.0))
        toolbar_text = safe_text_color(COLORS["toolbar"], COLORS["text"])
        panel_text = safe_text_color(COLORS["panel"], COLORS["text"])
        style.configure("Shell.TFrame", background=COLORS["bg"])
        style.configure("ShellSidebar.TFrame", background=COLORS["toolbar"], relief="solid", borderwidth=1)
        style.configure("ShellHeader.TFrame", background=COLORS["toolbar"], relief="solid", borderwidth=1)
        style.configure("ShellCard.TFrame", background=COLORS["panel"], relief="solid", borderwidth=1)
        style.configure(
            "ShellBrand.TLabel", background=COLORS["toolbar"], foreground=toolbar_text,
            font=("DejaVu Sans", max(15, round(17 * factor)), "bold"),
        )
        style.configure(
            "ShellHint.TLabel", background=COLORS["toolbar"], foreground=COLORS["muted"],
            font=("DejaVu Sans", max(9, round(10 * factor))),
        )
        style.configure(
            "ShellKpi.TLabel", background=COLORS["panel"], foreground=panel_text,
            font=("DejaVu Sans", max(18, round(21 * factor)), "bold"),
        )
        style.configure(
            "ShellKpiHint.TLabel", background=COLORS["panel"], foreground=COLORS["muted"],
            font=("DejaVu Sans", max(9, round(10 * factor))),
        )
        style.configure(
            "ShellNav.TButton", background=COLORS["toolbar"], foreground=toolbar_text,
            padding=(12, 10), anchor="w", relief="flat", borderwidth=0,
        )
        style.configure(
            "ShellNavActive.TButton", background=COLORS["selection"],
            foreground=best_text_color(COLORS["selection"]), padding=(12, 10),
            anchor="w", relief="flat", borderwidth=0,
        )
        style.configure("Shell.TNotebook", background=COLORS["bg"], borderwidth=0)
        style.layout("Shell.TNotebook.Tab", [])

    def _build_shell_sidebar(self, parent) -> None:
        ttk.Label(parent, text="▣  VideoBatch Fast", style="ShellBrand.TLabel").pack(anchor="w")
        ttk.Label(parent, text="Batch Video Processing", style="ShellHint.TLabel").pack(
            anchor="w", padx=(27, 0), pady=(2, 20)
        )
        self._shell_nav_buttons = {}
        for item in SHELL_NAVIGATION:
            if item.action == "disabled":
                button = ttk.Button(
                    parent, text=item.label + " · Checkpoint 5", style="ShellNav.TButton",
                    state="disabled",
                )
            elif item.action == "settings":
                button = ttk.Button(parent, text=item.label, style="ShellNav.TButton", command=self._open_settings)
            else:
                button = ttk.Button(
                    parent, text=item.label, style="ShellNav.TButton",
                    command=lambda index=item.page_index: self._select_shell_page(index),
                )
            button.pack(fill="x", pady=2)
            self._shell_nav_buttons[item.key] = button
        ttk.Frame(parent, style="ShellSidebar.TFrame").pack(fill="both", expand=True)
        status = ttk.Frame(parent, style="ShellCard.TFrame", padding=11)
        status.pack(fill="x", pady=(12, 0))
        ttk.Label(status, text="Systemstatus", style="ShellKpiHint.TLabel").pack(anchor="w")
        ttk.Label(status, textvariable=self.status_text, style="Success.TLabel", wraplength=175).pack(
            anchor="w", pady=(7, 3)
        )
        ttk.Label(status, text=f"Version {build_label()}", style="ShellKpiHint.TLabel").pack(anchor="w")

    def _build_shell_header(self, parent) -> None:
        header = ttk.Frame(parent, style="ShellHeader.TFrame", padding=(14, 11))
        header.grid(row=0, column=0, sticky="ew", pady=(0, 11))
        header.columnconfigure(1, weight=1)
        identity = ttk.Frame(header, style="ShellHeader.TFrame")
        identity.grid(row=0, column=0, sticky="w")
        self.shell_section_title = StringVar(value="Dashboard")
        ttk.Label(identity, textvariable=self.shell_section_title, style="HeaderTitle.TLabel").pack(anchor="w")
        ttk.Label(identity, text="Kanonische Oberfläche · VB-GFX-1.0", style="ShellHint.TLabel").pack(anchor="w")

        controls = ttk.Frame(header, style="ShellHeader.TFrame")
        controls.grid(row=0, column=2, sticky="e")
        theme_reverse = {label: key for key, label in CANONICAL_THEME_LABELS.items()}
        self.shell_theme_combo = ttk.Combobox(controls, values=list(theme_reverse), state="readonly", width=16)
        self.shell_theme_combo.set(CANONICAL_THEME_LABELS.get(self.theme_name.get(), "Midnight Blue"))
        self.shell_theme_combo.grid(row=0, column=0, padx=(0, 6))
        self.shell_theme_combo.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._set_canonical_theme(theme_reverse[self.shell_theme_combo.get()]),
        )
        self.shell_font_combo = ttk.Combobox(controls, values=list(FONT_PROFILES), state="readonly", width=10)
        self.shell_font_combo.set(self._font_profile_for_scale(self.global_font_scale.get()))
        self.shell_font_combo.grid(row=0, column=1)
        self.shell_font_combo.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._set_global_zoom(FONT_PROFILES[self.shell_font_combo.get()]),
        )

        search_row = ttk.Frame(header, style="ShellHeader.TFrame")
        search_row.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(9, 0))
        search_row.columnconfigure(0, weight=1)
        self.shell_search = StringVar(value="")
        search = ttk.Entry(search_row, textvariable=self.shell_search)
        search.grid(row=0, column=0, sticky="ew")
        search.bind("<Return>", self._run_shell_search)
        ttk.Label(search_row, text="Medien, Vorschau, Effekte, Queue oder Hilfe suchen", style="ShellHint.TLabel").grid(
            row=1, column=0, sticky="w", pady=(3, 0)
        )

    def _build_shell_kpis(self, parent) -> None:
        row = ttk.Frame(parent, style="Shell.TFrame")
        row.grid(row=1, column=0, sticky="ew", pady=(0, 11))
        for column in range(4):
            row.columnconfigure(column, weight=1, uniform="kpi")
        self.shell_media_kpi = StringVar(value="0")
        self.shell_queue_kpi = StringVar(value="0")
        self.shell_effect_kpi = StringVar(value="Automatik")
        self.shell_scheduler_kpi = StringVar(value="Nicht geplant")
        cards = (
            ("Medien", self.shell_media_kpi, "Audio, Bilder und Videos"),
            ("Queue", self.shell_queue_kpi, "vorbereitete Aufträge"),
            ("Effekte", self.shell_effect_kpi, "aktiver Look"),
            ("Startzeituhr", self.shell_scheduler_kpi, "vollständig in Checkpoint 5"),
        )
        for column, (title, variable, hint) in enumerate(cards):
            card = ttk.Frame(row, style="ShellCard.TFrame", padding=(14, 11))
            card.grid(row=0, column=column, sticky="nsew", padx=4)
            ttk.Label(card, text=title, style="ShellKpiHint.TLabel").pack(anchor="w")
            ttk.Label(card, textvariable=variable, style="ShellKpi.TLabel").pack(anchor="w", pady=(4, 1))
            ttk.Label(card, text=hint, style="ShellKpiHint.TLabel").pack(anchor="w")

    def _build_shell_actions(self, parent) -> None:
        bar = ttk.Frame(parent, style="ShellHeader.TFrame", padding=(8, 6))
        bar.grid(row=2, column=0, sticky="ew", pady=(0, 11))
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
        if not self._shell_action_buttons:
            return
        available = int(width if width is not None else getattr(event, "width", 0))
        columns = 3 if available and available < 920 else len(self._shell_action_buttons)
        parent = self._shell_action_buttons[0].master
        for column in range(len(self._shell_action_buttons)):
            parent.columnconfigure(column, weight=1 if column < columns else 0)
        for index, button in enumerate(self._shell_action_buttons):
            button.grid_forget()
            button.grid(row=index // columns, column=index % columns, sticky="ew", padx=3, pady=3)

    def _set_canonical_theme(self, name: str) -> None:
        if name not in available_themes():
            name = "neon_gravity"
        self.theme_name.set(name)
        self.config["theme"] = name
        apply_theme(self.root, self.global_font_scale.get(), name)
        self._refresh_theme_widgets()
        self._save_settings()
        self.guidance_text.set(f"Farbtheme aktiviert: {CANONICAL_THEME_LABELS[name]}.")

    @staticmethod
    def _font_profile_for_scale(scale: int) -> str:
        return min(FONT_PROFILES, key=lambda label: abs(FONT_PROFILES[label] - int(scale)))

    def _refresh_theme_widgets(self) -> None:
        super()._refresh_theme_widgets()
        self._configure_shell_styles()
