#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from videobatch_fast.debug_runtime import RUNTIME, debug_enabled_from_config, show_incident_dialog

STATE = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "VideoBatchFast"
_UI_READY_RE = re.compile(r"UI_READY pid=(\d+)")


def _latest_file(directory: Path, pattern: str) -> Path | None:
    try:
        candidates = [path for path in directory.glob(pattern) if path.is_file() and not path.is_symlink()]
    except OSError:
        return None
    try:
        return max(candidates, key=lambda path: path.stat().st_mtime, default=None)
    except OSError:
        return None


def _latest_file_since(directory: Path, pattern: str, since: float) -> Path | None:
    try:
        candidates = [
            path
            for path in directory.glob(pattern)
            if path.is_file()
            and not path.is_symlink()
            and path.stat().st_mtime >= since - 0.5
        ]
    except OSError:
        return None
    try:
        return max(candidates, key=lambda path: path.stat().st_mtime, default=None)
    except OSError:
        return None


def _tail(path: Path | None, limit: int = 20_000) -> str:
    if path is None:
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")[-limit:]
    except OSError:
        return ""


def _stream_file(path: Path | None, offset: int, *, prefix: str) -> int:
    if path is None or not path.is_file():
        return offset
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            handle.seek(offset)
            chunk = handle.read()
            new_offset = handle.tell()
    except OSError:
        return offset
    if not chunk:
        return new_offset
    for line in chunk.splitlines():
        text = line.rstrip()
        if not text:
            continue
        if text.startswith("STAGE "):
            RUNTIME.verbose(
                f"Startphase: {text}",
                "Die bestehende Bootstrap-Routine hat den nächsten klar abgegrenzten Prüfschritt erreicht.",
                "scripts/bootstrap.py",
                "Keine Eingabe nötig. Der Starter arbeitet automatisch weiter.",
            )
        elif text.startswith("APPLICATION ATTEMPT"):
            RUNTIME.verbose(
                "Die grafische Anwendung wird als eigener Prozess gestartet.",
                text,
                "Bootstrap → Application-Prozess",
                "Wenn dieser Versuch scheitert, werden Application-Log und Python-Fehler automatisch übernommen.",
            )
        elif _UI_READY_RE.match(text):
            RUNTIME.verbose(
                "Die Oberfläche meldet Startbereitschaft.",
                text,
                "UI-Ready-Handshake",
                "Der Debug-Wächter bleibt aktiv und zeigt die weitere Anwendungsausgabe im Terminal.",
                level="OK",
            )
        elif "UI_READY TIMEOUT" in text or "FAILED:" in text or "APPLICATION EXITED" in text:
            RUNTIME.verbose(
                "Ein Startfehler wurde erkannt.",
                text,
                "Bootstrap-/Application-Protokoll",
                "Nicht raten oder Dateien löschen; der vollständige TXT-Bericht wird automatisch erzeugt.",
                level="FEHLER",
            )
        elif RUNTIME.enabled:
            print(f"[{prefix}] {text}", flush=True)
    return new_offset


def _ready_pid(bootstrap_log: Path | None) -> int | None:
    text = _tail(bootstrap_log, 40_000)
    matches = _UI_READY_RE.findall(text)
    if not matches:
        return None
    try:
        return int(matches[-1])
    except ValueError:
        return None


def _process_exists(pid: int) -> bool:
    return (Path("/proc") / str(pid)).exists()


def _reported_crash_path(application_log: Path | None) -> str:
    text = _tail(application_log, 60_000)
    paths = [line.split("DEBUG_REPORT=", 1)[1].strip() for line in text.splitlines() if "DEBUG_REPORT=" in line]
    return paths[-1] if paths else ""


def _diagnostic_action() -> None:
    command = [sys.executable, str(ROOT / "scripts" / "user_diagnostics.py"), "--brief"]
    try:
        subprocess.Popen(
            command,
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": str(SRC)},
            start_new_session=True,
        )
    except OSError as exc:
        print(f"[DEBUG] Systemdiagnose konnte nicht gestartet werden: {exc}", file=sys.stderr)


def _failure_context(returncode: int) -> dict[str, object]:
    bootstrap_log = _latest_file(STATE / "logs", "bootstrap_*.log")
    application_log = _latest_file(STATE / "logs", "application_*.log")
    startup_report = STATE / "startup" / "latest.json"
    return {
        "Starter-Rückgabecode": returncode,
        "Letzter Bootstrap-Log": bootstrap_log or "nicht gefunden",
        "Letzter Application-Log": application_log or "nicht gefunden",
        "Bootstrap-Logauszug": _tail(bootstrap_log),
        "Application-Logauszug": _tail(application_log),
        "Startup-Report": _tail(startup_report),
    }


