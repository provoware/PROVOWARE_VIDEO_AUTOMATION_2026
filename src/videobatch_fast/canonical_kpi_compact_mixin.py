from __future__ import annotations

from tkinter import TclError, ttk


class CanonicalKpiCompactMixin:
    """Make extended KPI evidence responsive without removing its real data."""

    def _build_shell_kpis(self, parent) -> None:
        super()._build_shell_kpis(parent)
        tracked = list(getattr(self, "_shell_kpi_detail_labels", ()))
        for card in getattr(self, "_shell_kpi_cards", ()):
            for child in card.winfo_children():
                if isinstance(child, ttk.Label) and child not in tracked:
                    tracked.append(child)
                    try:
                        child.pack_configure(pady=(0, 1))
                    except TclError:
                        pass
            card.bind("<Configure>", self._compact_kpi_labels, add="+")
        self._shell_kpi_detail_labels = tracked
        self._compact_kpi_labels()

    def _compact_kpi_labels(self, _event=None) -> None:
        for card in getattr(self, "_shell_kpi_cards", ()):
            width = max(130, card.winfo_width() - 26)
            for child in card.winfo_children():
                if isinstance(child, ttk.Label):
                    try:
                        child.configure(wraplength=width)
                    except TclError:
                        return

    @staticmethod
    def _kpi_action_style(_snapshot) -> str:
        # Statusfarbe und Ursache bleiben sichtbar; der kleine Linkstil verhindert,
        # dass eine Wiederherstellungsaktion die Kartenhöhe dominiert.
        return "ShellKpiLink.TButton"
