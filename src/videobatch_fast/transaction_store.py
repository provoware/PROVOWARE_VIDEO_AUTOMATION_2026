from __future__ import annotations

import base64
import hashlib
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from .safe_io import SafeIoError, atomic_write_bytes, atomic_write_json, exclusive_file_lock, fsync_directory

TRANSACTION_SCHEMA_VERSION = 1
MAX_TRANSACTION_BYTES = 32 * 1024 * 1024
MAX_AUDIT_BYTES = 2 * 1024 * 1024



class TransactionError(RuntimeError):
    """Raised when a durable multi-file transaction cannot be completed safely."""


class TransactionConflictError(TransactionError):
    """Raised when optimistic revision checks detect a stale writer."""


@dataclass(frozen=True)
class TransactionResult:
    transaction_id: str
    revisions: dict[str, int]
    recovered: bool = False


@dataclass(frozen=True)
class TransactionHealth:
    status: str
    pending: bool = False
    quarantined_count: int = 0
    orphan_revisions: tuple[str, ...] = ()
    issues: tuple[str, ...] = ()
    last_transaction_id: str = ""

    @property
    def healthy(self) -> bool:
        return self.status == "ok"


def _control_dir(root: Path) -> Path:
    return root / ".videobatch-transactions"


def _pending_path(root: Path) -> Path:
    return _control_dir(root) / "pending.json"


def _revisions_path(root: Path) -> Path:
    return _control_dir(root) / "revisions.json"


def _commit_path(root: Path) -> Path:
    return _control_dir(root) / "last-commit.json"


def _lock_path(root: Path) -> Path:
    return _control_dir(root) / ".transaction.lock"


def _quarantine_dir(root: Path) -> Path:
    return _control_dir(root) / "quarantine"


def _audit_path(root: Path) -> Path:
    return _control_dir(root) / "audit.jsonl"


