from __future__ import annotations

from tkinter import Canvas, TclError, ttk
from typing import Callable

WORKFLOW_LAYOUT_MODES = {"two_columns", "wide", "compact"}
DEFAULT_WORKFLOW_LAYOUT_MODE = "two_columns"


def normalize_workflow_layout_mode(value: object) -> str:
    selected = str(value)
    return selected if selected in WORKFLOW_LAYOUT_MODES else DEFAULT_WORKFLOW_LAYOUT_MODE


class ScrollableWorkflowGrid:
    """Two-column workflow grid that grows vertically instead of clipping widgets."""

    def __init__(self, parent, *, background: str, min_cell_height: int = 285, layout_mode: str = DEFAULT_WORKFLOW_LAYOUT_MODE) -> None:
        self.wrapper = ttk.Frame(parent, style="Card.TFrame")
        self.wrapper.pack(fill="both", expand=True)
        self.canvas = Canvas(
            self.wrapper,
            background=background,
            highlightthickness=0,
            borderwidth=0,
        )
        self.scrollbar = ttk.Scrollbar(self.wrapper, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.body = ttk.Frame(self.canvas, style="Card.TFrame", padding=(2, 2, 7, 10))
        self.window_id = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.min_cell_height = min_cell_height
        self.cards: list[ttk.Frame] = []
        self._card_positions: dict[ttk.Frame, tuple[int, int]] = {}
        self._rows = 0
        self.layout_mode = normalize_workflow_layout_mode(layout_mode)
        self._refresh_job: str | None = None
        self._last_canvas_size: tuple[int, int] | None = None
        self._last_visible_cell: int | None = None
        self._last_scrollregion = None
        self._configure_columns()
        self.body.bind("<Configure>", self._sync_scroll_region, add="+")
        self.canvas.bind("<Configure>", self._sync_width_and_rows, add="+")
        self.canvas.bind("<MouseWheel>", self._wheel, add="+")
        self.canvas.bind("<Button-4>", lambda _e: self._scroll(-3), add="+")
        self.canvas.bind("<Button-5>", lambda _e: self._scroll(3), add="+")

    def add_card(
        self,
        *,
        title: str,
        subtitle: str = "",
        builder: Callable[[ttk.Frame], object] | None = None,
        row: int,
        column: int,
    ) -> ttk.Frame:
        card = ttk.Frame(self.body, style="WorkflowCard.TFrame", padding=8)
        card.grid(row=row, column=column, sticky="nsew", padx=5, pady=5)
        self._card_positions[card] = (row, column)
        header = ttk.Frame(card, style="WorkflowCard.TFrame")
        header.pack(fill="x", pady=(0, 6))
        ttk.Label(header, text=title, style="WorkflowTitle.TLabel").pack(anchor="w")
        if subtitle:
            ttk.Label(header, text=subtitle, style="WorkflowHint.TLabel", wraplength=620, justify="left").pack(anchor="w", pady=(1, 0))
        content = ttk.Frame(card, style="WorkflowCard.TFrame")
        content.pack(fill="both", expand=True)
        if builder is not None:
            built = builder(content)
            if built is not None and hasattr(built, "pack_info"):
                try:
                    if not built.winfo_manager():
                        built.pack(fill="both", expand=True)
                except TclError:
                    pass
        self.cards.append(card)
        self._rows = max(self._rows, row + 1)
        self._apply_card_layout()
        self.bind_scrolling(card)
        self.schedule_refresh()
        return card

    def set_layout_mode(self, mode: str) -> None:
        self.layout_mode = normalize_workflow_layout_mode(mode)
        self._apply_card_layout()
        self.schedule_refresh()

    def bind_scrolling(self, widget) -> None:
        try:
            widget.bind("<MouseWheel>", self._wheel, add="+")
            widget.bind("<Button-4>", lambda _e: self._scroll(-3), add="+")
            widget.bind("<Button-5>", lambda _e: self._scroll(3), add="+")
            for child in widget.winfo_children():
                self.bind_scrolling(child)
        except TclError:
            return

    def schedule_refresh(self) -> None:
        """Coalesce geometry updates instead of nesting Tk idle loops per card."""
        if self._refresh_job is not None:
            return
        try:
            self._refresh_job = self.canvas.after_idle(self._run_scheduled_refresh)
        except TclError:
            self._refresh_job = None

    def _run_scheduled_refresh(self) -> None:
        self._refresh_job = None
        self.refresh()

    def refresh(self) -> None:
        try:
            self._sync_width_and_rows()
            self._sync_scroll_region()
        except TclError:
            pass

    def scroll_to_widget(self, widget) -> None:
        try:
            self.body.update_idletasks()
            self.refresh()
            top = max(0, widget.winfo_y() - 8)
            total = max(1, self.body.winfo_reqheight())
            self.canvas.yview_moveto(min(1.0, top / total))
            widget.focus_set()
        except TclError:
            pass

    def _configure_columns(self) -> None:
        columns = 1 if self.layout_mode == "wide" else 2
        for column in range(2):
            weight = 1 if column < columns else 0
            self.body.columnconfigure(column, weight=weight, uniform="workflow-columns" if weight else "")

    def _apply_card_layout(self) -> None:
        previous_rows = self._rows
        self._configure_columns()
        for index, card in enumerate(self.cards):
            original_row, original_column = self._card_positions.get(card, (index // 2, index % 2))
            if self.layout_mode == "wide":
                row, column, columnspan = index, 0, 2
            else:
                row, column, columnspan = original_row, original_column, 1
            card.grid_configure(row=row, column=column, columnspan=columnspan, sticky="nsew", padx=5, pady=5)
        self._rows = len(self.cards) if self.layout_mode == "wide" else max((row for row, _column in self._card_positions.values()), default=-1) + 1
        for row in range(max(previous_rows, self._rows)):
            if row < self._rows:
                self.body.rowconfigure(row, weight=1, uniform="workflow-rows", minsize=self.min_cell_height)
            else:
                self.body.rowconfigure(row, weight=0, uniform="", minsize=0)

    def _sync_scroll_region(self, _event=None) -> None:
        try:
            region = self.canvas.bbox("all")
            if region == self._last_scrollregion:
                return
            self._last_scrollregion = region
            self.canvas.configure(scrollregion=region)
        except TclError:
            pass

    def _sync_width_and_rows(self, event=None) -> None:
        try:
            width = max(1, int(event.width if event is not None else self.canvas.winfo_width()))
            height = max(1, int(event.height if event is not None else self.canvas.winfo_height()))
            size = (width, height)
            divisor = 3 if self.layout_mode == "compact" else 2
            visible_cell = max(self.min_cell_height, (max(600, height) - 24) // divisor)
            if self._last_canvas_size != size:
                self._last_canvas_size = size
                self.canvas.itemconfigure(self.window_id, width=width)
            if self._last_visible_cell != visible_cell:
                self._last_visible_cell = visible_cell
                for row in range(self._rows):
                    self.body.rowconfigure(row, minsize=visible_cell)
            self._sync_scroll_region()
        except TclError:
            pass

    def _wheel(self, event):
        if getattr(event, "state", 0) & 0x4:
            return None
        delta = getattr(event, "delta", 0)
        if delta:
            self._scroll(-3 if delta > 0 else 3)
            return "break"
        return None

    def _scroll(self, units: int):
        try:
            self.canvas.yview_scroll(units, "units")
        except TclError:
            pass
        return "break"
