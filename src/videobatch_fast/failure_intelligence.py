from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import traceback
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from types import TracebackType
from typing import Any

from .event_logging import safe_text
from .safe_io import atomic_write_json, quarantine_file

SCHEMA_VERSION = 1
_LEDGER_NAME = "failure_regressions.json"
_OCCURRENCE_LOG_NAME = "failure_occurrences.jsonl"
_LOCK = threading.RLock()

_UUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b"
)
_HEX_RE = re.compile(r"\b0x[0-9a-fA-F]+\b")
_ISO_TIME_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?\b")
_VOLATILE_ID_RE = re.compile(
    r"(?i)\b(pid|process|job|run|task|request|session|operation)[-_ ]?(id)?\s*[:=#]?\s*\d+\b"
)
_TMP_PATH_RE = re.compile(r"(?:/tmp|/var/tmp)/[^\s'\";,]+")


@dataclass(frozen=True, slots=True)
class FailureOccurrence:
    timestamp: str
    occurrence_id: str
    fingerprint: str
    regression_state: str
    exception_type: str
    message: str
    source_file: str
    source_line: int
    source_function: str
    operation_id: str
    occurrence_count: int
    regression_count: int
    first_seen: str
    last_seen: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class FailureLedgerError(RuntimeError):
    """Raised when the regression ledger cannot be handled without losing evidence."""


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _normalise_message(message: Any) -> str:
    text = safe_text(message, 2000).strip()
    text = _UUID_RE.sub("<uuid>", text)
    text = _HEX_RE.sub("<hex>", text)
    text = _ISO_TIME_RE.sub("<timestamp>", text)
    text = _TMP_PATH_RE.sub("<tmp-path>", text)
    text = _VOLATILE_ID_RE.sub(lambda match: f"{match.group(1).lower()}=<id>", text)
    return " ".join(text.split())


def _portable_source_path(filename: str) -> str:
    text = safe_text(filename, 2000)
    try:
        parts = Path(text).parts
    except (OSError, ValueError):
        return text
    for marker in ("src", "tests", "scripts"):
        if marker in parts:
            index = parts.index(marker)
            return Path(*parts[index:]).as_posix()
    return Path(text).name or text


def _trace_details(tb: TracebackType | None) -> tuple[str, int, str]:
    if tb is None:
        return "<unknown>", 0, "<unknown>"
    frames = traceback.extract_tb(tb)
    if not frames:
        return "<unknown>", 0, "<unknown>"
    frame = frames[-1]
    return _portable_source_path(frame.filename), int(frame.lineno), safe_text(frame.name, 240)


def _fingerprint(*, exception_type: str, message: str, source_file: str, source_function: str) -> str:
    canonical = "\n".join((exception_type, message, source_file, source_function))
    return hashlib.sha256(canonical.encode("utf-8", errors="replace")).hexdigest()[:24]


def _empty_ledger() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "updated_at": _now(), "entries": {}}


