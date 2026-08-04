from __future__ import annotations

from tkinter import Canvas, TclError, ttk
from typing import Callable


class ScrollableWorkflowGrid:
    """Two-column workflow grid that grows vertically instead of clipping widgets."""

    def __init__(self, parent, *, background: str, min_cell_height: int = 285) -> None:
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
        self._rows = 0
        self.body.columnconfigure(0, weight=1, uniform="workflow-columns")
        self.body.columnconfigure(1, weight=1, uniform="workflow-columns")
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
        self.body.rowconfigure(row, weight=1, uniform="workflow-rows", minsize=self.min_cell_height)
        self.bind_scrolling(card)
        self.refresh()
        return card

    def bind_scrolling(self, widget) -> None:
        try:
            widget.bind("<MouseWheel>", self._wheel, add="+")
            widget.bind("<Button-4>", lambda _e: self._scroll(-3), add="+")
            widget.bind("<Button-5>", lambda _e: self._scroll(3), add="+")
            for child in widget.winfo_children():
                self.bind_scrolling(child)
        except TclError:
            return

    def refresh(self) -> None:
        try:
            self.body.update_idletasks()
            self._sync_width_and_rows()
            self._sync_scroll_region()
        except TclError:
            pass

    def scroll_to_widget(self, widget) -> None:
        try:
            self.refresh()
            top = max(0, widget.winfo_y() - 8)
            total = max(1, self.body.winfo_reqheight())
            self.canvas.yview_moveto(min(1.0, top / total))
            widget.focus_set()
        except TclError:
            pass

    def _sync_scroll_region(self, _event=None) -> None:
        try:
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        except TclError:
            pass

    def _sync_width_and_rows(self, event=None) -> None:
        try:
            width = event.width if event is not None else self.canvas.winfo_width()
            height = event.height if event is not None else self.canvas.winfo_height()
            self.canvas.itemconfigure(self.window_id, width=max(1, width))
            visible_cell = max(self.min_cell_height, (max(600, height) - 24) // 2)
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
