#!/usr/bin/env python3
from __future__ import annotations

import fcntl
import json
import os
import queue
import shlex
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from videobatch_fast.ffmpeg_capabilities import (  # noqa: E402
    encoder_smoke_test,
    read_ffmpeg_capabilities,
)
from videobatch_fast.linux_installation import normalize_linux_installation  # noqa: E402
from videobatch_fast.probe import ffmpeg_path, ffprobe_path  # noqa: E402
from videobatch_fast.startup_handshake import read_ready_marker  # noqa: E402

CHECK_ONLY = "--check-only" in sys.argv
if CHECK_ONLY:
    sys.argv.remove("--check-only")
STATE = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "VideoBatchFast"
LOG_DIR = STATE / "logs"
TOOLCHAIN = ROOT / "scripts" / "toolchain.py"
STARTUP_CONTRACT = ROOT / "STARTUP_CONTRACT.json"

SYSTEM_PACKAGES = (
    "python3",
    "python3-venv",
    "ffmpeg",
    "wl-clipboard",
    "xdg-utils",
    "xdg-desktop-portal",
    "xdg-desktop-portal-kde",
    "libnotify-bin",
    "libegl1",
    "libgl1",
    "libfontconfig1",
    "libwayland-client0",
    "libxkbcommon0",
)

REQUIRED_FFMPEG_FILTERS = frozenset({"eq", "fade", "fps", "pad", "scale", "setpts", "trim", "xfade", "concat"})


class BootstrapFailure(RuntimeError):
    pass


class EventSink:
    def __init__(self, events: queue.Queue[tuple[str, Any]], log_path: Path) -> None:
        self.events = events
        self.log_path = log_path
        self._lock = threading.Lock()

    def log(self, text: str) -> None:
        with self._lock:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a", encoding="utf-8", errors="replace") as handle:
                handle.write(text.rstrip() + "\n")

    def stage(self, number: int, message: str) -> None:
        self.log(f"STAGE {number}: {message}")
        self.events.put(("stage", (number, message)))

    def done(self, pid: int, safe_mode: bool) -> None:
        self.events.put(("done", (pid, safe_mode)))

    def failed(self, message: str) -> None:
        self.log("FAILED: " + message)
        self.events.put(("failed", message))


