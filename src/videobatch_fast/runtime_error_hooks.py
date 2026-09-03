from __future__ import annotations

from typing import Any

from .debug_runtime import RUNTIME, show_incident_dialog
from .error_handling import error_definition
from .ui_components import SolutionDialog


def tk_exception_handler(root: Any):
    """Return the one canonical Tk callback error handler used by all UI entry points."""
    def handle(exc_type, exc, tb) -> None:
        incident = RUNTIME.capture_exception(
            exc_type,
            exc,
            tb,
            what="In der laufenden Oberfläche ist ein Fehler aufgetreten.",
            how="Tkinter hat eine Ausnahme in einer Bedienaktion oder UI-Aktualisierung gemeldet.",
            where="Tkinter-Callback",
            solutions=(
                "Den automatisch erzeugten Bericht prüfen.",
                "Die zuletzt verwendete Aktion einmal kontrolliert reproduzieren.",
                "Falls die betroffene Oberfläche instabil wirkt, VideoBatch regulär neu starten.",
            ),
            fatal=False,
            auto_open=True,
            scope="tkinter",
        )
        if incident is not None:
            show_incident_dialog(incident, root=root)
            return
        SolutionDialog(
            root,
            error_definition("RUNTIME_UNHANDLED_EXCEPTION"),
            f"{exc_type.__name__}: {exc}",
        )

    return handle
