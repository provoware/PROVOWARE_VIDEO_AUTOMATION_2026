#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from videobatch_fast.debug_runtime import RUNTIME, debug_enabled_from_config, show_incident_dialog

STATE = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "VideoBatchFast"


def _latest_file(directory: Path, pattern: str) -> Path | None:
    try:
        candidates = [path for path in directory.glob(pattern) if path.is_file() and not path.is_symlink()]
    except OSError:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime, default=None)


def _tail(path: Path | None, limit: int = 20_000) -> str:
    if path is None:
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")[-limit:]
    except OSError:
        return ""


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


def main() -> int:
    enabled = debug_enabled_from_config(default=True)
    RUNTIME.set_enabled(enabled)
    os.environ["VIDEOBATCH_DEBUG"] = "1" if enabled else "0"
    os.environ.setdefault("VIDEOBATCH_DEBUG_DIR", str(ROOT / "debugging"))

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
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env={
                **os.environ,
                "PYTHONPATH": os.pathsep.join(
                    part for part in (str(SRC), os.environ.get("PYTHONPATH", "")) if part
                ),
            },
            check=False,
        )
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

    if completed.returncode == 0:
        RUNTIME.verbose(
            "Der sichere Starter hat die Oberfläche erfolgreich freigegeben.",
            "Die UI-Ready-Meldung wurde empfangen; die Anwendung läuft als eigener Prozess weiter.",
            "scripts/bootstrap.py → UI_READY",
            "Jetzt die Oberfläche verwenden. Ein späterer Python-Fehler wird vom zentralen App-Debugfänger protokolliert.",
            level="OK",
        )
        return 0

    context = _failure_context(completed.returncode)
    incident = RUNTIME.capture_message(
        what="VideoBatch konnte den Start nicht erfolgreich abschließen.",
        how=(
            f"Die bestehende Bootstrap-Routine wurde beendet und lieferte Rückgabecode {completed.returncode}. "
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
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
