from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .naming import safe_stem
from .safe_io import atomic_write_json

JOURNAL_SCHEMA_VERSION = 2
TERMINAL_STATES = {"committed", "rolled_back", "source_retained", "failed_safe"}


@dataclass(frozen=True, slots=True)
class ArchiveRecord:
    source: str
    target: str
    size: int
    sha256: str
    kind: str
    status: str
    timestamp: str
    transaction_id: str = ""


@dataclass(slots=True)
class ArchiveTransaction:
    transaction_id: str
    source: Path
    target: Path
    temp: Path | None
    reservation: Path
    journal: Path
    expected_size: int
    expected_hash: str
    kind: str
    state: str = "prepared"
    message: str = ""


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def used_name(path: Path, suffix: str = "__verwendet") -> str:
    stem = path.stem
    while stem.endswith(suffix):
        stem = stem[: -len(suffix)]
    return f"{safe_stem(stem + suffix)}{path.suffix.lower()}"


def _transaction_dir(project_dir: Path) -> Path:
    directory = Path(project_dir) / "Verwendet" / ".transactions"
    directory.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(directory, 0o700)
    except OSError:
        pass
    return directory


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    atomic_write_json(path, payload)


def _journal_payload(transaction: ArchiveTransaction) -> dict[str, Any]:
    return {
        "schema_version": JOURNAL_SCHEMA_VERSION,
        "transaction_id": transaction.transaction_id,
        "source": str(transaction.source),
        "target": str(transaction.target),
        "temp": str(transaction.temp) if transaction.temp else "",
        "reservation": str(transaction.reservation),
        "expected_size": transaction.expected_size,
        "expected_hash": transaction.expected_hash,
        "kind": transaction.kind,
        "state": transaction.state,
        "message": transaction.message,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }


def _record_state(transaction: ArchiveTransaction, state: str, message: str = "") -> None:
    transaction.state = state
    transaction.message = message
    _atomic_json(transaction.journal, _journal_payload(transaction))