class KDialogProgress:
    """Stdlib-only bootstrap UI for Kubuntu before the private PySide6 runtime exists."""

    def __init__(self) -> None:
        self.kdialog = shutil.which("kdialog")
        self.qdbus = next(
            (path for name in ("qdbus6", "qdbus-qt6", "qdbus") if (path := shutil.which(name))),
            None,
        )
        self.dbus_ref: tuple[str, ...] = ()

    @property
    def available(self) -> bool:
        return bool(self.kdialog and os.environ.get("WAYLAND_DISPLAY"))

    def open(self) -> bool:
        if not self.available:
            return False
        if self.qdbus:
            try:
                completed = subprocess.run(
                    [
                        str(self.kdialog),
                        "--title",
                        "VideoBatch Fast startet",
                        "--progressbar",
                        "VideoBatch wird sicher vorbereitet …",
                        "4",
                    ],
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    timeout=10,
                    check=False,
                )
                if completed.returncode == 0:
                    self.dbus_ref = tuple(completed.stdout.strip().split())
            except (OSError, subprocess.SubprocessError):
                self.dbus_ref = ()
        self.stage(0, "VideoBatch wird sicher vorbereitet …")
        return True

    def _dbus_call(self, *args: str) -> bool:
        if not self.qdbus or not self.dbus_ref:
            return False
        try:
            completed = subprocess.run(
                [str(self.qdbus), *self.dbus_ref, *args],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
                check=False,
            )
            return completed.returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False

    def _popup(self, message: str, seconds: int = 2) -> None:
        if not self.kdialog:
            return
        try:
            subprocess.Popen(
                [
                    str(self.kdialog),
                    "--title",
                    "VideoBatch Fast",
                    "--passivepopup",
                    message,
                    str(seconds),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except OSError:
            pass

    def stage(self, number: int, message: str) -> None:
        if self.dbus_ref:
            changed = self._dbus_call("Set", "", "value", str(max(0, min(4, number))))
            changed = self._dbus_call("setLabelText", message) and changed
            if changed:
                return
            self.dbus_ref = ()
        self._popup(f"[{max(0, min(4, number))}/4] {message}")

    def success(self, safe_mode: bool) -> None:
        label = "Sicherer Startmodus ist geöffnet." if safe_mode else "VideoBatch ist startbereit."
        self.stage(4, label)
        time.sleep(0.25)
        self.close()
        self._popup(label, 3)

    def error(self, message: str, log_path: Path) -> None:
        self.close()
        if not self.kdialog:
            return
        text = f"{message}\n\nDiagnoseprotokoll:\n{log_path}"
        try:
            subprocess.run(
                [str(self.kdialog), "--title", "VideoBatch · Startfehler", "--error", text],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=120,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            pass

    def close(self) -> None:
        if self.dbus_ref:
            self._dbus_call("close")
        self.dbus_ref = ()


def run_logged(command: list[str], sink: EventSink, *, timeout: int = 1800) -> subprocess.CompletedProcess[str]:
    sink.log("$ " + " ".join(shlex.quote(part) for part in command))
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
            errors="replace",
        )
    except subprocess.TimeoutExpired as exc:
        sink.log(f"TIMEOUT after {timeout}s")
        raise BootstrapFailure("Die automatische Vorbereitung hat das Zeitlimit überschritten.") from exc
    except OSError as exc:
        raise BootstrapFailure(f"Ein benötigter Prozess konnte nicht gestartet werden: {exc}") from exc
    sink.log(completed.stdout or "(keine Prozessausgabe)")
    return completed


def acquire_lock(wait_seconds: float = 45.0) -> Any:
    """Serialize concurrent double-clicks instead of showing a second error."""
    lock_dir = STATE / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    handle = (lock_dir / "bootstrap.lock").open("a+", encoding="utf-8")
    deadline = time.monotonic() + max(0.0, wait_seconds)
    while True:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return handle
        except BlockingIOError:
            if time.monotonic() >= deadline:
                handle.close()
                return None
            time.sleep(0.25)


def verify_project() -> None:
    required = (
        "VERSION.json",
        "TOOLCHAIN_CONTRACT.json",
        "STARTUP_CONTRACT.json",
        "scripts/toolchain.py",
        "scripts/startup_check.py",
        "src/videobatch_fast/qt_phase3.py",
        "src/videobatch_fast/linux_installation.py",
    )
    missing = [name for name in required if not (ROOT / name).is_file()]
    if missing:
        raise BootstrapFailure("Das Programmpaket ist unvollständig: " + ", ".join(missing))


def load_startup_contract() -> dict[str, Any]:
    try:
        contract = json.loads(STARTUP_CONTRACT.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BootstrapFailure(f"Der Startvertrag ist unlesbar: {exc}") from exc
    if contract.get("schema_version") != 1:
        raise BootstrapFailure("Der Startvertrag besitzt eine unbekannte Version.")
    policy = contract.get("policy", {})
    required_true = (
        "interactive_questions_forbidden",
        "quality_tools_must_not_block_application_start",
        "real_encoder_smoke_test_is_authoritative",
        "runtime_environment_is_content_addressed",
        "runtime_environment_must_not_be_moved_after_creation",
        "ui_ready_handshake_required",
        "normal_start_retried_in_safe_mode",
        "existing_instance_is_focused_instead_of_rejected",
        "runtime_ready_marker_is_auto_repairable",
        "startup_probe_never_blocks_ui_launch",
        "system_python_runtime_fallback_allowed",
        "system_fallback_forces_safe_mode",
        "system_dependencies_checked_on_every_start",
        "missing_system_dependencies_offer_graphical_auto_repair",
        "system_dependency_repair_uses_kubuntu_package_manager",
        "system_dependency_repair_requires_post_validation",
        "system_dependency_repair_never_uses_unattended_sudo",
    )
    missing = [name for name in required_true if policy.get(name) is not True]
    if missing:
        raise BootstrapFailure("Der Startvertrag verletzt Pflichtregeln: " + ", ".join(missing))
    return contract


def _missing_system_packages(sink: EventSink) -> list[str]:
    dpkg_query = shutil.which("dpkg-query")
    if not dpkg_query:
        sink.log("SYSTEM DEPENDENCY CHECK skipped: dpkg-query fehlt")
        return []
    completed = run_logged(
        [dpkg_query, "-W", "-f=${binary:Package}\t${Status}\n", *SYSTEM_PACKAGES],
        sink,
        timeout=20,
    )
    installed: set[str] = set()
    for line in completed.stdout.splitlines():
        try:
            package, status = line.split("\t", 1)
        except ValueError:
            continue
        if status.strip() == "install ok installed":
            installed.add(package.split(":", 1)[0])
    return [package for package in SYSTEM_PACKAGES if package not in installed]

def _ffmpeg_stack_issues() -> list[str]:
    issues: list[str] = []
    ffmpeg = ffmpeg_path()
    if not ffmpeg:
        issues.append("FFmpeg fehlt")
    if not ffprobe_path():
        issues.append("FFprobe fehlt")
    if not ffmpeg:
        return issues

    read_ffmpeg_capabilities.cache_clear()
    encoder_smoke_test.cache_clear()
    capabilities = read_ffmpeg_capabilities(ffmpeg)
    if capabilities.error:
        issues.append(capabilities.error)
    else:
        missing_filters = REQUIRED_FFMPEG_FILTERS - capabilities.filters
        if missing_filters:
            issues.append("FFmpeg-Kernfilter fehlen: " + ", ".join(sorted(missing_filters)))
    aac_ok, detail = encoder_smoke_test(ffmpeg, "aac", "audio")
    if not aac_ok:
        issues.append("AAC-Kurztest fehlgeschlagen" + (f": {detail}" if detail else ""))
    return issues

def _confirm_online_system_repair(packages: list[str], sink: EventSink) -> bool:
    if not packages:
        return False
    kdialog = shutil.which("kdialog")
    if not kdialog or not os.environ.get("WAYLAND_DISPLAY"):
        sink.log("SYSTEM DEPENDENCY REPAIR skipped: keine grafische Wayland-Freigabe verfügbar")
        return False
    message = (
        "VideoBatch hat fehlende Systemabhängigkeiten erkannt:\n\n"
        + ", ".join(packages)
        + "\n\nDie fehlenden Pakete jetzt automatisch über die Kubuntu-Paketverwaltung reparieren?"
    )
    try:
        completed = subprocess.run(
            [
                kdialog,
                "--title",
                "VideoBatch · System automatisch reparieren",
                "--yes-label",
                "Online reparieren",
                "--no-label",
                "Offline bleiben",
                "--yesno",
                message,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        sink.log(f"SYSTEM DEPENDENCY REPAIR confirmation failed: {exc}")
        return False
    return completed.returncode == 0


def ensure_system_dependencies(sink: EventSink) -> bool:
    """Repair missing or functionally broken Kubuntu dependencies once."""
    missing = _missing_system_packages(sink)
    media_issues = _ffmpeg_stack_issues()
    if not missing and not media_issues:
        sink.log("SYSTEM DEPENDENCIES VERIFIED")
        return True
    if missing:
        sink.log("SYSTEM DEPENDENCIES MISSING: " + ", ".join(missing))
    if media_issues:
        sink.log("MEDIA STACK ISSUES: " + " | ".join(media_issues))
    repair_packages = list(missing)
    if media_issues and "ffmpeg" not in repair_packages:
        repair_packages.append("ffmpeg")
    if not _confirm_online_system_repair(repair_packages, sink):
        return False

    apt_get = shutil.which("apt-get")
    if not apt_get:
        sink.log("SYSTEM DEPENDENCY REPAIR failed: apt-get fehlt")
        return False
    if os.geteuid() == 0:
        prefix: list[str] = []
    else:
        pkexec = shutil.which("pkexec")
        if not pkexec:
            sink.log("SYSTEM DEPENDENCY REPAIR failed: pkexec fehlt")
            return False
        prefix = [pkexec]

    update = run_logged([*prefix, apt_get, "update"], sink, timeout=900)
    if update.returncode != 0:
        sink.log("SYSTEM DEPENDENCY REPAIR failed during apt-get update")
        return False
    if missing:
        install = run_logged(
            [*prefix, apt_get, "install", "-y", "--no-install-recommends", *missing],
            sink,
            timeout=1800,
        )
        if install.returncode != 0:
            sink.log("SYSTEM DEPENDENCY REPAIR failed during apt-get install")
            return False
    if media_issues and "ffmpeg" not in missing:
        reinstall = run_logged(
            [*prefix, apt_get, "install", "--reinstall", "-y", "--no-install-recommends", "ffmpeg"],
            sink,
            timeout=1800,
        )
        if reinstall.returncode != 0:
            sink.log("SYSTEM DEPENDENCY REPAIR failed during FFmpeg reinstall")
            return False

    remaining = _missing_system_packages(sink)
    remaining_media = _ffmpeg_stack_issues()
    if remaining or remaining_media:
        detail = ", ".join(remaining) if remaining else "Pakete vollständig"
        if remaining_media:
            detail += " | " + " | ".join(remaining_media)
        sink.log("SYSTEM DEPENDENCY REPAIR incomplete: " + detail)
        return False
    sink.log("SYSTEM DEPENDENCY REPAIR VERIFIED")
    return True

def install_user_launchers(sink: EventSink) -> None:
    """Maintain exactly one XDG menu entry and one stable user launcher."""
    try:
        launcher_value = os.environ.get("VIDEOBATCH_PORTABLE_LAUNCHER", "").strip()
        launcher = Path(launcher_value).expanduser().resolve() if launcher_value else (ROOT / "start.sh").resolve()
        report = normalize_linux_installation(project_root=ROOT, launcher=launcher)
        sink.log("INSTALLATION_HYGIENE " + json.dumps(report, ensure_ascii=False, sort_keys=True))
    except (OSError, RuntimeError, ValueError) as exc:
        sink.log(f"Launcher-/Installationsbereinigung übersprungen: {exc}")


def toolchain_python(scope: str, sink: EventSink) -> Path:
    completed = run_logged([sys.executable, str(TOOLCHAIN), "path", "--scope", scope, "--quiet"], sink, timeout=60)
    if completed.returncode:
        raise BootstrapFailure("Der Laufzeitpfad konnte nicht bestimmt werden.")
    try:
        value = completed.stdout.strip().splitlines()[-1]
    except IndexError as exc:
        raise BootstrapFailure("Der Laufzeitpfad ist leer.") from exc
    return Path(value)


def system_runtime_fallback(sink: EventSink) -> Path | None:
    """Use the system interpreter only as a verified, degraded last-known-safe path."""
    code = (
        "import cryptography,cffi,pycparser; "
        "from PIL import Image; "
        "from PySide6 import QtCore,QtGui,QtWidgets; "
        "assert QtCore.qVersion(); "
        "print('SYSTEM_RUNTIME_FALLBACK_OK')"
    )
    completed = run_logged([sys.executable, "-c", code], sink, timeout=60)
    if completed.returncode == 0 and "SYSTEM_RUNTIME_FALLBACK_OK" in completed.stdout:
        sink.log("SYSTEM RUNTIME FALLBACK VERIFIED")
        return Path(sys.executable).resolve()
    return None


def _portable_runtime(sink: EventSink) -> Path | None:
    if os.environ.get("VIDEOBATCH_PORTABLE") != "1":
        return None
    code = (
        "import cryptography,cffi,pycparser; "
        "from PIL import Image; "
        "from PySide6 import QtCore,QtGui,QtWidgets; "
        "assert QtCore.qVersion(); "
        "print('PORTABLE_RUNTIME_VERIFIED')"
    )
    completed = run_logged([sys.executable, "-c", code], sink, timeout=60)
    if completed.returncode or "PORTABLE_RUNTIME_VERIFIED" not in completed.stdout:
        raise BootstrapFailure("Die eingebettete portable Laufzeit ist beschädigt.")
    sink.log("PORTABLE RUNTIME VERIFIED")
    return Path(sys.executable).resolve()


def ensure_runtime(sink: EventSink, *, maximum_attempts: int = 2) -> tuple[Path, bool]:
    portable = _portable_runtime(sink)
    if portable is not None:
        return portable, False
    base = [sys.executable, str(TOOLCHAIN), "prepare", "--scope", "runtime", "--auto-repair", "--quiet"]
    completed = run_logged(base, sink)
    attempt = 1
    while completed.returncode and attempt < max(1, maximum_attempts):
        attempt += 1
        sink.log(f"Laufzeitaufbau Versuch {attempt - 1} fehlgeschlagen; kontrollierter Neuaufbau folgt.")
        completed = run_logged([*base, "--replace"], sink)
    if completed.returncode:
        fallback = system_runtime_fallback(sink)
        if fallback is not None:
            return fallback, True
        raise BootstrapFailure("Die Laufzeit konnte nach allen automatischen Reparaturversuchen nicht verifiziert werden.")
    python = toolchain_python("runtime", sink)
    check = run_logged([str(python), str(TOOLCHAIN), "gate", "--scope", "runtime", "--quiet"], sink, timeout=120)
    if check.returncode:
        fallback = system_runtime_fallback(sink)
        if fallback is not None:
            return fallback, True
        raise BootstrapFailure("Die neue Laufzeit hat ihre Abschlussprüfung nicht bestanden.")
    return python, False


def _project_pythonpath() -> str:
    existing = os.environ.get("PYTHONPATH", "").strip()
    parts = [str(ROOT / "src")]
    if existing:
        parts.append(existing)
    return os.pathsep.join(parts)


def run_startup_probe(python: Path, sink: EventSink) -> dict[str, Any]:
    env = {**os.environ, "PYTHONPATH": _project_pythonpath()}
    sink.log("$ startup_check.py")
    try:
        completed = subprocess.run(
            [str(python), str(ROOT / "scripts" / "startup_check.py")],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=120,
            check=False,
            errors="replace",
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        sink.log(f"Startup-Prüfung als Warnung übersprungen: {exc}")
        return {"status": "warning", "message": str(exc)}
    sink.log(completed.stdout or "(keine Prozessausgabe)")
    report_path = STATE / "startup" / "latest.json"
    if report_path.is_file():
        try:
            return json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            pass
    return {"status": "ready" if completed.returncode == 0 else "warning"}


def _tail(path: Path, limit: int = 5000) -> str:
    try:
        value = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return value[-limit:]


def launch_application(
    python: Path,
    environment: dict[str, str],
    sink: EventSink,
    *,
    safe_mode: bool,
    timeout: float = 35.0,
) -> tuple[int, bool]:
    """Launch native Qt/Wayland and require a real UI-ready handshake."""
    handshake_dir = STATE / "startup" / "handshakes"
    handshake_dir.mkdir(parents=True, exist_ok=True)
    token = f"{os.getpid()}-{time.time_ns()}-{'safe' if safe_mode else 'normal'}"
    marker = handshake_dir / f"{token}.json"
    app_log = LOG_DIR / f"application_{token}.log"
    app_log.parent.mkdir(parents=True, exist_ok=True)
    child_env = {
        **environment,
        "VIDEOBATCH_UI_READY_FILE": str(marker),
        "VIDEOBATCH_SAFE_MODE": "1" if safe_mode else "0",
        "PYTHONUNBUFFERED": "1",
        "QT_QPA_PLATFORM": "wayland",
    }
    sink.log(f"APPLICATION ATTEMPT safe_mode={safe_mode} transport=wayland log={app_log}")
    try:
        with app_log.open("a", encoding="utf-8", errors="replace") as output:
            process = subprocess.Popen(
                [str(python), "-m", "videobatch_fast"],
                cwd=ROOT,
                env=child_env,
                text=True,
                stdout=output,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
    except OSError as exc:
        raise BootstrapFailure(f"Die Qt-Oberfläche konnte nicht gestartet werden: {exc}") from exc

    deadline = time.monotonic() + max(5.0, timeout)
    while time.monotonic() < deadline:
        payload = read_ready_marker(marker)
        if payload is not None:
            sink.log(f"UI_READY pid={process.pid} safe_mode={safe_mode} payload={payload}")
            try:
                marker.unlink(missing_ok=True)
            except OSError:
                pass
            return process.pid, safe_mode
        returncode = process.poll()
        if returncode is not None:
            detail = _tail(app_log)
            sink.log(f"APPLICATION EXITED returncode={returncode}\n{detail}")
            raise BootstrapFailure(
                "Die Qt-Oberfläche wurde vor der Bereitschaftsmeldung beendet."
                + (f" Letzter technischer Hinweis: {detail.splitlines()[-1]}" if detail.splitlines() else "")
            )
        time.sleep(0.1)

    sink.log(f"UI_READY TIMEOUT safe_mode={safe_mode}")
    try:
        process.terminate()
        process.wait(timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        try:
            process.kill()
        except OSError:
            pass
    raise BootstrapFailure("Die Qt-Oberfläche hat ihre Startbereitschaft nicht rechtzeitig bestätigt.")


def worker(sink: EventSink) -> None:
    lock_handle = acquire_lock()
    if lock_handle is None:
        sink.failed("Ein anderer Startvorgang arbeitet noch. Das vorhandene Fenster bleibt erhalten.")
        return
    try:
        sink.stage(1, "Programmpaket und Kubuntu-Wayland-System prüfen")
        verify_project()
        startup_contract = load_startup_contract()
        install_user_launchers(sink)
        system_ready = ensure_system_dependencies(sink)

        sink.stage(2, "Qt-Laufzeit automatisch vorbereiten")
        attempts = int(startup_contract["policy"].get("maximum_automatic_repair_attempts", 2))
        python, runtime_fallback = ensure_runtime(sink, maximum_attempts=attempts)

        sink.stage(3, "Projekt und Medienfunktionen prüfen")
        report = run_startup_probe(python, sink)
        if runtime_fallback or not system_ready:
            report = {
                **report,
                "status": "degraded",
                "runtime_fallback": runtime_fallback,
                "system_dependencies_ready": system_ready,
            }

        sink.stage(4, "Native Qt-Wayland-Oberfläche öffnen")
        environment = {
            **os.environ,
            "PYTHONPATH": _project_pythonpath(),
            "VIDEOBATCH_BOOTSTRAP_LOG": str(sink.log_path),
            "VIDEOBATCH_STARTUP_STATUS": str(report.get("status", "ready")),
            "VIDEOBATCH_STARTUP_REPORT": str(STATE / "startup" / "latest.json"),
        }
        ready_timeout = float(startup_contract["policy"].get("application_ready_timeout_seconds", 35))
        if runtime_fallback:
            sink.stage(4, "Qt im sicheren Startmodus öffnen")
            safe_environment = {**environment, "VIDEOBATCH_STARTUP_STATUS": "degraded"}
            pid, safe_mode = launch_application(python, safe_environment, sink, safe_mode=True, timeout=ready_timeout)
        else:
            try:
                pid, safe_mode = launch_application(python, environment, sink, safe_mode=False, timeout=ready_timeout)
            except BootstrapFailure as first_error:
                sink.log(f"NORMAL START FAILED: {first_error}")
                sink.stage(4, "Qt im sicheren Startmodus öffnen")
                safe_environment = {**environment, "VIDEOBATCH_STARTUP_STATUS": "degraded"}
                pid, safe_mode = launch_application(python, safe_environment, sink, safe_mode=True, timeout=ready_timeout)
        sink.done(pid, safe_mode)
    except Exception as exc:
        sink.failed(str(exc))
    finally:
        try:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
            lock_handle.close()
        except OSError:
            pass


def terminal_main(events: queue.Queue[tuple[str, Any]], sink: EventSink) -> int:
    thread = threading.Thread(target=worker, args=(sink,), daemon=True)
    thread.start()
    while True:
        kind, payload = events.get()
        if kind == "stage":
            number, message = payload
            print(f"[{number}/4] {message}", flush=True)
        elif kind == "done":
            pid, safe_mode = payload
            mode = "safe" if safe_mode else "normal"
            print(f"BOOTSTRAP_READY pid={pid} mode={mode}")
            return 0
        elif kind == "failed":
            print("VideoBatch konnte den Start nicht selbstständig abschließen.", file=sys.stderr)
            print(f"Protokoll: {sink.log_path}", file=sys.stderr)
            return 1


def kdialog_main(events: queue.Queue[tuple[str, Any]], sink: EventSink) -> int:
    progress = KDialogProgress()
    if not progress.open():
        return terminal_main(events, sink)
    thread = threading.Thread(target=worker, args=(sink,), daemon=True)
    thread.start()
    while True:
        kind, payload = events.get()
        if kind == "stage":
            number, message = payload
            progress.stage(number, message)
        elif kind == "done":
            pid, safe_mode = payload
            if CHECK_ONLY:
                print(f"BOOTSTRAP_READY pid={pid} mode={'safe' if safe_mode else 'normal'}")
            progress.success(safe_mode)
            return 0
        elif kind == "failed":
            progress.error(str(payload), sink.log_path)
            print("VideoBatch konnte den Start nicht selbstständig abschließen.", file=sys.stderr)
            print(f"Protokoll: {sink.log_path}", file=sys.stderr)
            return 1


def main() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"bootstrap_{stamp}.log"
    events: queue.Queue[tuple[str, Any]] = queue.Queue()
    sink = EventSink(events, log_path)
    sink.log(f"VideoBatch Wayland bootstrap started {datetime.now().isoformat()}")
    progress = KDialogProgress()
    return kdialog_main(events, sink) if progress.available else terminal_main(events, sink)


if __name__ == "__main__":
    raise SystemExit(main())
