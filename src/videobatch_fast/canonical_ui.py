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


def _apply_optional_tk_scaling(root: Tk) -> None:
    """Respect the desktop's Tk scaling unless the user explicitly overrides it."""
    raw = os.environ.get("VIDEOBATCH_TK_SCALING", "").strip()
    if not raw:
        return
    try:
        value = float(raw)
        if not 0.75 <= value <= 3.0:
            raise ValueError("Wert außerhalb 0.75..3.0")
        root.tk.call("tk", "scaling", value)
        RUNTIME.verbose(
            "Manuelle Tk-Skalierung wurde angewendet.",
            f"VIDEOBATCH_TK_SCALING={value:g}",
            "canonical_ui._apply_optional_tk_scaling",
            "Ohne Umgebungsvariable verwendet VideoBatch ausschließlich die KDE/Tk-Systemskalierung.",
            level="OK",
        )
    except (TypeError, ValueError, Exception) as exc:
        RUNTIME.verbose(
            "Manuelle Tk-Skalierung wurde verworfen.",
            f"Ungültiger Wert {raw!r}: {type(exc).__name__}: {exc}",
            "canonical_ui._apply_optional_tk_scaling",
            "VIDEOBATCH_TK_SCALING entfernen oder einen Wert zwischen 0.75 und 3.0 setzen.",
            level="WARNUNG",
        )


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
        _apply_optional_tk_scaling(root)

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
    except Exception as exc:
        handled = capture_runtime_exception(
            type(exc),
            exc,
            exc.__traceback__,
            scope="runtime",
            fatal=True,
            where="canonical_ui.run_app",
            root=root,
            auto_open=True,
        )
        try:
            if root is not None and root.winfo_exists():
                root.destroy()
        except Exception:
            pass
        if not handled:
            raise
        raise SystemExit(1) from None