def _reserve_target(directory: Path, name: str) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    base = directory / name
    for counter in range(1, 10_000):
        target = base if counter == 1 else base.with_name(f"{base.stem}_{counter}{base.suffix}")
        reservation = target.with_name(f".{target.name}.archive-reserve")
        if target.exists():
            continue
        try:
            fd = os.open(reservation, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            continue
        try:
            os.write(fd, f"pid={os.getpid()}\ntarget={target}\n".encode("utf-8"))
            os.fsync(fd)
        finally:
            os.close(fd)
        if target.exists():
            reservation.unlink(missing_ok=True)
            continue
        return target, reservation
    raise FileExistsError("Kein freier, atomar reservierbarer Archivname verfügbar.")


def unique_target(directory: Path, name: str) -> Path:
    """Compatibility helper. Archive operations use _reserve_target atomically."""
    target, reservation = _reserve_target(Path(directory), name)
    reservation.unlink(missing_ok=True)
    return target


def _verify_file(path: Path, size: int, sha256: str) -> None:
    if not path.is_file():
        raise OSError(f"Datei fehlt: {path}")
    if path.stat().st_size != size:
        raise OSError(f"Dateigröße stimmt nicht: {path}")
    if file_hash(path) != sha256:
        raise OSError(f"Prüfsumme stimmt nicht: {path}")


def _publish_without_overwrite(source: Path, target: Path) -> None:
    """Publish a file without replacing an existing target."""
    try:
        os.link(source, target)
    except FileExistsError:
        raise
    except OSError as exc:
        raise OSError(f"Zieldatei konnte nicht exklusiv veröffentlicht werden: {exc}") from exc


def _new_transaction(source: Path, project_dir: Path, kind: str, suffix: str) -> ArchiveTransaction:
    folder = {"audio": "Audio", "image": "Bilder", "video": "Videos"}.get(kind, "Sonstiges")
    destination_dir = Path(project_dir) / "Verwendet" / folder
    destination_dir.mkdir(parents=True, exist_ok=True)
    target, reservation = _reserve_target(destination_dir, used_name(source, suffix))
    transaction_id = uuid.uuid4().hex
    journal = _transaction_dir(Path(project_dir)) / f"{transaction_id}.json"
    transaction = ArchiveTransaction(
        transaction_id=transaction_id,
        source=source,
        target=target,
        temp=None,
        reservation=reservation,
        journal=journal,
        expected_size=source.stat().st_size,
        expected_hash=file_hash(source),
        kind=kind,
    )
    _record_state(transaction, "prepared", "Quelle geprüft und Ziel exklusiv reserviert.")
    return transaction


def archive_file(source: Path, project_dir: Path, kind: str, suffix: str = "__verwendet") -> ArchiveRecord:
    source = Path(source)
    if not source.is_file():
        raise FileNotFoundError(source)
    transaction = _new_transaction(source, Path(project_dir), kind, suffix)
    same_device = source.stat().st_dev == transaction.target.parent.stat().st_dev
    status = "moved"
    try:
        if same_device:
            _publish_without_overwrite(source, transaction.target)
            _record_state(transaction, "published", "Quelle wurde ohne Überschreiben als Ziel veröffentlicht.")
            _verify_file(transaction.target, transaction.expected_size, transaction.expected_hash)
            _record_state(transaction, "verified_target", "Veröffentlichtes Ziel vollständig verifiziert.")
        else:
            fd, temp_name = tempfile.mkstemp(prefix="archive_", suffix=".part", dir=transaction.target.parent)
            os.close(fd)
            transaction.temp = Path(temp_name)
            _record_state(transaction, "copying", "Kopie auf dem Ziel-Dateisystem wird erstellt.")
            shutil.copy2(source, transaction.temp)
            _record_state(transaction, "copied", "Temporäre Kopie erstellt.")
            _verify_file(transaction.temp, transaction.expected_size, transaction.expected_hash)
            _record_state(transaction, "verified_temp", "Temporäre Kopie vollständig verifiziert.")
            _publish_without_overwrite(transaction.temp, transaction.target)
            _record_state(transaction, "published", "Zieldatei exklusiv veröffentlicht.")
            _verify_file(transaction.target, transaction.expected_size, transaction.expected_hash)
            _record_state(transaction, "verified_target", "Veröffentlichtes Ziel vollständig verifiziert.")
            transaction.temp.unlink(missing_ok=True)

        try:
            source.unlink()
        except OSError as exc:
            status = "copied_source_retained"
            _record_state(
                transaction,
                "source_retained",
                f"Ziel ist gültig; Original blieb wegen eines Löschfehlers erhalten: {exc}",
            )
        else:
            _record_state(transaction, "source_removed", "Original nach bestätigter Zielprüfung entfernt.")
            _record_state(transaction, "committed", "Archivtransaktion vollständig abgeschlossen.")

        _verify_file(transaction.target, transaction.expected_size, transaction.expected_hash)
        return ArchiveRecord(
            str(source),
            str(transaction.target),
            transaction.expected_size,
            transaction.expected_hash,
            kind,
            status,
            time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            transaction.transaction_id,
        )
    except Exception as exc:
        if transaction.target.exists() and transaction.state not in {"verified_target", "source_removed", "committed", "source_retained"}:
            try:
                transaction.target.unlink()
            except OSError:
                pass
        if transaction.temp:
            transaction.temp.unlink(missing_ok=True)
        safe = source.exists()
        _record_state(
            transaction,
            "failed_safe" if safe else "failed",
            f"Archivierung fehlgeschlagen; Original {'ist erhalten' if safe else 'konnte nicht bestätigt werden'}: {exc}",
        )
        raise
    finally:
        transaction.reservation.unlink(missing_ok=True)


def recover_archive_transactions(project_dir: Path) -> list[dict[str, str]]:
    """Recover or classify unfinished archive transactions without deleting source data."""
    results: list[dict[str, str]] = []
    directory = _transaction_dir(Path(project_dir))
    for journal in sorted(directory.glob("*.json")):
        try:
            payload = json.loads(journal.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            results.append({"journal": str(journal), "status": "invalid", "message": "Journal nicht lesbar."})
            continue
        state = str(payload.get("state", ""))
        if state in TERMINAL_STATES:
            continue
        source = Path(str(payload.get("source", "")))
        target = Path(str(payload.get("target", "")))
        temp = Path(str(payload.get("temp", ""))) if payload.get("temp") else None
        reservation = Path(str(payload.get("reservation", ""))) if payload.get("reservation") else None
        expected_size = int(payload.get("expected_size", 0) or 0)
        expected_hash = str(payload.get("expected_hash", ""))
        target_valid = False
        try:
            _verify_file(target, expected_size, expected_hash)
            target_valid = True
        except OSError:
            target_valid = False
        if target_valid and source.exists():
            payload["state"] = "source_retained"
            payload["message"] = "Wiederaufnahme: gültiges Ziel und Original vorhanden; Original bewusst erhalten."
        elif target_valid and not source.exists():
            payload["state"] = "committed"
            payload["message"] = "Wiederaufnahme: gültiges Ziel bestätigt und Original bereits entfernt."
        else:
            if temp:
                temp.unlink(missing_ok=True)
            payload["state"] = "failed_safe" if source.exists() else "failed"
            payload["message"] = "Wiederaufnahme: unvollständiges Ziel bereinigt; Originalstatus geprüft."
        payload["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        _atomic_json(journal, payload)
        if reservation:
            reservation.unlink(missing_ok=True)
        results.append({"journal": str(journal), "status": str(payload["state"]), "message": str(payload["message"])})
    return results


def append_manifest(project_dir: Path, records: list[ArchiveRecord]) -> Path:
    path = Path(project_dir) / "used_files_manifest.json"
    existing: list[dict[str, Any]] = []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        existing = raw.get("records", []) if isinstance(raw, dict) and isinstance(raw.get("records"), list) else []
    except (OSError, json.JSONDecodeError):
        pass
    payload = {
        "schema_version": 2,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "records": existing + [asdict(item) for item in records],
    }
    _atomic_json(path, payload)
    return path
