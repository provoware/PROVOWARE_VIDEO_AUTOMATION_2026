from __future__ import annotations

from .canonical_shell_contract import DASHBOARD_COLUMN_WEIGHTS, dashboard_layout_mode


def layout_canonical_dashboard(self, width: int) -> None:
    """Lay out canonical dashboard cards without changing application state."""
    if not hasattr(self, "_dashboard_surface"):
        return
    mode = dashboard_layout_mode(width)
    cards = (
        self._dashboard_sources_card,
        self._dashboard_queue_card,
        self._dashboard_details_card,
        self._dashboard_scheduler_card,
        self._dashboard_appearance_card,
    )
    for card in cards:
        card.grid_forget()
    for column in range(3):
        self._dashboard_surface.columnconfigure(column, weight=0, minsize=0)

    if mode == "three_columns":
        for column, weight in enumerate(DASHBOARD_COLUMN_WEIGHTS):
            self._dashboard_surface.columnconfigure(column, weight=weight)
        self._dashboard_sources_card.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 6),
            pady=(0, 7),
        )
        self._dashboard_queue_card.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=6,
            pady=(0, 7),
        )
        self._dashboard_details_card.grid(
            row=0,
            column=2,
            sticky="nsew",
            padx=(6, 0),
            pady=(0, 7),
        )
        self._dashboard_scheduler_card.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="nsew",
            padx=(0, 6),
        )
        self._dashboard_appearance_card.grid(
            row=1,
            column=2,
            sticky="nsew",
            padx=(6, 0),
        )
    elif mode == "two_columns":
        self._dashboard_surface.columnconfigure(0, weight=35)
        self._dashboard_surface.columnconfigure(1, weight=65)
        self._dashboard_sources_card.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 6),
            pady=(0, 7),
        )
        self._dashboard_queue_card.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=(6, 0),
            pady=(0, 7),
        )
        self._dashboard_details_card.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="nsew",
            pady=7,
        )
        self._dashboard_scheduler_card.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=(0, 6),
            pady=(7, 0),
        )
        self._dashboard_appearance_card.grid(
            row=2,
            column=1,
            sticky="nsew",
            padx=(6, 0),
            pady=(7, 0),
        )
    else:
        self._dashboard_surface.columnconfigure(0, weight=1)
        for row, card in enumerate(cards):
            card.grid(
                row=row,
                column=0,
                sticky="nsew",
                pady=(0 if row == 0 else 7, 0),
            )

    self._dashboard_layout_mode = mode
    self._update_dashboard_wraplengths()
    self.root.after_idle(
        lambda: self._dashboard_canvas.configure(
            scrollregion=self._dashboard_canvas.bbox("all")
        )
    )
    self.root.after_idle(self._sync_dashboard_scrollbar)