def _monitor_application(
    pid: int,
    application_log: Path | None,
    bootstrap_log: Path | None,
    clean_marker: Path,
    started_at: float,
) -> None:
    RUNTIME.verbose(
        f"Der laufende Anwendungsprozess wird überwacht · PID {pid}.",
        "Der Starter liest ausschließlich den Log dieser Startsitzung und prüft, ob der Prozess regulär oder unerwartet endet.",
        str(application_log or "Application-Log noch nicht gefunden"),
        "Debugmodus im Tool ausschalten, wenn diese ausführliche Terminalbegleitung nicht mehr gewünscht ist.",
    )
    offset = 0
    while _process_exists(pid):
        if not debug_enabled_from_config(default=True):
            RUNTIME.set_enabled(False)
            return
        if application_log is None:
            application_log = _latest_file_since(
                STATE / "logs", "application_*.log", started_at
            )
        offset = _stream_file(application_log, offset, prefix="APP")
        time.sleep(0.2)

    _stream_file(application_log, offset, prefix="APP")
    if clean_marker.is_file():
        clean_marker.unlink(missing_ok=True)
        RUNTIME.verbose(
            "Die Anwendung wurde regulär beendet.",
            "Der Prozess ist verschwunden und die Anwendung hat vorher die Clean-Shutdown-Markierung geschrieben.",
            f"PID {pid}",
            "Keine Reparatur nötig.",
            level="OK",
        )
        return

    existing_report = _reported_crash_path(application_log)
    if existing_report:
        RUNTIME.verbose(
            "Die Anwendung wurde nach einem bereits protokollierten Fehler beendet.",
            f"Die Anwendung selbst hat bereits einen vollständigen Bericht erzeugt: {existing_report}",
            f"PID {pid}",
            "Den bereits automatisch geöffneten Bericht verwenden; kein doppelter Bericht wird erzeugt.",
            level="FEHLER",
        )
        return

    incident = RUNTIME.capture_message(
        what="Der VideoBatch-Anwendungsprozess ist ohne reguläre Abschlussmarkierung verschwunden.",
        how=(
            "Der externe Debug-Wächter hat festgestellt, dass die Prozess-ID nicht mehr existiert, "
            "obwohl kein sauberer Programmabschluss protokolliert wurde. Das deckt auch harte Abbrüche ohne Python-Traceback ab."
        ),
        where=f"Anwendungsprozess PID {pid} · letzter Log: {application_log or 'nicht gefunden'}",
        solutions=(
            "Den Application-Logauszug im Bericht auf die letzte Meldung vor dem Abbruch prüfen.",
            "Die zuletzt ausgeführte Aktion im Tool notieren und den Fehler einmal kontrolliert reproduzieren.",
            "Bei erneutem Abbruch den erzeugten Bericht verwenden; Originalmedien nicht verändern oder löschen.",
            "Systemdiagnose starten, falls kein Python-Fehler im Bericht sichtbar ist.",
        ),
        fatal=True,
        extra_context={
            "Überwachte PID": pid,
            "Application-Log": application_log or "nicht gefunden",
            "Application-Logauszug": _tail(application_log, 40_000),
            "Bootstrap-Logauszug": _tail(bootstrap_log, 20_000),
        },
        auto_open=True,
        force=True,
        prefix="PROZESSABSTURZ",
    )
    if incident is not None:
        show_incident_dialog(
            incident,
            extra_actions={"Systemdiagnose starten": _diagnostic_action},
        )


