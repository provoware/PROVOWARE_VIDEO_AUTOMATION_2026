from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from .paths import state_dir

DIAGNOSTIC_SCHEMA_VERSION = 1
QUEUE_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class PathStatus:
    path: str
    exists: bool
    is_file: bool


@dataclass(frozen=True, slots=True)
class RetryEntryDiagnostic:
    job_id: str
    index: int | None
    state: str
    attempts: int
    max_attempts: int
    retry_allowed: bool
    startable: bool
    start_blockers: tuple[str, ...]
    first_error: str
    latest_error: str
    protection: str
    failure_kind: str
    operation_id: str
    updated_at: str
    audio: PathStatus
    media: PathStatus
    media_sequence: tuple[PathStatus, ...]
    output: str


@dataclass(frozen=True, slots=True)
class RetryDiagnosticReport:
    schema_version: int
    queue_path: str
    queue_exists: bool
    queue_valid: bool
    queue_sha256: str
    queue_size: int
    queue_schema_version: int | None
    max_entries: int
    max_attempts: int
    dropped_total: int
    total: int
    startable: int
    blocked: int
    not_started: int
    invalid_entries: int
    error: str
    entries: tuple[RetryEntryDiagnostic, ...]

    def as_payload(self) -> dict[str, Any]:
        return asdict(self)


def default_queue_path() -> Path:
    return state_dir() / "jobs" / "retry_queue.json"


def _path_status(raw: object) -> PathStatus:
    text = str(raw or "")
    if not text:
        return PathStatus("", False, False)
    path = Path(text).expanduser()
    try:
        exists = path.exists()
        is_file = path.is_file()
    except OSError:
        exists = False
        is_file = False
    return PathStatus(str(path), exists, is_file)


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return default


def _entry_diagnostic(item: dict[str, Any], queue_max_attempts: int) -> RetryEntryDiagnostic:
    state = str(item.get("state", "unknown") or "unknown")
    attempts = max(0, _safe_int(item.get("attempts"), 0))
    max_attempts = max(1, _safe_int(item.get("max_attempts"), queue_max_attempts or 1))
    retry_allowed = bool(item.get("retry_allowed")) and attempts < max_attempts
    audio = _path_status(item.get("audio"))
    media = _path_status(item.get("media"))
    raw_sequence = item.get("media_sequence", [])
    sequence_values = raw_sequence if isinstance(raw_sequence, list) else []
    media_sequence = tuple(_path_status(value) for value in sequence_values)

    blockers: list[str] = []
    if state == "limit_reached" or attempts >= max_attempts:
        blockers.append("Versuchslimit erreicht")
    if not retry_allowed:
        blockers.append("Eintrag ist nicht zum Wiederanlauf freigegeben")
    if not audio.is_file:
        blockers.append("Audiodatei fehlt oder ist keine Datei")
    media_inputs: Iterable[PathStatus] = media_sequence or (media,)
    if not all(path.is_file for path in media_inputs):
        blockers.append("Mindestens eine Mediendatei fehlt oder ist keine Datei")
    if state not in {"failed", "not_started"}:
        blockers.append(f"Status {state!r} ist nicht startbar")

    unique_blockers = tuple(dict.fromkeys(blockers))
    return RetryEntryDiagnostic(
        job_id=str(item.get("job_id", "")),
        index=_safe_int(item.get("index"), -1) if item.get("index") is not None else None,
        state=state,
        attempts=attempts,
        max_attempts=max_attempts,
        retry_allowed=retry_allowed,
        startable=not unique_blockers,
        start_blockers=unique_blockers,
        first_error=str(item.get("first_error", "")),
        latest_error=str(item.get("latest_error", "")),
        protection=str(item.get("protection", "")),
        failure_kind=str(item.get("failure_kind", "")),
        operation_id=str(item.get("operation_id", "")),
        updated_at=str(item.get("updated_at", "")),
        audio=audio,
        media=media,
        media_sequence=media_sequence,
        output=str(item.get("output", "")),
    )


