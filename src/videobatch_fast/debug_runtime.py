from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import threading
import traceback
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import TracebackType
from typing import Any, Callable, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DEBUG_DIR = PROJECT_ROOT / "debugging"
APP_ID = "VideoBatchFast"


@dataclass(frozen=True, slots=True)
class DebugIncident:
    path: Path
    text: str
    what: str
    how: str
    where: str
    solutions: tuple[str, ...]
    fatal: bool


def _config_path() -> Path:
    base = Path(
        os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")
    ).expanduser()
    return base / APP_ID / "config.json"


def debug_enabled_from_config(default: bool = True) -> bool:
    override = os.environ.get("VIDEOBATCH_DEBUG", "").strip().lower()
    if override in {"1", "true", "yes", "on"}:
        return True
    if override in {"0", "false", "no", "off"}:
        return False
    path = _config_path()
    if not path.is_file() or path.is_symlink():
        return default
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return default
    return bool(payload.get("debug_mode", default)) if isinstance(payload, dict) else default


def _limited_tail(path: Path | None, limit: int = 16_000) -> str:
    if path is None or not path.is_file() or path.is_symlink():
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return text[-limit:]


def _safe_value(value: Any, maximum: int = 4_000) -> str:
    try:
        text = str(value)
    except Exception:
        text = "<nicht darstellbar>"
    return text if len(text) <= maximum else text[: maximum - 3] + "..."


