from __future__ import annotations

import os
from pathlib import Path
from tkinter import Tk

from .canonical_dashboard_mixin import CanonicalDashboardMixin
from .canonical_debug_mixin import CanonicalDebugMixin
from .canonical_help_status_mixin import CanonicalHelpStatusMixin
from .canonical_kpi_compact_mixin import CanonicalKpiCompactMixin
from .canonical_kpi_detail_mixin import CanonicalKpiDetailMixin
from .canonical_window_mixin import CanonicalWindowMixin
from .canonical_shell_workspace import CanonicalShellWorkspaceMixin
from .canonical_shell_chrome import CanonicalShellChromeMixin
from .debug_runtime import RUNTIME
from .runtime_error_hooks import (
    capture_runtime_exception,
    install_thread_debug_hook,
    tk_exception_handler,
)
from .startup_handshake import signal_ui_ready
from .ui import VideoBatchFastUI


class CanonicalVideoBatchFastUI(
    CanonicalDebugMixin,
    CanonicalKpiCompactMixin,
    CanonicalKpiDetailMixin,
    CanonicalWindowMixin,
    CanonicalShellWorkspaceMixin,
    CanonicalDashboardMixin,
    CanonicalHelpStatusMixin,
    CanonicalShellChromeMixin,
    VideoBatchFastUI,
):
    """VB-GFX-1.0 shell around the complete VideoBatch implementation."""


def run_app() -> None:
    clean_marker = os.environ.get("VIDEOBATCH_DEBUG_CLEAN_MARKER", "").strip()
    if clean_marker:
        RUNTIME.set_clean_shutdown_marker(Path(clean_marker).expanduser())
    RUNTIME.verbose(
        "Die grafische Anwendung wird aufgebaut.",
        "VideoBatch erstellt zuerst das Tk-Fenster und anschließend die kanonische Oberfläche.",
        "videobatch_fast.canonical_ui.run_app",
        "Keine Eingabe nötig. Bei einem Fehler wird sofort ein verständlicher TXT-Bericht erzeugt.",
    )
    root: Tk | None = None
    try:
        root = Tk()
        root.report_callback_exception = tk_exception_handler(root)
        install_thread_debug_hook()
        try:
            root.tk.call("tk", "scaling", max(1.0, root.winfo_fpixels("1i") / 72.0))
        except Exception as exc:
            RUNTIME.verbose(
                "Die automatische DPI-Skalierung konnte nicht vollständig gesetzt werden.",
                f"Tk meldete {type(exc).__name__}: {exc}. VideoBatch verwendet die vorhandene Skalierung.",
                "Tk scaling",
                "Keine Aktion nötig, solange Schrift und Elemente lesbar bleiben.",
                level="WARNUNG",
            )

        RUNTIME.verbose(
            "Die VideoBatch-Oberfläche wird jetzt konstruiert.",
            "Alle Mixins, Variablen, Dashboardkarten, Queueelemente und Hilfebereiche werden erzeugt.",
            "CanonicalVideoBatchFastUI(root)",
            "Bei einem Konstruktionsfehler bleibt der vollständige Python-Ort im Absturzbericht erhalten.",
        )
        CanonicalVideoBatchFastUI(root)
        root.update_idletasks()
        signal_ui_ready()
        RUNTIME.verbose(
            "Die Oberfläche hat die Startbereitschaft bestätigt.",
            "Tk konnte den vollständigen Aufbau abschließen und die UI-Ready-Markierung wurde geschrieben.",
            "startup_handshake.signal_ui_ready",
            "VideoBatch kann jetzt normal bedient werden.",
            level="OK",
        )
        root.mainloop()
        RUNTIME.mark_clean_shutdown()
    except BaseException as exc:
        capture_runtime_exception(
            type(exc),
            exc,
            exc.__traceback__,
            scope="runtime",
            fatal=True,
            where="canonical_ui.run_app · genauer Python-Ort steht im Bericht",
            root=root,
            auto_open=True,
        )
        try:
            if root is not None and root.winfo_exists():
                root.destroy()
        except Exception:
            pass
        raise SystemExit(1) from None