def main() -> int:
    started_at = time.time()
    enabled = debug_enabled_from_config(default=True)
    RUNTIME.set_enabled(enabled)
    os.environ.setdefault("VIDEOBATCH_DEBUG_DIR", str(ROOT / "debugging"))
    os.environ.pop("VIDEOBATCH_DEBUG_CLEAN_MARKER", None)

    watchdog_dir = STATE / "debugging" / "watchdog"
    watchdog_dir.mkdir(parents=True, exist_ok=True)
    clean_marker = watchdog_dir / f"clean_{os.getpid()}_{time.time_ns()}.marker"
    clean_marker.unlink(missing_ok=True)
    if enabled:
        os.environ["VIDEOBATCH_DEBUG_CLEAN_MARKER"] = str(clean_marker)

    RUNTIME.verbose(
        "VideoBatch-Start wurde angefordert.",
        "Der Debug-Starter übernimmt jetzt die bestehende sichere Bootstrap-Routine und beobachtet ihr Ergebnis.",
        f"Projektordner: {ROOT}",
        "Keine Eingabe nötig. Jeder Startschritt wird verständlich erklärt, solange der Debugmodus aktiv ist.",
    )
    RUNTIME.verbose(
        "Die vorhandene Bootstrap-Routine wird gestartet.",
        "Sie prüft Projekt, Laufzeit, Startdiagnose, normalen Start und bei Bedarf den sicheren Startmodus.",
        "scripts/bootstrap.py",
        "Bei einem Fehler wird zusätzlich ein ausführlicher TXT-Bericht im Projektordner debugging erzeugt.",
    )

    command = [sys.executable, str(ROOT / "scripts" / "bootstrap.py"), *sys.argv[1:]]
    environment = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join(
            part for part in (str(SRC), os.environ.get("PYTHONPATH", "")) if part
        ),
    }
    try:
        process = subprocess.Popen(command, cwd=ROOT, env=environment)
    except OSError as exc:
        incident = RUNTIME.capture_exception(
            type(exc),
            exc,
            exc.__traceback__,
            what="Die Bootstrap-Routine konnte überhaupt nicht gestartet werden.",
            how="Das Betriebssystem hat den Start des Python-Prozesses abgelehnt.",
            where="scripts/debug_launcher.py → scripts/bootstrap.py",
            solutions=(
                "Prüfen, ob Python 3 vorhanden und ausführbar ist.",
                "Prüfen, ob der Projektordner vollständig entpackt wurde.",
                "Danach STARTEN.sh erneut ausführen.",
            ),
            fatal=True,
            extra_context=_failure_context(127),
            auto_open=True,
            force=True,
        )
        if incident is not None:
            show_incident_dialog(
                incident,
                extra_actions={"Systemdiagnose starten": _diagnostic_action},
            )
        return 127

    bootstrap_log: Path | None = None
    bootstrap_offset = 0
    while process.poll() is None:
        latest = _latest_file_since(STATE / "logs", "bootstrap_*.log", started_at)
        if latest is not None:
            if latest != bootstrap_log:
                bootstrap_log = latest
                bootstrap_offset = 0
            bootstrap_offset = _stream_file(bootstrap_log, bootstrap_offset, prefix="BOOTSTRAP")
        time.sleep(0.15)
    _stream_file(bootstrap_log, bootstrap_offset, prefix="BOOTSTRAP")
    returncode = int(process.returncode or 0)

    if returncode != 0:
        context = _failure_context(returncode)
        incident = RUNTIME.capture_message(
            what="VideoBatch konnte den Start nicht erfolgreich abschließen.",
            how=(
                f"Die bestehende Bootstrap-Routine wurde beendet und lieferte Rückgabecode {returncode}. "
                "Die letzten Bootstrap-, Application- und Startup-Daten wurden automatisch in diesen Bericht übernommen."
            ),
            where="STARTEN.sh → scripts/debug_launcher.py → scripts/bootstrap.py",
            solutions=(
                "Den automatisch geöffneten Bericht unter WAS, WIE und WO lesen.",
                "Die Aktion „Systemdiagnose starten“ verwenden.",
                "Im Application-Logauszug die letzte Python-Fehlermeldung prüfen.",
                "Erst nach Klärung des konkreten Fehlers erneut starten; keine Projekt- oder Mediendateien löschen.",
            ),
            fatal=True,
            extra_context=context,
            auto_open=True,
            force=True,
            prefix="STARTABSTURZ",
        )
        if incident is not None:
            show_incident_dialog(
                incident,
                extra_actions={"Systemdiagnose starten": _diagnostic_action},
            )
        return returncode

    RUNTIME.verbose(
        "Der sichere Starter hat die Oberfläche erfolgreich freigegeben.",
        "Die UI-Ready-Meldung wurde empfangen; die Anwendung läuft als eigener Prozess weiter.",
        "scripts/bootstrap.py → UI_READY",
        "Der Debug-Wächter übernimmt jetzt die laufende Anwendungsausgabe.",
        level="OK",
    )
    if not enabled:
        return 0

    pid = _ready_pid(bootstrap_log)
    application_log = _latest_file_since(STATE / "logs", "application_*.log", started_at)
    if pid is None:
        RUNTIME.verbose(
            "Die Anwendung läuft, ihre Prozess-ID konnte aber nicht aus dem Bootstrap-Log gelesen werden.",
            "Der Starter hat erfolgreich beendet, aber keine auswertbare UI_READY-PID gefunden.",
            str(bootstrap_log or "Bootstrap-Log nicht gefunden"),
            "Die Anwendung kann benutzt werden; Python-Fehler werden weiterhin von der Anwendung selbst protokolliert.",
            level="WARNUNG",
        )
        return 0

    _monitor_application(pid, application_log, bootstrap_log, clean_marker, started_at)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
