from __future__ import annotations

from tkinter import TclError, ttk

from .theme import COLORS, best_text_color, safe_text_color

VISUAL_PASS2_GAP = 8
VISUAL_PASS2_CARD_PADDING = 12
VISUAL_PASS2_HALF_GAP = VISUAL_PASS2_GAP // 2
VISUAL_PASS2_MIN_ROW_HEIGHT = 32
VISUAL_PASS2_MIN_HINT_FONT = 10
VISUAL_PASS2_MIN_BUTTON_PAD_Y = 7


def visual_scale_factor(scale_percent: int) -> float:
    """Return the shared low-vision scale without defeating 80–200% UI zoom."""

    return max(0.8, min(2.0, scale_percent / 100.0))


class CanonicalVisualPolishMixin:
    """Pure presentation layer for Visual Pass 2.

    The mixin only adjusts ttk styles, geometry, spacing and focus-neutral widget
    presentation. It deliberately does not alter commands, application state,
    project data or render behaviour.
    """

    def _configure_shell_styles(self) -> None:
        super()._configure_shell_styles()
        style = ttk.Style(self.root)
        scale = int(self.global_font_scale.get()) if hasattr(self, "global_font_scale") else 105
        factor = visual_scale_factor(scale)
        panel_text = safe_text_color(COLORS["panel"], COLORS["text"])
        panel_muted = safe_text_color(COLORS["panel"], COLORS["muted"])
        button_pad_x = max(10, round(10 * factor))
        button_pad_y = max(VISUAL_PASS2_MIN_BUTTON_PAD_Y, round(7 * factor))
        row_height = max(VISUAL_PASS2_MIN_ROW_HEIGHT, round(32 * factor))
        heading_pad_x = max(8, round(8 * factor))
        heading_pad_y = max(6, round(6 * factor))

        style.configure(
            "ShellHeader.TFrame",
            background=COLORS["toolbar"],
            relief="flat",
            borderwidth=0,
        )
        style.configure(
            "ShellActionBar.TFrame",
            background=COLORS["bg"],
            relief="flat",
            borderwidth=0,
        )
        style.configure(
            "ShellCard.TFrame",
            background=COLORS["panel"],
            relief="solid",
            borderwidth=1,
            bordercolor=COLORS["border_subtle"],
        )
        style.configure(
            "ShellPrimaryCard.TFrame",
            background=COLORS["panel"],
            relief="solid",
            borderwidth=1,
            bordercolor=COLORS["accent2"],
        )

        for style_name in (
            "ShellKpiMedia.TFrame",
            "ShellKpiQueue.TFrame",
            "ShellKpiEffects.TFrame",
            "ShellKpiScheduler.TFrame",
        ):
            style.configure(
                style_name,
                background=COLORS["panel"],
                relief="solid",
                borderwidth=1,
                bordercolor=COLORS["border_subtle"],
            )
        style.configure(
            "ShellKpi.TLabel",
            background=COLORS["panel"],
            foreground=panel_text,
            font=("DejaVu Sans", max(15, round(16 * factor)), "bold"),
        )
        style.configure(
            "ShellKpiHint.TLabel",
            background=COLORS["panel"],
            foreground=panel_muted,
            font=(
                "DejaVu Sans",
                max(VISUAL_PASS2_MIN_HINT_FONT, round(10 * factor)),
            ),
        )

        style.configure(
            "Ghost.TButton",
            background=COLORS["panel2"],
            foreground=safe_text_color(COLORS["panel2"], COLORS["text"]),
            padding=(button_pad_x, button_pad_y),
            borderwidth=2,
            bordercolor=COLORS["border_subtle"],
            relief="flat",
        )
        style.map(
            "Ghost.TButton",
            background=[("active", COLORS["hover"]), ("focus", COLORS["selection"])],
            foreground=[
                ("active", best_text_color(COLORS["hover"])),
                ("focus", best_text_color(COLORS["selection"])),
            ],
            bordercolor=[
                ("focus", COLORS["accent2"]),
                ("active", COLORS["hover"]),
            ],
        )

        style.configure("Treeview", rowheight=row_height)
        style.configure(
            "Treeview.Heading",
            background=COLORS["panel2"],
            foreground=safe_text_color(COLORS["panel2"], COLORS["muted"]),
            padding=(heading_pad_x, heading_pad_y),
            font=("DejaVu Sans", max(10, round(10 * factor)), "bold"),
            relief="flat",
        )
        style.configure(
            "ShellFooterStatus.TLabel",
            background=COLORS["toolbar"],
            foreground=safe_text_color(COLORS["toolbar"], COLORS["success"]),
            padding=(6, 2),
            font=("DejaVu Sans", max(10, round(10 * factor)), "bold"),
            anchor="e",
        )

    def _build_shell_header(self, parent) -> None:
        super()._build_shell_header(parent)
        try:
            self._shell_header.configure(padding=(VISUAL_PASS2_CARD_PADDING, VISUAL_PASS2_GAP))
            self._shell_header.grid_configure(pady=(0, VISUAL_PASS2_GAP))
        except (AttributeError, TclError):
            pass

    def _build_shell_kpis(self, parent) -> None:
        super()._build_shell_kpis(parent)
        try:
            self._shell_kpi_row.grid_configure(pady=(0, VISUAL_PASS2_GAP))
            for card in self._shell_kpi_cards:
                card.configure(padding=(VISUAL_PASS2_CARD_PADDING, VISUAL_PASS2_GAP))
        except (AttributeError, TclError):
            pass

    def _layout_shell_kpis(self, event=None, *, width: int | None = None) -> None:
        super()._layout_shell_kpis(event, width=width)
        for card in getattr(self, "_shell_kpi_cards", ()):
            try:
                if card.winfo_manager() == "grid":
                    card.grid_configure(
                        padx=VISUAL_PASS2_HALF_GAP,
                        pady=VISUAL_PASS2_HALF_GAP,
                    )
            except TclError:
                continue

    def _build_shell_actions(self, parent) -> None:
        super()._build_shell_actions(parent)
        buttons = tuple(getattr(self, "_shell_action_buttons", ()))
        if not buttons:
            return
        try:
            bar = buttons[0].master
            bar.configure(style="ShellActionBar.TFrame", padding=(4, 2))
            bar.grid_configure(pady=(0, VISUAL_PASS2_GAP))
        except TclError:
            return

    def _layout_shell_actions(self, event=None, *, width: int | None = None) -> None:
        super()._layout_shell_actions(event, width=width)
        for button in getattr(self, "_shell_action_buttons", ()):
            try:
                if button.winfo_manager() == "grid":
                    button.grid_configure(
                        padx=VISUAL_PASS2_HALF_GAP,
                        pady=VISUAL_PASS2_HALF_GAP,
                    )
            except TclError:
                continue

    def _layout_canonical_dashboard(self, width: int) -> None:
        super()._layout_canonical_dashboard(width)
        cards = tuple(
            card
            for card in (
                getattr(self, "_dashboard_sources_card", None),
                getattr(self, "_dashboard_queue_card", None),
                getattr(self, "_dashboard_details_card", None),
                getattr(self, "_dashboard_scheduler_card", None),
            )
            if card is not None
        )
        for card in cards:
            try:
                card.configure(padding=(VISUAL_PASS2_CARD_PADDING, 10))
            except TclError:
                continue
        queue = getattr(self, "_dashboard_queue_card", None)
        if queue is not None:
            try:
                queue.configure(style="ShellPrimaryCard.TFrame")
            except TclError:
                pass
        self._apply_visual_pass2_dashboard_gaps()

    def _apply_visual_pass2_dashboard_gaps(self) -> None:
        mode = getattr(self, "_dashboard_layout_mode", "")
        source = getattr(self, "_dashboard_sources_card", None)
        queue = getattr(self, "_dashboard_queue_card", None)
        details = getattr(self, "_dashboard_details_card", None)
        scheduler = getattr(self, "_dashboard_scheduler_card", None)
        if not all((source, queue, details, scheduler)):
            return
        try:
            if mode == "three_columns":
                source.grid_configure(padx=(0, 4), pady=(0, 8))
                queue.grid_configure(padx=4, pady=(0, 8))
                details.grid_configure(padx=(4, 0), pady=(0, 8))
                scheduler.grid_configure(pady=(0, 0))
            elif mode == "two_columns":
                source.grid_configure(padx=(0, 4), pady=(0, 8))
                queue.grid_configure(padx=(4, 0), pady=(0, 8))
                details.grid_configure(padx=0, pady=(0, 8))
                scheduler.grid_configure(padx=0, pady=(0, 0))
            elif mode == "stacked":
                visible = [
                    card
                    for card in (source, queue, details, scheduler)
                    if card.winfo_manager() == "grid"
                ]
                for index, card in enumerate(visible):
                    card.grid_configure(
                        padx=0,
                        pady=(0, VISUAL_PASS2_GAP if index < len(visible) - 1 else 0),
                    )
        except TclError:
            return

    def _build_canonical_status_bar(self, parent) -> None:
        before = set(parent.winfo_children())
        super()._build_canonical_status_bar(parent)
        created = [widget for widget in parent.winfo_children() if widget not in before]
        if not created:
            return
        bar = created[-1]
        try:
            bar.configure(padding=(10, 3))
        except TclError:
            return
        for child in bar.winfo_children():
            try:
                if child.winfo_class() == "TLabel" and child.cget("style") == "Status.TLabel":
                    child.configure(style="ShellFooterStatus.TLabel")
            except TclError:
                continue
