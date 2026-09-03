from __future__ import annotations

import sys
import threading
import time
from dataclasses import replace
from typing import Any

from .debug_runtime import RUNTIME, show_incident_dialog
from .error_handling import error_definition
from .runtime_error_guidance import (
    classify_runtime_exception,
    exception_fingerprint,
    exception_location,
)
from .ui_components import SolutionDialog

_DEDUP_WINDOW_SECONDS = 12.0
_recent_fingerprints: dict[str, float] = {}
_dedup_lock = threading.RLock()
_thread_hook_lock = threading.RLock()
_thread_hook_installed = False


def _claim_fingerprint(fingerprint: str) -> bool:
    """Return True once per short incident window and prune stale fingerprints."""
    now = time.monotonic()
    cutoff = now - (_DEDUP_WINDOW_SECONDS * 4.0)
    with _dedup_lock:
        stale = [key for key, stamp in _recent_fingerprints.items() if stamp < cutoff]
        for key in stale:
            _recent_fingerprints.pop(key, None)
        previous = _recent_fingerprints.get(fingerprint)
        if previous is not None and now - previous < _DEDUP_WINDOW_SECONDS:
            return False
        _recent_fingerprints[fingerprint] = now
        return True


def _release_fingerprint(fingerprint: str) -> None:
    """Allow normal fallback handling when no report or dialog was produced."""
    with _dedup_lock:
        _recent_fingerprints.pop(fingerprint, None)


def capture_runtime_exception(
    exc_type: type[BaseException],
    exc: BaseException,
    tb,
    *,
    scope: str,
    fatal: bool,
    where: str,
    root: Any = None,
    auto_open: bool = True,
) -> bool:
    """Classify, deduplicate, report and optionally display one runtime exception."""
    guidance = classify_runtime_exception(exc_type, exc, scope=scope)
    fingerprint = exception_fingerprint(exc_type, exc, tb, scope=scope)
    trace_where = exception_location(tb)
    actual_where = f"{where} · {trace_where}" if where and trace_where else (trace_where or where)
    if not _claim_fingerprint(fingerprint):
        RUNTIME.verbose(
            "Ein bereits gemeldeter Fehler wurde erneut erkannt.",
            f"Fehlercode {guidance.code}, Fingerprint {fingerprint}. Ein weiterer Bericht/Dialog wird unterdrückt.",
            actual_where,
            "Die erste Meldung verwenden; identische Wiederholungen werden nach kurzer Zeit wieder zugelassen.",
            level="WARNUNG",
        )
        return True

    technical = f"{exc_type.__name__}: {exc}"
    try:
        incident = RUNTIME.capture_exception(
            exc_type,
            exc,
            tb,
            what=guidance.what,
            how=guidance.how,
            where=actual_where,
            solutions=guidance.solutions,
            fatal=fatal,
            auto_open=auto_open,
            extra_context={
                "Fehlercode": guidance.code,
                "Fehler-Fingerprint": fingerprint,
                "Fehlerbereich": scope,
                "Klassifizierter Schweregrad": guidance.severity,
            },
        )
    except Exception as report_exc:
        print(
            "[FEHLER-NOTFALL] Der zentrale Fehlerbericht selbst ist fehlgeschlagen: "
            f"{type(report_exc).__name__}: {report_exc}; Ursprungsfehler: {technical}",
            file=sys.stderr,
            flush=True,
        )
        incident = None

    handled = incident is not None
    if root is not None:
        if incident is not None:
            try:
                dialog_incident = replace(
                    incident,
                    how=(
                        f"{incident.how}\n"
                        f"Fehlercode: {guidance.code}\n"
                        f"Fehler-Fingerprint: {fingerprint}"
                    ),
                )
                show_incident_dialog(dialog_incident, root=root)
                return True
            except Exception as dialog_exc:
                print(
                    "[FEHLER-NOTFALL] Der Fehlerdialog konnte nicht geöffnet werden: "
                    f"{type(dialog_exc).__name__}: {dialog_exc}",
                    file=sys.stderr,
                    flush=True,
                )
        try:
            SolutionDialog(root, error_definition(guidance.code), technical)
            return True
        except Exception as fallback_exc:
            print(
                "[FEHLER-NOTFALL] Auch der Ersatzdialog ist fehlgeschlagen: "
                f"{type(fallback_exc).__name__}: {fallback_exc}",
                file=sys.stderr,
                flush=True,
            )

    if handled:
        return True

    _release_fingerprint(fingerprint)
    return False


def tk_exception_handler(root: Any):
    """Return the one canonical Tk callback error handler used by all UI entry points."""

    def handle(exc_type, exc, tb) -> None:
        capture_runtime_exception(
            exc_type,
            exc,
            tb,
            scope="tkinter",
            fatal=False,
            where="Tkinter-Callback",
            root=root,
            auto_open=True,
        )

    return handle


def install_thread_debug_hook() -> None:
    """Install exactly one process-wide background-thread exception bridge."""
    global _thread_hook_installed
    with _thread_hook_lock:
        if _thread_hook_installed:
            return
        previous = threading.excepthook

        def handle(args: threading.ExceptHookArgs) -> None:
            if not issubclass(args.exc_type, Exception):
                previous(args)
                return
            try:
                handled = capture_runtime_exception(
                    args.exc_type,
                    args.exc_value,
                    args.exc_traceback,
                    scope="thread",
                    fatal=False,
                    where=f"Thread: {args.thread.name}",
                    root=None,
                    auto_open=True,
                )
            except BaseException:
                handled = False
            if not handled:
                previous(args)

        threading.excepthook = handle
        _thread_hook_installed = True