def _append_audit(root: Path, event: str, **details: Any) -> None:
    control = _control_dir(root)
    control.mkdir(parents=True, exist_ok=True)
    path = _audit_path(root)
    payload = {
        "schema_version": 1,
        "at_unix_ns": time.time_ns(),
        "event": event,
        **details,
    }
    encoded = (json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    try:
        if path.exists() and path.stat().st_size + len(encoded) > MAX_AUDIT_BYTES:
            rotated = path.with_name("audit.previous.jsonl")
            os.replace(path, rotated)
            fsync_directory(control)
        with path.open("ab") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        fsync_directory(control)
    except (OSError, SafeIoError):
        # Observability must never weaken the transaction safety path.
        return


def _quarantine_file(root: Path, path: Path, *, reason: str) -> Path | None:
    if not path.exists():
        return None
    directory = _quarantine_dir(root)
    directory.mkdir(parents=True, exist_ok=True)
    stamp = f"{time.time_ns()}-{uuid.uuid4().hex[:8]}"
    target = directory / f"{path.name}.{stamp}.quarantine"
    try:
        os.replace(path, target)
        fsync_directory(directory)
        fsync_directory(path.parent)
    except (OSError, SafeIoError):
        return None
    _append_audit(root, "TRANSACTION_QUARANTINED", source=path.name, quarantine=target.name, reason=reason)
    return target


def _canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _hash_value(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _relative_key(root: Path, target: Path) -> str:
    try:
        relative = target.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise TransactionError(f"Transaktionsziel liegt außerhalb des Transaktionswurzelverzeichnisses: {target}") from exc
    if str(relative).startswith(".videobatch-transactions"):
        raise TransactionError("Transaktionskontrolldateien dürfen nicht als Nutzdaten überschrieben werden.")
    return relative.as_posix()


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TransactionError(f"Transaktionsmetadaten sind nicht sicher lesbar: {path}") from exc
    if not isinstance(value, dict):
        raise TransactionError(f"Transaktionsmetadaten haben ein ungültiges Format: {path}")
    return value


def _load_revisions(root: Path) -> dict[str, int]:
    raw = _read_json_object(_revisions_path(root))
    if not raw:
        return {}
    if int(raw.get("schema_version", 0) or 0) != TRANSACTION_SCHEMA_VERSION:
        raise TransactionError("Die Revisionsdatei verwendet eine nicht unterstützte Schemaversion.")
    values = raw.get("revisions", {})
    if not isinstance(values, dict):
        raise TransactionError("Die Revisionsdatei enthält keine gültige Revisionszuordnung.")
    result: dict[str, int] = {}
    for key, value in values.items():
        if not isinstance(key, str) or not isinstance(value, int) or value < 0:
            raise TransactionError("Die Revisionsdatei enthält ungültige Revisionswerte.")
        result[key] = value
    return result


def _write_revisions(root: Path, revisions: Mapping[str, int]) -> None:
    atomic_write_json(
        _revisions_path(root),
        {"schema_version": TRANSACTION_SCHEMA_VERSION, "revisions": dict(sorted(revisions.items()))},
    )


def _validate_journal(root: Path, journal: dict[str, Any]) -> tuple[str, list[dict[str, Any]], dict[str, int]]:
    if int(journal.get("schema_version", 0) or 0) != TRANSACTION_SCHEMA_VERSION:
        raise TransactionError("Das Write-Ahead-Journal verwendet eine nicht unterstützte Schemaversion.")
    txid = journal.get("transaction_id")
    writes = journal.get("writes")
    revisions = journal.get("revisions")
    if not isinstance(txid, str) or not txid or not isinstance(writes, list) or not isinstance(revisions, dict):
        raise TransactionError("Das Write-Ahead-Journal ist unvollständig.")
    if len(_canonical_bytes(journal)) > MAX_TRANSACTION_BYTES:
        raise TransactionError("Das Write-Ahead-Journal überschreitet das sichere Größenlimit.")
    clean_revisions: dict[str, int] = {}
    seen: set[str] = set()
    for key, value in revisions.items():
        if not isinstance(key, str) or not isinstance(value, int) or value < 1:
            raise TransactionError("Das Write-Ahead-Journal enthält ungültige Zielrevisionen.")
        clean_revisions[key] = value
    clean_writes: list[dict[str, Any]] = []
    for item in writes:
        if not isinstance(item, dict):
            raise TransactionError("Das Write-Ahead-Journal enthält einen ungültigen Schreibsatz.")
        key = item.get("path")
        value = item.get("value")
        digest = item.get("sha256")
        if not isinstance(key, str) or not key or key in seen or not isinstance(digest, str):
            raise TransactionError("Das Write-Ahead-Journal enthält ungültige oder doppelte Ziele.")
        target = (root / key).resolve()
        _relative_key(root, target)
        if _hash_value(value) != digest or clean_revisions.get(key, 0) < 1:
            raise TransactionError("Das Write-Ahead-Journal hat eine ungültige Nutzdatenintegrität.")
        seen.add(key)
        clean_writes.append({"path": key, "value": value, "sha256": digest})
    if seen != set(clean_revisions):
        raise TransactionError("Write-Ahead-Journal und Revisionssatz sind inkonsistent.")
    return txid, clean_writes, clean_revisions


def _apply_journal_locked(root: Path, journal: dict[str, Any], *, recovered: bool) -> TransactionResult:
    txid, writes, target_revisions = _validate_journal(root, journal)
    for item in writes:
        target = root / str(item["path"])
        target.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(target, item["value"])
    current = _load_revisions(root)
    current.update(target_revisions)
    _write_revisions(root, current)
    atomic_write_json(
        _commit_path(root),
        {
            "schema_version": TRANSACTION_SCHEMA_VERSION,
            "transaction_id": txid,
            "committed_at_unix_ns": time.time_ns(),
            "revisions": target_revisions,
        },
    )
    pending = _pending_path(root)
    try:
        pending.unlink(missing_ok=True)
        fsync_directory(pending.parent)
    except (OSError, SafeIoError) as exc:
        raise TransactionError("Der Commit wurde geschrieben, aber das Journal konnte nicht sicher abgeschlossen werden.") from exc
    _append_audit(root, "TRANSACTION_RECOVERED" if recovered else "TRANSACTION_COMMITTED", transaction_id=txid, revisions=target_revisions)
    return TransactionResult(txid, target_revisions, recovered=recovered)


def recover_pending_transaction(root: Path | str) -> TransactionResult | None:
    base = Path(root).expanduser().resolve()
    control = _control_dir(base)
    control.mkdir(parents=True, exist_ok=True)
    try:
        with exclusive_file_lock(_lock_path(base), timeout_seconds=5.0):
            pending = _pending_path(base)
            if not pending.exists():
                return None
            try:
                journal = _read_json_object(pending)
                return _apply_journal_locked(base, journal, recovered=True)
            except TransactionError as exc:
                _quarantine_file(base, pending, reason=str(exc))
                _append_audit(base, "TRANSACTION_RECOVERY_BLOCKED", error=str(exc))
                raise
    except SafeIoError as exc:
        raise TransactionError("Transaction-Recovery ist durch einen parallelen Schreibvorgang blockiert.") from exc


def _before_snapshot(target: Path) -> dict[str, Any]:
    if not target.exists():
        return {"exists": False}
    try:
        raw = target.read_bytes()
    except OSError as exc:
        raise TransactionError(f"Der Vorzustand von {target} ist nicht sicher lesbar.") from exc
    return {
        "exists": True,
        "format": "raw-base64",
        "raw_base64": base64.b64encode(raw).decode("ascii"),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def rollback_pending_transaction(root: Path | str) -> TransactionResult | None:
    """Restore the captured pre-transaction state and discard a valid pending WAL.

    Rollback is explicit and conservative. Corrupt journals are quarantined and
    never trusted as rollback sources.
    """
    base = Path(root).expanduser().resolve()
    control = _control_dir(base)
    control.mkdir(parents=True, exist_ok=True)
    try:
        with exclusive_file_lock(_lock_path(base), timeout_seconds=5.0):
            pending = _pending_path(base)
            if not pending.exists():
                return None
            try:
                journal = _read_json_object(pending)
                txid, writes, target_revisions = _validate_journal(base, journal)
                by_path = {str(item["path"]): item for item in journal.get("writes", []) if isinstance(item, dict)}
                for write in reversed(writes):
                    key = str(write["path"])
                    raw = by_path[key].get("before")
                    if not isinstance(raw, dict) or not isinstance(raw.get("exists"), bool):
                        raise TransactionError("Das Journal enthält keinen verlässlichen Rollback-Vorzustand.")
                    target = base / key
                    if raw["exists"]:
                        digest = raw.get("sha256")
                        target.parent.mkdir(parents=True, exist_ok=True)
                        if raw.get("format") == "raw-base64":
                            encoded = raw.get("raw_base64")
                            if not isinstance(encoded, str) or not isinstance(digest, str):
                                raise TransactionError("Der Rollback-Rohzustand ist unvollständig.")
                            try:
                                payload = base64.b64decode(encoded.encode("ascii"), validate=True)
                            except (ValueError, UnicodeError) as exc:
                                raise TransactionError("Der Rollback-Rohzustand ist nicht dekodierbar.") from exc
                            if hashlib.sha256(payload).hexdigest() != digest:
                                raise TransactionError("Der Rollback-Rohzustand hat eine ungültige Integrität.")
                            atomic_write_bytes(target, payload)
                        else:
                            value = raw.get("value")
                            if not isinstance(digest, str) or hashlib.sha256(_canonical_bytes(value)).hexdigest() != digest:
                                # Legacy snapshots used canonical JSON hashes.
                                if not isinstance(digest, str) or _hash_value(value) != digest:
                                    raise TransactionError("Der Rollback-Vorzustand hat eine ungültige Integrität.")
                            atomic_write_json(target, value)
                    elif target.exists():
                        target.unlink()
                        fsync_directory(target.parent)
                pending.unlink(missing_ok=True)
                fsync_directory(pending.parent)
                _append_audit(base, "TRANSACTION_ROLLED_BACK", transaction_id=txid, revisions=target_revisions)
                return TransactionResult(txid, target_revisions, recovered=False)
            except TransactionError as exc:
                _quarantine_file(base, pending, reason=f"Rollback nicht sicher möglich: {exc}")
                _append_audit(base, "TRANSACTION_ROLLBACK_BLOCKED", error=str(exc))
                raise
    except SafeIoError as exc:
        raise TransactionError("Transaction-Rollback ist durch einen parallelen Schreibvorgang blockiert.") from exc


def transactional_write_json(
    root: Path | str,
    updates: Mapping[Path | str, Any],
    *,
    expected_revisions: Mapping[Path | str, int] | None = None,
    _crash_after_writes: int | None = None,
) -> TransactionResult:
    """Durably update related JSON files with WAL-style roll-forward recovery.

    The durable pending journal is the commit intent. Once written, recovery always
    completes all listed writes. Optional expected revisions reject stale writers.
    ``_crash_after_writes`` exists only for deterministic fault-injection tests.
    """
    base = Path(root).expanduser().resolve()
    if not updates:
        raise TransactionError("Eine Transaktion benötigt mindestens ein Ziel.")
    base.mkdir(parents=True, exist_ok=True)
    _control_dir(base).mkdir(parents=True, exist_ok=True)
    try:
        with exclusive_file_lock(_lock_path(base), timeout_seconds=10.0):
            pending = _pending_path(base)
            if pending.exists():
                _apply_journal_locked(base, _read_json_object(pending), recovered=True)
            current = _load_revisions(base)
            prepared: list[tuple[str, Any, dict[str, Any]]] = []
            for raw_path, value in updates.items():
                target = Path(raw_path).expanduser()
                if not target.is_absolute():
                    target = base / target
                key = _relative_key(base, target)
                prepared.append((key, value, _before_snapshot(target)))
            if len({key for key, _, _before in prepared}) != len(prepared):
                raise TransactionError("Eine Transaktion darf dasselbe Ziel nicht mehrfach enthalten.")
            expected: dict[str, int] = {}
            for raw_path, revision in (expected_revisions or {}).items():
                target = Path(raw_path).expanduser()
                if not target.is_absolute():
                    target = base / target
                key = _relative_key(base, target)
                expected[key] = int(revision)
            for key, revision in expected.items():
                actual = current.get(key, 0)
                if actual != revision:
                    raise TransactionConflictError(
                        f"Veralteter Schreibstand für {key}: erwartet Revision {revision}, aktuell {actual}."
                    )
            revisions = {key: current.get(key, 0) + 1 for key, _value, _before in prepared}
            txid = uuid.uuid4().hex
            journal = {
                "schema_version": TRANSACTION_SCHEMA_VERSION,
                "transaction_id": txid,
                "prepared_at_unix_ns": time.time_ns(),
                "writer_pid": os.getpid(),
                "writes": [
                    {"path": key, "value": value, "sha256": _hash_value(value), "before": before}
                    for key, value, before in prepared
                ],
                "revisions": revisions,
            }
            if len(_canonical_bytes(journal)) > MAX_TRANSACTION_BYTES:
                raise TransactionError("Die Transaktion überschreitet das sichere Journalgrößenlimit.")
            atomic_write_json(pending, journal)
            if _crash_after_writes == 0:
                raise RuntimeError("fault-injection: crash after durable WAL")
            count = 0
            for item in journal["writes"]:
                target = base / item["path"]
                target.parent.mkdir(parents=True, exist_ok=True)
                atomic_write_json(target, item["value"])
                count += 1
                if _crash_after_writes is not None and count >= _crash_after_writes:
                    raise RuntimeError(f"fault-injection: crash after {count} writes")
            current.update(revisions)
            _write_revisions(base, current)
            atomic_write_json(
                _commit_path(base),
                {
                    "schema_version": TRANSACTION_SCHEMA_VERSION,
                    "transaction_id": txid,
                    "committed_at_unix_ns": time.time_ns(),
                    "revisions": revisions,
                },
            )
            pending.unlink(missing_ok=True)
            fsync_directory(pending.parent)
            _append_audit(base, "TRANSACTION_COMMITTED", transaction_id=txid, revisions=revisions)
            return TransactionResult(txid, revisions, recovered=False)
    except SafeIoError as exc:
        raise TransactionError("Die Transaktion konnte nicht dauerhaft serialisiert werden.") from exc



def transaction_audit_timeline(root: Path | str, *, limit: int = 100) -> list[dict[str, Any]]:
    base = Path(root).expanduser().resolve()
    events: list[dict[str, Any]] = []
    for path in (_audit_path(base).with_name("audit.previous.jsonl"), _audit_path(base)):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError):
            continue
        for line in lines:
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                events.append(value)
    return events[-max(0, int(limit)):]


def inspect_transaction_state(root: Path | str, *, recover: bool = False) -> TransactionHealth:
    """Inspect transaction control state without trusting corrupt metadata.

    ``recover=True`` attempts REDO of a valid pending WAL. Invalid WAL is
    quarantined by the recovery path and reported as degraded, never applied.
    """
    base = Path(root).expanduser().resolve()
    control = _control_dir(base)
    control.mkdir(parents=True, exist_ok=True)
    issues: list[str] = []
    pending = _pending_path(base)
    if pending.exists():
        if recover:
            try:
                recover_pending_transaction(base)
            except TransactionError as exc:
                issues.append(str(exc))
        else:
            try:
                _validate_journal(base, _read_json_object(pending))
                issues.append("Eine vollständige, noch nicht abgeschlossene Transaktion wartet auf Recovery.")
            except TransactionError as exc:
                issues.append(f"Beschädigtes Pending-Journal: {exc}")

    revisions: dict[str, int] = {}
    try:
        revisions = _load_revisions(base)
    except TransactionError as exc:
        issues.append(str(exc))
        _quarantine_file(base, _revisions_path(base), reason=str(exc))

    orphan: list[str] = []
    for key in sorted(revisions):
        target = base / key
        if not target.exists():
            orphan.append(key)
    if orphan:
        issues.append(f"{len(orphan)} verwaiste Revisionszuordnung(en) erkannt.")

    last_tx = ""
    commit = _commit_path(base)
    if commit.exists():
        try:
            marker = _read_json_object(commit)
            if int(marker.get("schema_version", 0) or 0) != TRANSACTION_SCHEMA_VERSION:
                raise TransactionError("Der Commit-Marker verwendet eine nicht unterstützte Schemaversion.")
            txid = marker.get("transaction_id")
            marker_revisions = marker.get("revisions")
            if not isinstance(txid, str) or not txid or not isinstance(marker_revisions, dict):
                raise TransactionError("Der Commit-Marker ist unvollständig.")
            last_tx = txid
            for key, value in marker_revisions.items():
                if not isinstance(key, str) or not isinstance(value, int) or revisions.get(key, 0) < value:
                    raise TransactionError("Commit-Marker und Revisionsregister sind inkonsistent.")
        except TransactionError as exc:
            issues.append(str(exc))
            _quarantine_file(base, commit, reason=str(exc))

    quarantine_count = 0
    try:
        quarantine_count = sum(1 for item in _quarantine_dir(base).iterdir() if item.is_file())
    except OSError:
        pass
    status = "ok" if not issues else "degraded"
    health = TransactionHealth(
        status=status,
        pending=_pending_path(base).exists(),
        quarantined_count=quarantine_count,
        orphan_revisions=tuple(orphan),
        issues=tuple(issues),
        last_transaction_id=last_tx,
    )
    _append_audit(
        base,
        "TRANSACTION_HEALTH_CHECK",
        status=health.status,
        pending=health.pending,
        quarantined_count=health.quarantined_count,
        orphan_revisions=list(health.orphan_revisions),
        issues=list(health.issues),
    )
    return health


def prune_orphan_revisions(root: Path | str) -> tuple[str, ...]:
    """Remove revision entries whose target files no longer exist.

    This is a metadata-only rollback: user data is never deleted or rewritten.
    """
    base = Path(root).expanduser().resolve()
    with exclusive_file_lock(_lock_path(base), timeout_seconds=5.0):
        revisions = _load_revisions(base)
        orphan = tuple(sorted(key for key in revisions if not (base / key).exists()))
        if not orphan:
            return ()
        for key in orphan:
            revisions.pop(key, None)
        _write_revisions(base, revisions)
        _append_audit(base, "ORPHAN_REVISIONS_PRUNED", paths=list(orphan))
        return orphan


def current_revision(root: Path | str, target: Path | str) -> int:
    base = Path(root).expanduser().resolve()
    recover_pending_transaction(base)
    path = Path(target).expanduser()
    if not path.is_absolute():
        path = base / path
    key = _relative_key(base, path)
    return _load_revisions(base).get(key, 0)