def _open_path(path: Path) -> bool:
    opener = shutil.which("xdg-open")
    if not opener:
        return False
    try:
        subprocess.Popen(
            [opener, str(path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return True
    except OSError:
        return False


def _trace_location(tb: TracebackType | None) -> str:
    if tb is None:
        return "Kein Python-Traceback verfügbar."
    frames = traceback.extract_tb(tb)
    if not frames:
        return "Kein Python-Traceback verfügbar."
    frame = frames[-1]
    return f"{frame.filename}:{frame.lineno} · {frame.name}()"


def _system_context() -> dict[str, str]:
    return {
        "Zeit": datetime.now().astimezone().isoformat(timespec="seconds"),
        "PID": str(os.getpid()),
        "Python": sys.version.replace("\n", " "),
        "Interpreter": sys.executable,
        "System": platform.platform(),
        "Architektur": platform.machine(),
        "Arbeitsordner": str(Path.cwd()),
        "Projektordner": str(PROJECT_ROOT),
        "DISPLAY": os.environ.get("DISPLAY", ""),
        "WAYLAND_DISPLAY": os.environ.get("WAYLAND_DISPLAY", ""),
        "XDG_SESSION_TYPE": os.environ.get("XDG_SESSION_TYPE", ""),
        "Safe-Mode": os.environ.get("VIDEOBATCH_SAFE_MODE", "0"),
        "Startup-Status": os.environ.get("VIDEOBATCH_STARTUP_STATUS", ""),
    }


class HumanDebugRuntime:
    """Small stdlib-only debug channel shared by launcher and Tk application."""

    def __init__(self) -> None:
        self.enabled = debug_enabled_from_config()
        self._history: deque[str] = deque(maxlen=160)
        self._lock = threading.RLock()
        self._context_provider: Callable[[], dict[str, Any]] | None = None
        self._clean_shutdown_marker: Path | None = None

    def set_enabled(self, enabled: bool) -> None:
        with self._lock:
            previous = self.enabled
            self.enabled = bool(enabled)
        if previous and not self.enabled:
            print(
                "[DEBUG] Debugmodus wurde im Tool ausgeschaltet. "
                "Die ausführliche Konsolenausgabe ist ab jetzt deaktiviert.",
                flush=True,
            )
        elif not previous and self.enabled:
            self.verbose(
                "Debugmodus wurde eingeschaltet.",
                "VideoBatch protokolliert Start, Fehlerorte und Lösungsmöglichkeiten wieder ausführlich.",
                "Benutzereinstellung · Debugmodus",
                "Keine Aktion nötig. Bei einem Fehler wird automatisch ein TXT-Bericht erzeugt.",
            )

    def set_context_provider(self, provider: Callable[[], dict[str, Any]] | None) -> None:
        self._context_provider = provider

    def set_clean_shutdown_marker(self, path: Path | None) -> None:
        self._clean_shutdown_marker = path

    def mark_clean_shutdown(self) -> None:
        marker = self._clean_shutdown_marker
        if marker is None:
            return
        try:
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text(
                datetime.now().astimezone().isoformat(timespec="seconds") + "\n",
                encoding="utf-8",
            )
        except OSError:
            pass

    def verbose(
        self,
        what: str,
        how: str,
        where: str,
        solution: str,
        *,
        level: str = "DEBUG",
    ) -> None:
        if not self.enabled:
            return
        stamp = datetime.now().strftime("%H:%M:%S")
        block = (
            f"\n[{level} {stamp}]\n"
            f"WAS?    {what}\n"
            f"WIE?    {how}\n"
            f"WO?     {where}\n"
            f"LÖSUNG? {solution}\n"
        )
        with self._lock:
            self._history.append(block.rstrip())
        print(block, flush=True)

    def _debug_dir(self) -> Path:
        preferred = Path(os.environ.get("VIDEOBATCH_DEBUG_DIR", DEFAULT_DEBUG_DIR)).expanduser()
        try:
            preferred.mkdir(parents=True, exist_ok=True)
            probe = preferred / ".write-test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return preferred
        except OSError:
            fallback = Path(
                os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")
            ).expanduser() / APP_ID / "debugging"
            fallback.mkdir(parents=True, exist_ok=True)
            return fallback

    def _context(self, extra: dict[str, Any] | None) -> dict[str, Any]:
        result: dict[str, Any] = dict(_system_context())
        provider = self._context_provider
        if provider is not None:
            try:
                supplied = provider()
                if isinstance(supplied, dict):
                    result.update(supplied)
            except Exception as exc:
                result["Kontextfehler"] = f"{type(exc).__name__}: {exc}"
        if extra:
            result.update(extra)
        return result

    def _write_report(self, text: str, *, prefix: str) -> Path:
        directory = self._debug_dir()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        target = directory / f"{prefix}_{stamp}_pid-{os.getpid()}.txt"
        fd, temporary_name = tempfile.mkstemp(
            prefix=f".{target.name}.", suffix=".tmp", dir=directory
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
        return target

    def _render_report(
        self,
        *,
        what: str,
        how: str,
        where: str,
        solutions: Iterable[str],
        fatal: bool,
        exception_text: str = "",
        traceback_text: str = "",
        extra_context: dict[str, Any] | None = None,
    ) -> str:
        solution_list = tuple(str(item).strip() for item in solutions if str(item).strip())
        context = self._context(extra_context)
        bootstrap_log = _limited_tail(
            Path(os.environ["VIDEOBATCH_BOOTSTRAP_LOG"])
            if os.environ.get("VIDEOBATCH_BOOTSTRAP_LOG")
            else None
        )
        startup_report = _limited_tail(
            Path(os.environ["VIDEOBATCH_STARTUP_REPORT"])
            if os.environ.get("VIDEOBATCH_STARTUP_REPORT")
            else None
        )
        with self._lock:
            history = "\n".join(self._history)

        lines = [
            "VIDEOBATCH FAST · MENSCHLICHER DEBUG- UND ABSTURZBERICHT",
            "=" * 72,
            f"Schweregrad: {'ABSTURZ / FATAL' if fatal else 'FEHLER / WEITERARBEIT MÖGLICH'}",
            "",
            "WAS IST PASSIERT?",
            what,
            "",
            "WIE WURDE ES ERKANNT?",
            how,
            "",
            "WO IST ES PASSIERT?",
            where,
            "",
            "LÖSUNGSMÖGLICHKEITEN",
        ]
        if solution_list:
            lines.extend(f"{index}. {item}" for index, item in enumerate(solution_list, 1))
        else:
            lines.append("1. Bericht sichern und den letzten reproduzierbaren Schritt erneut prüfen.")
        lines.extend(["", "SYSTEM- UND SITZUNGSKONTEXT"])
        lines.extend(f"- {key}: {_safe_value(value)}" for key, value in sorted(context.items()))
        if exception_text:
            lines.extend(["", "TECHNISCHER FEHLER", exception_text])
        if traceback_text:
            lines.extend(["", "VOLLSTÄNDIGER PYTHON-TRACEBACK", traceback_text.rstrip()])
        if history:
            lines.extend(["", "LETZTE DEBUG-SCHRITTE", history])
        if bootstrap_log:
            lines.extend(["", "LETZTER BOOTSTRAP-LOGAUSSCHNITT", bootstrap_log])
        if startup_report:
            lines.extend(["", "LETZTER STARTUP-REPORT", startup_report])
        lines.extend(
            [
                "",
                "HINWEIS",
                "Dieser Bericht wurde lokal erzeugt. Er wurde nicht automatisch hochgeladen oder versendet.",
                "",
            ]
        )
        return "\n".join(lines)

    def capture_exception(
        self,
        exc_type: type[BaseException],
        exc: BaseException,
        tb: TracebackType | None,
        *,
        what: str,
        how: str,
        where: str = "",
        solutions: Iterable[str] = (),
        fatal: bool = True,
        extra_context: dict[str, Any] | None = None,
        auto_open: bool = True,
        force: bool = False,
    ) -> DebugIncident | None:
        if not self.enabled and not force:
            return None
        actual_where = where.strip() or _trace_location(tb)
        technical = f"{exc_type.__name__}: {exc}"
        trace = "".join(traceback.format_exception(exc_type, exc, tb))
        solution_tuple = tuple(solutions)
        text = self._render_report(
            what=what,
            how=how,
            where=actual_where,
            solutions=solution_tuple,
            fatal=fatal,
            exception_text=technical,
            traceback_text=trace,
            extra_context=extra_context,
        )
        path = self._write_report(text, prefix="ABSTURZ" if fatal else "FEHLER")
        print("\n" + text, file=sys.stderr, flush=True)
        print(f"DEBUG_REPORT={path}", file=sys.stderr, flush=True)
        if auto_open:
            _open_path(path)
        return DebugIncident(path, text, what, how, actual_where, solution_tuple, fatal)

    def capture_message(
        self,
        *,
        what: str,
        how: str,
        where: str,
        solutions: Iterable[str] = (),
        fatal: bool = False,
        extra_context: dict[str, Any] | None = None,
        auto_open: bool = True,
        force: bool = False,
        prefix: str = "DEBUGBERICHT",
    ) -> DebugIncident | None:
        if not self.enabled and not force:
            return None
        solution_tuple = tuple(solutions)
        text = self._render_report(
            what=what,
            how=how,
            where=where,
            solutions=solution_tuple,
            fatal=fatal,
            extra_context=extra_context,
        )
        path = self._write_report(text, prefix=prefix)
        print("\n" + text, flush=True)
        print(f"DEBUG_REPORT={path}", flush=True)
        if auto_open:
            _open_path(path)
        return DebugIncident(path, text, what, how, where, solution_tuple, fatal)

    def open_debug_folder(self) -> bool:
        return _open_path(self._debug_dir())


RUNTIME = HumanDebugRuntime()


def show_incident_dialog(
    incident: DebugIncident,
    *,
    root: Any = None,
    extra_actions: dict[str, Callable[[], None]] | None = None,
) -> None:
    if not RUNTIME.enabled:
        return
    if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        return
    try:
        import tkinter as tk
        from tkinter import ttk
    except ImportError:
        return

    owns_root = root is None
    try:
        host = root if root is not None else tk.Tk()
        if owns_root:
            host.withdraw()
        dialog = tk.Toplevel(host)
        dialog.title("VideoBatch · Fehlerdiagnose")
        dialog.geometry("780x560")
        dialog.minsize(680, 480)
        dialog.transient(host if not owns_root else None)
        body = ttk.Frame(dialog, padding=16)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Fehlerdiagnose", font=("TkDefaultFont", 16, "bold")).pack(anchor="w")

        for title, value in (
            ("WAS?", incident.what),
            ("WIE?", incident.how),
            ("WO?", incident.where),
            ("LÖSUNG?", incident.solutions[0] if incident.solutions else "Bericht prüfen."),
        ):
            row = ttk.Frame(body)
            row.pack(fill="x", pady=(8, 0))
            ttk.Label(row, text=title, width=9, font=("TkDefaultFont", 10, "bold")).pack(side="left", anchor="n")
            ttk.Label(row, text=value, wraplength=620, justify="left").pack(side="left", fill="x", expand=True)

        ttk.Separator(body).pack(fill="x", pady=14)
        ttk.Label(body, text=f"Bericht: {incident.path}", wraplength=710).pack(anchor="w")

        actions: dict[str, Callable[[], None]] = {
            "Bericht öffnen": lambda: _open_path(incident.path),
            "Debugging-Ordner öffnen": lambda: _open_path(incident.path.parent),
            "Bericht in Zwischenablage kopieren": lambda: (
                host.clipboard_clear(), host.clipboard_append(incident.text), host.update()
            ),
        }
        if extra_actions:
            actions.update(extra_actions)
        actions["Dialog schließen"] = dialog.destroy

        selected = tk.StringVar(value=next(iter(actions)))
        ttk.Label(body, text="Aktion auswählen:").pack(anchor="w", pady=(12, 3))
        choice = ttk.Combobox(body, textvariable=selected, values=list(actions), state="readonly")
        choice.pack(fill="x")

        def execute() -> None:
            action = actions.get(selected.get())
            if action is not None:
                action()

        ttk.Button(body, text="Ausgewählte Aktion ausführen", command=execute).pack(anchor="e", pady=(10, 0))
        ttk.Label(
            body,
            text="Der Bericht bleibt im Projektordner unter debugging erhalten.",
            wraplength=710,
        ).pack(anchor="w", pady=(18, 0))
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        if owns_root:
            dialog.grab_set()
            host.wait_window(dialog)
            host.destroy()
    except Exception as exc:
        print(f"[DEBUG] Interaktiver Fehlerdialog konnte nicht geöffnet werden: {exc}", file=sys.stderr)