def _validate_ledger(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise FailureLedgerError("Fehlergedächtnis ist kein JSON-Objekt.")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise FailureLedgerError("Fehlergedächtnis besitzt eine unbekannte Schema-Version.")
    entries = payload.get("entries")
    if not isinstance(entries, dict):
        raise FailureLedgerError("Fehlergedächtnis enthält keine gültige Eintragsliste.")
    for fingerprint, entry in entries.items():
        if not isinstance(fingerprint, str) or not isinstance(entry, dict):
            raise FailureLedgerError("Fehlergedächtnis enthält einen ungültigen Eintrag.")
        if entry.get("fingerprint") != fingerprint:
            raise FailureLedgerError("Fehlergedächtnis enthält einen inkonsistenten Fingerprint.")
        if entry.get("state") not in {"new", "known", "resolved", "regressed"}:
            raise FailureLedgerError("Fehlergedächtnis enthält einen unbekannten Regressionsstatus.")
        if not isinstance(entry.get("count"), int) or entry["count"] < 1:
            raise FailureLedgerError("Fehlergedächtnis enthält einen ungültigen Vorkommniszähler.")
        if not isinstance(entry.get("regression_count", 0), int) or entry.get("regression_count", 0) < 0:
            raise FailureLedgerError("Fehlergedächtnis enthält einen ungültigen Regressionszähler.")
    return payload


def _load_ledger(path: Path) -> tuple[dict[str, Any], Path | None]:
    if not path.exists():
        return _empty_ledger(), None
    if path.is_symlink() or not path.is_file():
        raise FailureLedgerError(f"Unsicherer Fehlergedächtnis-Pfad: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return _validate_ledger(payload), None
    except (OSError, UnicodeError, json.JSONDecodeError, FailureLedgerError) as exc:
        try:
            quarantined = quarantine_file(path, label="corrupt")
        except Exception as quarantine_exc:
            raise FailureLedgerError(
                f"Beschädigtes Fehlergedächtnis konnte nicht sicher erhalten werden: {quarantine_exc}"
            ) from exc
        return _empty_ledger(), quarantined


def _append_occurrence(path: Path, occurrence: FailureOccurrence) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(occurrence.as_dict(), ensure_ascii=False, sort_keys=True) + "\n"
    data = payload.encode("utf-8", errors="replace")
    descriptor = os.open(path, os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o600)
    try:
        os.write(descriptor, data)
        os.fsync(descriptor)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    finally:
        os.close(descriptor)


def record_exception(
    exc_type: type[BaseException],
    exc: BaseException,
    tb: TracebackType | None,
    *,
    directory: Path,
    operation_id: str = "runtime",
) -> tuple[FailureOccurrence, Path | None]:
    """Record one exception and return its stable signature plus any quarantined ledger."""
    root = Path(directory).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    ledger_path = root / _LEDGER_NAME
    occurrence_path = root / _OCCURRENCE_LOG_NAME

    timestamp = _now()
    exception_type = safe_text(exc_type.__name__, 240)
    message = _normalise_message(exc)
    source_file, source_line, source_function = _trace_details(tb)
    fingerprint = _fingerprint(
        exception_type=exception_type,
        message=message,
        source_file=source_file,
        source_function=source_function,
    )
    occurrence_id = uuid.uuid4().hex
    operation = safe_text(operation_id or "runtime", 160)

    with _LOCK:
        ledger, quarantined = _load_ledger(ledger_path)
        entries: dict[str, Any] = ledger["entries"]
        previous = entries.get(fingerprint)
        if previous is None:
            state = "new"
            count = 1
            regression_count = 0
            first_seen = timestamp
        else:
            previous_state = previous["state"]
            state = "regressed" if previous_state == "resolved" else ("regressed" if previous_state == "regressed" else "known")
            count = int(previous["count"]) + 1
            regression_count = int(previous.get("regression_count", 0)) + (1 if previous_state == "resolved" else 0)
            first_seen = str(previous["first_seen"])

        occurrence = FailureOccurrence(
            timestamp=timestamp,
            occurrence_id=occurrence_id,
            fingerprint=fingerprint,
            regression_state=state,
            exception_type=exception_type,
            message=message,
            source_file=source_file,
            source_line=source_line,
            source_function=source_function,
            operation_id=operation,
            occurrence_count=count,
            regression_count=regression_count,
            first_seen=first_seen,
            last_seen=timestamp,
        )
        entries[fingerprint] = {
            "fingerprint": fingerprint,
            "exception_type": exception_type,
            "message": message,
            "source_file": source_file,
            "source_function": source_function,
            "first_seen": first_seen,
            "last_seen": timestamp,
            "count": count,
            "regression_count": regression_count,
            "state": state,
            "resolved_at": None if state != "resolved" else previous.get("resolved_at") if previous else None,
            "last_occurrence_id": occurrence_id,
            "last_source_line": source_line,
            "last_operation_id": operation,
        }
        ledger["updated_at"] = timestamp
        atomic_write_json(ledger_path, ledger, mode=0o600)
        _append_occurrence(occurrence_path, occurrence)
        return occurrence, quarantined


def mark_resolved(
    fingerprint: str,
    *,
    directory: Path,
    resolution: str = "",
) -> dict[str, Any]:
    """Mark a known failure as resolved. A later occurrence will be classified as a regression."""
    root = Path(directory).expanduser()
    ledger_path = root / _LEDGER_NAME
    clean_fingerprint = safe_text(fingerprint, 64).strip()
    with _LOCK:
        ledger, _ = _load_ledger(ledger_path)
        entries: dict[str, Any] = ledger["entries"]
        entry = entries.get(clean_fingerprint)
        if entry is None:
            raise KeyError(f"Unbekannter Fehler-Fingerprint: {clean_fingerprint}")
        now = _now()
        entry["state"] = "resolved"
        entry["resolved_at"] = now
        entry["resolution"] = safe_text(resolution, 2000)
        ledger["updated_at"] = now
        atomic_write_json(ledger_path, ledger, mode=0o600)
        return dict(entry)


def load_summary(*, directory: Path) -> dict[str, Any]:
    """Return state counts without modifying a valid ledger."""
    ledger_path = Path(directory).expanduser() / _LEDGER_NAME
    with _LOCK:
        ledger, quarantined = _load_ledger(ledger_path)
        counts = {"new": 0, "known": 0, "resolved": 0, "regressed": 0}
        for entry in ledger["entries"].values():
            counts[entry["state"]] += 1
        return {
            "schema_version": SCHEMA_VERSION,
            "updated_at": ledger["updated_at"],
            "total": len(ledger["entries"]),
            "counts": counts,
            "quarantined": str(quarantined) if quarantined else "",
        }
