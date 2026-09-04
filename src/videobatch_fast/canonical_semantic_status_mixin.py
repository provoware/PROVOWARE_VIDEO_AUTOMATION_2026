from __future__ import annotations

from tkinter import TclError, ttk

from .theme import COLORS, safe_text_color


_ERROR_MARKERS = (
    "fehler",
    "error",
    "kritisch",
    "abbruch",
    "fehlgeschlagen",
    "blockiert",
)
_WARNING_MARKERS = (
    "warn",
    "achtung",
    "prüf",
    "wart",
    "gelb",
    "unsicher",
)
_SUCCESS_MARKERS = (
    "bereit",
    "erfolg",
    "fertig",
    "bestanden",
    "grün",
    " ok",
    "ok ",
)


def semantic_status_state(text: str) -> str:
    """Return a presentation-only semantic state for a human-readable status."""
    normalized = f" {text.casefold().strip()} "
    if any(marker in normalized for marker in _ERROR_MARKERS):
        return "error"
    if any(marker in normalized for marker in _WARNING_MARKERS):
        return "warning"
    if any(marker in normalized for marker in _SUCCESS_MARKERS):
        return "success"
    return "neutral"


class CanonicalSemanticStatusMixin:
    """Give existing shell status text a truthful semantic colour without changing state."""

    def _configure_shell_styles(self) -> None:
        super()._configure_shell_styles()
        style = ttk.Style(self.root)
        palette = {
            "neutral": COLORS["muted"],
            "success": COLORS["success"],
            "warning": COLORS["warning"],
            "error": COLORS["danger"],
        }
        for state, color in palette.items():
            foreground = safe_text_color(COLORS["toolbar"], color)
            style.configure(
                f"ShellSemanticStatus{state.title()}.TLabel",
                background=COLORS["toolbar"],
                foreground=foreground,
                font=("DejaVu Sans", 9, "bold"),
            )
            style.configure(
                f"ShellSemanticSidebar{state.title()}.TLabel",
                background=COLORS["panel"],
                foreground=safe_text_color(COLORS["panel"], color),
                font=("DejaVu Sans", 9, "bold"),
            )

    def _semantic_status_style(self, *, sidebar: bool = False) -> str:
        state = semantic_status_state(self.status_text.get())
        prefix = "ShellSemanticSidebar" if sidebar else "ShellSemanticStatus"
        return f"{prefix}{state.title()}.TLabel"

    def _refresh_semantic_status_styles(self, *_args) -> None:
        header = getattr(self, "_semantic_header_status_label", None)
        sidebar = getattr(self, "_semantic_sidebar_status_label", None)
        try:
            if header is not None:
                header.configure(style=self._semantic_status_style())
            if sidebar is not None:
                sidebar.configure(style=self._semantic_status_style(sidebar=True))
        except TclError:
            return

    def _build_shell_sidebar(self, parent) -> None:
        before = set(parent.winfo_children())
        super()._build_shell_sidebar(parent)
        created = [widget for widget in parent.winfo_children() if widget not in before]
        for container in reversed(created):
            for child in container.winfo_children():
                try:
                    if child.winfo_class() == "TLabel" and str(child.cget("textvariable")) == str(self.status_text):
                        self._semantic_sidebar_status_label = child
                        self._refresh_semantic_status_styles()
                        return
                except TclError:
                    continue

    def _build_shell_header(self, parent) -> None:
        super()._build_shell_header(parent)
        controls = getattr(self, "_shell_header_controls", None)
        if controls is None:
            return
        for child in controls.winfo_children():
            try:
                if child.winfo_class() == "TLabel" and str(child.cget("textvariable")) == str(self.shell_header_status):
                    self._semantic_header_status_label = child
                    break
            except TclError:
                continue
        if not getattr(self, "_semantic_status_trace_installed", False):
            self.status_text.trace_add("write", self._refresh_semantic_status_styles)
            self._semantic_status_trace_installed = True
        self._refresh_semantic_status_styles()
