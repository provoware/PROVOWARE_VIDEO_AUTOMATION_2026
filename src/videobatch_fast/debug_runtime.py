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


def _safe_cwd() -> str:
    try:
        return str(Path.cwd())
    except OSError as exc:
        return f"<Arbeitsordner nicht mehr erreichbar: {exc}>"


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
        "Arbeitsordner": _safe_cwd(),
        "Projektordner": str(PROJECT_ROOT),
        "DISPLAY": os.environ.get("DISPLAY", ""),
        "WAYLAND_DISPLAY": os.environ.get("WAYLAND_DISPLAY", ""),
        "XDG_SESSION_TYPE": os.environ.get("XDG_SESSION_TYPE", ""),
        "Safe-Mode": os.environ.get("VIDEOBATCH_SAFE_MODE", "0"),
        "Startup-Status": os.environ.get("VIDEOBATCH_STARTUP_STATUS", ""),
    }


def _writable_directory(candidate: Path) -> Path | None:
    try:
        candidate.mkdir(parents=True, exist_ok=True)
        probe = candidate / f".write-test-{os.getpid()}-{threading.get_ident()}"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return candidate
    except OSError:
        return None


class HumanDebugRuntime:
    """Stdlib-only human diagnostic channel shared by launcher and Tk app."""

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
                "Die App-Diagnose wirkt sofort; der externe Prozesswächter ist ab dem nächsten Programmstart vollständig aktiv.",
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
        preferred = Path(
            os.environ.get("VIDEOBATCH_DEBUG_DIR", DEFAULT_DEBUG_DIR)
        ).expanduser()
        state_fallback = Path(
            os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")
        ).expanduser() / APP_ID / "debugging"
        temp_fallback = Path(tempfile.gettempdir()) / f"{APP_ID}-debugging-{os.getuid()}"
        for candidate in (preferred, state_fallback, temp_fallback):
            ready = _writable_directory(candidate)
            if ready is not None:
                return ready
        raise OSError(
            "Kein beschreibbarer Debugordner verfügbar: Projekt, Benutzer-State und temporärer Ordner sind blockiert."
        )

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
        solution_list = tuple(
            str(item).strip() for item in solutions if str(item).strip()
        )
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
            lines.extend(
                f"{index}. {item}" for index, item in enumerate(solution_list, 1)
            )
        else:
            lines.append(
                "1. Bericht sichern und den letzten reproduzierbaren Schritt erneut prüfen."
            )
        lines.extend(["", "SYSTEM- UND SITZUNGSKONTEXT"])
        lines.extend(
            f"- {key}: {_safe_value(value)}" for key, value in sorted(context.items())
        )
        if exception_text:
            lines.extend(["", "TECHNISCHER FEHLER", exception_text])
        if traceback_text:
            lines.extend(
                ["", "VOLLSTÄNDIGER PYTHON-TRACEBACK", traceback_text.rstrip()]
            )
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

    def _publish_report(
        self,
        text: str,
        *,
        prefix: str,
        error_stream: bool,
        auto_open: bool,
    ) -> Path:
        try:
            path = self._write_report(text, prefix=prefix)
        except OSError as exc:
            emergency = (
                "\n[DEBUG-NOTFALL] Der Bericht konnte nicht als Datei gespeichert werden.\n"
                f"Grund: {exc}\n\n{text}\n"
            )
            print(
                emergency,
                file=sys.stderr if error_stream else sys.stdout,
                flush=True,
            )
            raise
        stream = sys.stderr if error_stream else sys.stdout
        print("\n" + text, file=stream, flush=True)
        print(f"DEBUG_REPORT={path}", file=stream, flush=True)
        if auto_open:
            _open_path(path)
        return path

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
        path = self._publish_report(
            text,
            prefix="ABSTURZ" if fatal else "FEHLER",
            error_stream=True,
            auto_open=auto_open,
        )
        return DebugIncident(
            path, text, what, how, actual_where, solution_tuple, fatal
        )

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
        path = self._publish_report(
            text,
            prefix=prefix,
            error_stream=fatal,
            auto_open=auto_open,
        )
        return DebugIncident(path, text, what, how, where, solution_tuple, fatal)

    def open_debug_folder(self) -> bool:
        try:
            directory = self._debug_dir()
        except OSError as exc:
            print(f"[DEBUG] Debugging-Ordner nicht verfügbar: {exc}", file=sys.stderr)
            return False
        return _open_path(directory)


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
        dialog.geometry("800x620")
        dialog.minsize(700, 520)
        if not owns_root:
            dialog.transient(host)
        body = ttk.Frame(dialog, padding=16)
        body.pack(fill="both", expand=True)
        ttk.Label(
            body,
            text="Fehlerdiagnose",
            font=("TkDefaultFont", 16, "bold"),
        ).pack(anchor="w")

        for title, value in (
            ("WAS?", incident.what),
            ("WIE?", incident.how),
            ("WO?", incident.where),
        ):
            row = ttk.Frame(body)
            row.pack(fill="x", pady=(8, 0))
            ttk.Label(
                row,
                text=title,
                width=9,
                font=("TkDefaultFont", 10, "bold"),
            ).pack(side="left", anchor="n")
            ttk.Label(
                row,
                text=value,
                wraplength=640,
                justify="left",
            ).pack(side="left", fill="x", expand=True)

        solutions = incident.solutions or (
            "Bericht öffnen und den letzten reproduzierbaren Schritt prüfen.",
        )
        selected_solution = tk.StringVar(value=solutions[0])
        ttk.Label(
            body,
            text="LÖSUNG?",
            font=("TkDefaultFont", 10, "bold"),
        ).pack(anchor="w", pady=(12, 3))
        solution_choice = ttk.Combobox(
            body,
            textvariable=selected_solution,
            values=list(solutions),
            state="readonly",
        )
        solution_choice.pack(fill="x")
        selected_solution_text = ttk.Label(
            body,
            textvariable=selected_solution,
            wraplength=720,
            justify="left",
        )
        selected_solution_text.pack(fill="x", anchor="w", pady=(4, 0))

        ttk.Separator(body).pack(fill="x", pady=14)
        ttk.Label(
            body,
            text=f"Bericht: {incident.path}",
            wraplength=720,
        ).pack(anchor="w")

        def copy_report() -> None:
            host.clipboard_clear()
            host.clipboard_append(incident.text)
            host.update()

        def copy_solution() -> None:
            host.clipboard_clear()
            host.clipboard_append(selected_solution.get())
            host.update()

        actions: dict[str, Callable[[], None]] = {
            "Bericht öffnen": lambda: _open_path(incident.path),
            "Debugging-Ordner öffnen": lambda: _open_path(incident.path.parent),
            "Ausgewählte Lösung kopieren": copy_solution,
            "Gesamten Bericht kopieren": copy_report,
        }
        if extra_actions:
            actions.update(extra_actions)
        actions["Dialog schließen"] = dialog.destroy

        selected_action = tk.StringVar(value=next(iter(actions)))
        ttk.Label(body, text="Interaktive Aktion auswählen:").pack(
            anchor="w", pady=(14, 3)
        )
        action_choice = ttk.Combobox(
            body,
            textvariable=selected_action,
            values=list(actions),
            state="readonly",
        )
        action_choice.pack(fill="x")

        def execute() -> None:
            action = actions.get(selected_action.get())
            if action is not None:
                action()

        ttk.Button(
            body,
            text="Ausgewählte Aktion ausführen",
            command=execute,
        ).pack(anchor="e", pady=(10, 0))
        ttk.Label(
            body,
            text=(
                "Der Bericht bleibt bevorzugt im Projektordner debugging erhalten. "
                "Nur wenn dieser nicht beschreibbar ist, wird ein sicherer lokaler Ersatzordner verwendet."
            ),
            wraplength=720,
        ).pack(anchor="w", pady=(18, 0))
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        if owns_root:
            dialog.grab_set()
            host.wait_window(dialog)
            host.destroy()
    except Exception as exc:
        print(
            f"[DEBUG] Interaktiver Fehlerdialog konnte nicht geöffnet werden: {exc}",
            file=sys.stderr,
        )
