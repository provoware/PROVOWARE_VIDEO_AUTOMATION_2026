from __future__ import annotations

import os
import threading
from pathlib import Path
from tkinter import Tk

from .canonical_dashboard_mixin import CanonicalDashboardMixin
from .canonical_debug_mixin import CanonicalDebugMixin
from .canonical_help_status_mixin import CanonicalHelpStatusMixin
from .canonical_kpi_compact_mixin import CanonicalKpiCompactMixin
from .canonical_kpi_detail_mixin import CanonicalKpiDetailMixin
from .canonical_start_check_mixin import CanonicalStartCheckMixin
from .canonical_window_mixin import CanonicalWindowMixin
from .canonical_shell_workspace import CanonicalShellWorkspaceMixin
from .canonical_shell_chrome import CanonicalShellChromeMixin
from .debug_runtime import RUNTIME, show_incident_dialog
from .error_handling import error_definition
from .startup_handshake import signal_ui_ready
from .ui import VideoBatchFastUI
from .ui_components import SolutionDialog


class CanonicalVideoBatchFastUI(
    CanonicalDebugMixin,
    CanonicalKpiCompactMixin,
    CanonicalKpiDetailMixin,
    CanonicalWindowMixin,
    CanonicalShellWorkspaceMixin,
    CanonicalStartCheckMixin,
    CanonicalDashboardMixin,
    CanonicalHelpStatusMixin,
    CanonicalShellChromeMixin,
    VideoBatchFastUI,
):
    """VB-GFX-1.0 shell around the complete VideoBatch implementation."""


def _tk_exception_handler(root: Tk):
    def handle(exc_type, exc, tb) -> None:
        incident = RUNTIME.capture_exception(
            exc_type,
            exc,
            tb,
            what="In der laufenden Oberfläche ist ein Fehler aufgetreten.",
            how=(
                "Tkinter hat eine Ausnahme in einer Schaltfläche, einem Ereignis oder einer "
                "automatischen UI-Aktualisierung gemeldet."
            ),
            where="Tkinter-Callback · genauer Python-Ort steht im Bericht",
            solutions=(
                "Den automatisch geöffneten TXT-Bericht prüfen.",
                "Die zuletzt verwendete Schaltfläche oder Auswahl notieren und den Schritt reproduzieren.",
                "Bei Darstellungsfehlern zunächst zum Dashboard zurückkehren und die Schriftgröße auf Standard stellen.",
                "Falls die Oberfläche instabil bleibt, VideoBatch regulär schließen und neu starten.",
            ),
            fatal=False,
            auto_open=True,
        )
        if incident is not None:
            show_incident_dialog(incident, root=root)
            return
        SolutionDialog(root, error_definition("UNKNOWN"), f"{exc_type.__name__}: {exc}")

    return handle


def _install_thread_debug_hook() -> None:
    previous = threading.excepthook

    def handle(args: threading.ExceptHookArgs) -> None:
        incident = RUNTIME.capture_exception(
            args.exc_type,
            args.exc_value,
            args.exc_traceback,
            what=f"Ein Hintergrundprozess ist unerwartet abgebrochen: {args.thread.name}.",
            how="Python hat eine unbehandelte Ausnahme in einem Hintergrund-Thread gemeldet.",
            where=f"Thread: {args.thread.name}",
            solutions=(
                "Den automatisch geöffneten Bericht prüfen.",
                "Den betroffenen Auftrag nicht blind erneut starten; zuerst Ursache und Quelldateien prüfen.",
                "Falls nur eine Vorschau betroffen war, die Hauptanwendung geöffnet lassen und den Vorgang kontrolliert wiederholen.",
            ),
            fatal=False,
            auto_open=True,
        )
        if incident is None:
            previous(args)

    threading.excepthook = handle


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
        root.report_callback_exception = _tk_exception_handler(root)
        _install_thread_debug_hook()
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
        exc_type = type(exc)
        incident = RUNTIME.capture_exception(
            exc_type,
            exc,
            exc.__traceback__,
            what="VideoBatch konnte die grafische Anwendung nicht stabil weiter ausführen.",
            how=(
                "Der Fehler trat während Fensteraufbau, Oberflächenkonstruktion oder Hauptschleife auf "
                "und wurde vom zentralen Absturzfänger abgefangen."
            ),
            where="canonical_ui.run_app · genauer Python-Ort steht im Bericht",
            solutions=(
                "Den automatisch geöffneten TXT-Bericht vollständig prüfen.",
                "Im Bericht unter WO IST ES PASSIERT den Dateinamen und die Zeilennummer notieren.",
                "VideoBatch anschließend erneut über STARTEN.sh öffnen; der Starter versucht weiterhin den sicheren Startmodus.",
                "Falls derselbe Fehler erneut auftritt, den Bericht aus dem Projektordner debugging zusammen mit dem letzten Schritt verwenden.",
            ),
            fatal=True,
            auto_open=True,
        )
        if incident is not None and root is not None:
            show_incident_dialog(incident, root=root)
        try:
            if root is not None and root.winfo_exists():
                root.destroy()
        except Exception:
            pass
        raise SystemExit(1) from None