def inspect_retry_queue(path: Path | None = None) -> RetryDiagnosticReport:
    """Inspect a retry queue without creating, modifying, quarantining or deleting anything."""
    target = Path(path) if path is not None else default_queue_path()
    target = target.expanduser()
    try:
        exists = target.is_file()
    except OSError:
        exists = False
    if not exists:
        return RetryDiagnosticReport(
            DIAGNOSTIC_SCHEMA_VERSION,
            str(target),
            False,
            True,
            "",
            0,
            None,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            "",
            (),
        )

    try:
        raw = target.read_bytes()
    except OSError as exc:
        return RetryDiagnosticReport(
            DIAGNOSTIC_SCHEMA_VERSION,
            str(target),
            True,
            False,
            "",
            0,
            None,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            f"Datei konnte nicht gelesen werden: {exc}",
            (),
        )

    digest = hashlib.sha256(raw).hexdigest()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return RetryDiagnosticReport(
            DIAGNOSTIC_SCHEMA_VERSION,
            str(target),
            True,
            False,
            digest,
            len(raw),
            None,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            f"Ungültiges JSON: {exc}",
            (),
        )
    if not isinstance(payload, dict):
        return RetryDiagnosticReport(
            DIAGNOSTIC_SCHEMA_VERSION,
            str(target),
            True,
            False,
            digest,
            len(raw),
            None,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            "Wiederanlaufliste ist kein JSON-Objekt.",
            (),
        )

    schema_version = _safe_int(payload.get("schema_version"), -1)
    raw_entries = payload.get("entries", [])
    if schema_version != QUEUE_SCHEMA_VERSION or not isinstance(raw_entries, list):
        error = (
            f"Nicht unterstützte Schema-Version {schema_version}."
            if schema_version != QUEUE_SCHEMA_VERSION
            else "Feld 'entries' ist keine Liste."
        )
        return RetryDiagnosticReport(
            DIAGNOSTIC_SCHEMA_VERSION,
            str(target),
            True,
            False,
            digest,
            len(raw),
            schema_version,
            max(0, _safe_int(payload.get("max_entries"), 0)),
            max(0, _safe_int(payload.get("max_attempts"), 0)),
            max(0, _safe_int(payload.get("dropped_total"), 0)),
            0,
            0,
            0,
            0,
            len(raw_entries) if isinstance(raw_entries, list) else 0,
            error,
            (),
        )

    queue_max_attempts = max(1, _safe_int(payload.get("max_attempts"), 1))
    entries: list[RetryEntryDiagnostic] = []
    invalid_entries = 0
    for item in raw_entries:
        if not isinstance(item, dict) or not str(item.get("job_id", "")):
            invalid_entries += 1
            continue
        entries.append(_entry_diagnostic(item, queue_max_attempts))

    return RetryDiagnosticReport(
        DIAGNOSTIC_SCHEMA_VERSION,
        str(target),
        True,
        True,
        digest,
        len(raw),
        schema_version,
        max(0, _safe_int(payload.get("max_entries"), 0)),
        queue_max_attempts,
        max(0, _safe_int(payload.get("dropped_total"), 0)),
        len(entries),
        sum(item.startable for item in entries),
        sum(not item.startable for item in entries),
        sum(item.state == "not_started" for item in entries),
        invalid_entries,
        "",
        tuple(entries),
    )


def _human(report: RetryDiagnosticReport) -> str:
    lines = [
        "WIEDERANLAUF-DIAGNOSE · vollständig lesend",
        f"Datei: {report.queue_path}",
        f"Vorhanden: {'ja' if report.queue_exists else 'nein'}",
        f"Gültig: {'ja' if report.queue_valid else 'nein'}",
    ]
    if report.queue_sha256:
        lines.append(f"SHA-256: {report.queue_sha256}")
    if report.error:
        lines.append(f"Fehler: {report.error}")
    lines.append(
        f"Einträge: {report.total} · startbar: {report.startable} · blockiert: {report.blocked} · "
        f"nicht gestartet: {report.not_started} · ungültig: {report.invalid_entries}"
    )
    for number, item in enumerate(report.entries, start=1):
        marker = "STARTBAR" if item.startable else "BLOCKIERT"
        media_paths = item.media_sequence or (item.media,)
        lines.extend(
            [
                "",
                f"[{number}] {marker} · Status={item.state} · Versuch={item.attempts}/{item.max_attempts}",
                f"    Auftrag: {item.job_id}",
                f"    Audio: {item.audio.path or '-'} · {'vorhanden' if item.audio.is_file else 'fehlt'}",
                "    Medien: " + ", ".join(
                    f"{path.path or '-'} ({'vorhanden' if path.is_file else 'fehlt'})" for path in media_paths
                ),
                f"    Ausgabe: {item.output or '-'}",
                f"    Ursprünglicher Fehler: {item.first_error or '-'}",
                f"    Letzter Fehler: {item.latest_error or '-'}",
                f"    Schutzmaßnahme: {item.protection or '-'}",
            ]
        )
        if item.start_blockers:
            lines.append("    Startblocker: " + " · ".join(item.start_blockers))
    lines.extend(
        [
            "",
            "Schreibschutz: Dieser Befehl startet keine Aufträge und verändert oder löscht keine Einträge.",
        ]
    )
    return "\n".join(lines)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Zeigt die Wiederanlaufliste vollständig lesend an, ohne Aufträge oder Dateien zu verändern."
    )
    parser.add_argument("--path", type=Path, help="Ausdrücklich ausgewählte Wiederanlaufliste")
    parser.add_argument("--json", action="store_true", help="Maschinenlesbare JSON-Ausgabe")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    report = inspect_retry_queue(args.path)
    if args.json:
        print(json.dumps(report.as_payload(), ensure_ascii=False, indent=2))
    else:
        print(_human(report))
    return 0 if report.queue_valid else 2


if __name__ == "__main__":
    raise SystemExit(main())
