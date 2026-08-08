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
from typing import Any, Iterable, Mapping

from .paths import state_dir
from .safe_io import SafeIoError, atomic_write_bytes, atomic_write_json, exclusive_file_lock, fsync_directory
from .checkpoint_trust import CheckpointTrustError, sign_payload, verify_payload, write_prune_anchor

CHECKPOINT_SCHEMA_VERSION = 1
GRAPH_SCHEMA_VERSION = 1
RESTORE_SCHEMA_VERSION = 2
MAX_CHECKPOINT_FILES = 512
MAX_CHECKPOINT_FILE_BYTES = 32 * 1024 * 1024
MAX_CHECKPOINT_TOTAL_BYTES = 256 * 1024 * 1024
DEFAULT_CHECKPOINT_RETENTION = 12
GENERATION_FINGERPRINT_VERSION = 2

def default_checkpoint_root() -> Path:
    return state_dir() / "recovery-checkpoints"

class CheckpointError(RuntimeError):
    """Raised when a system checkpoint cannot be created, verified, or restored safely."""

@dataclass(frozen=True, slots=True)
class CheckpointRecord:
    generation_id: str
    created_at_unix_ns: int
    file_count: int
    total_bytes: int
    parent_generation_id: str = ""

@dataclass(frozen=True, slots=True)
class RestoreProbe:
    generation_id: str
    ok: bool
    target_count: int
    total_bytes: int
    issues: tuple[str, ...] = ()

@dataclass(frozen=True, slots=True)
class CheckpointHealth:
    status: str
    generation_count: int
    valid_generations: tuple[str, ...]
    invalid_generations: tuple[str, ...]
    creating_residue: tuple[str, ...]
    pending_restore: bool
    issues: tuple[str, ...] = ()

    @property
    def healthy(self) -> bool:
        return self.status == "ok"

def _control_dir(root: Path) -> Path:
    return root / ".videobatch-checkpoints"

def _generations_dir(root: Path) -> Path:
    return _control_dir(root) / "generations"

def _graph_path(root: Path) -> Path:
    return _control_dir(root) / "graph.json"

def _lock_path(root: Path) -> Path:
    return _control_dir(root) / ".checkpoint.lock"

def _pending_restore_path(root: Path) -> Path:
    return _control_dir(root) / "pending-restore.json"

def _audit_path(root: Path) -> Path:
    return _control_dir(root) / "audit.jsonl"

def _canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")

def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()

def _append_audit(root: Path, event: str, **details: Any) -> None:
    control = _control_dir(root)
    control.mkdir(parents=True, exist_ok=True)
    path = _audit_path(root)
    previous_hash = ""
    if path.exists():
        try:
            lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
            if lines:
                last = json.loads(lines[-1])
                if isinstance(last, dict) and isinstance(last.get("entry_hash_sha256"), str):
                    previous_hash = last["entry_hash_sha256"]
        except (OSError, UnicodeError, json.JSONDecodeError):
            previous_hash = "BROKEN-CHAIN"
    payload = {
        "schema_version": 2,
        "at_unix_ns": time.time_ns(),
        "event": event,
        "previous_hash_sha256": previous_hash,
        **details,
    }
    unsigned = dict(payload)
    payload["entry_hash_sha256"] = _sha256_bytes(_canonical_json(unsigned))
    try:
        payload["authentication"] = sign_payload(root, payload)
    except CheckpointTrustError:
        payload["authentication"] = {}
    encoded = _canonical_json(payload)
    try:
        with path.open("ab") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        fsync_directory(control)
    except (OSError, SafeIoError):
        return

def _fingerprint_manifest(manifest: Mapping[str, Any]) -> str:
    semantic = {key: value for key, value in manifest.items() if key not in {"fingerprint_sha256", "authentication"}}
    return _sha256_bytes(_canonical_json(semantic))

def _valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)

def generation_fingerprint(root: Path | str, generation_id: str) -> str:
    base = Path(root).expanduser().resolve()
    manifest = _generation_manifest(base, generation_id)
    declared = manifest.get("fingerprint_sha256")
    calculated = _fingerprint_manifest(manifest)
    if declared not in (None, ""):
        if not _valid_sha256(declared) or declared != calculated:
            raise CheckpointError(f"Checkpoint-Generationsfingerprint ist ungültig: {generation_id}")
    return calculated

def _normalize_sources(sources: Mapping[str, Path | str] | Iterable[tuple[str, Path | str]]) -> list[tuple[str, Path]]:
    items = list(sources.items()) if isinstance(sources, Mapping) else list(sources)
    if not items:
        raise CheckpointError("Ein System-Checkpoint benötigt mindestens eine Zustandsquelle.")
    if len(items) > MAX_CHECKPOINT_FILES:
        raise CheckpointError("Der System-Checkpoint überschreitet die zulässige Dateianzahl.")
    normalized: list[tuple[str, Path]] = []
    seen: set[Path] = set()
    for domain, raw_path in items:
        if not isinstance(domain, str) or not domain.strip():
            raise CheckpointError("Jede Checkpoint-Quelle benötigt eine eindeutige Domäne.")
        path = Path(raw_path).expanduser().resolve()
        if path in seen:
            raise CheckpointError(f"Checkpoint-Quelle ist doppelt enthalten: {path}")
        seen.add(path)
        normalized.append((domain.strip(), path))
    return normalized

def collect_recovery_sources(
    *,
    project_path: Path | str | None = None,
    config_path: Path | str | None = None,
    jobs_root: Path | str | None = None,
    backup_dir: Path | str | None = None,
) -> list[tuple[str, Path]]:
    """Collect the bounded recovery-state files that form one logical system generation."""
    result: list[tuple[str, Path]] = []
    if project_path is not None:
        result.append(("project", Path(project_path).expanduser().resolve()))
    if config_path is not None:
        result.append(("config", Path(config_path).expanduser().resolve()))
    if jobs_root is not None:
        jobs = Path(jobs_root).expanduser().resolve()
        result.append(("queue", jobs / "retry_queue.json"))
        for folder_name in ("active", "history"):
            folder = jobs / folder_name
            if folder.is_dir():
                for path in sorted(folder.glob("*.json")):
                    result.append(("job-journal", path.resolve()))
                    if len(result) >= MAX_CHECKPOINT_FILES:
                        raise CheckpointError("Zu viele Job-Journal-Dateien für einen einzelnen Checkpoint.")
    if backup_dir is not None:
        backup = Path(backup_dir).expanduser().resolve()
        result.append(("backup", backup / "history.json"))
        result.append(("backup", backup / "history.meta.json"))
    return _normalize_sources(result)

def _read_source(path: Path) -> tuple[bool, bytes, int]:
    if not path.exists():
        return False, b"", 0
    if not path.is_file():
        raise CheckpointError(f"Checkpoint-Quelle ist keine reguläre Datei: {path}")
    try:
        stat_before = path.stat()
        if stat_before.st_size > MAX_CHECKPOINT_FILE_BYTES:
            raise CheckpointError(f"Checkpoint-Quelle überschreitet das Einzeldateilimit: {path}")
        payload = path.read_bytes()
        stat_after = path.stat()
    except OSError as exc:
        raise CheckpointError(f"Checkpoint-Quelle konnte nicht stabil gelesen werden: {path}") from exc
    if stat_before.st_size != stat_after.st_size or stat_before.st_mtime_ns != stat_after.st_mtime_ns:
        raise CheckpointError(f"Checkpoint-Quelle änderte sich während der Aufnahme: {path}")
    return True, payload, stat_after.st_mtime_ns

def _manifest_path(generation_dir: Path) -> Path:
    return generation_dir / "manifest.json"

def _generation_manifest(root: Path, generation_id: str) -> dict[str, Any]:
    path = _manifest_path(_generations_dir(root) / generation_id)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CheckpointError(f"Checkpoint-Manifest ist nicht lesbar: {generation_id}") from exc
    if not isinstance(value, dict) or int(value.get("schema_version", 0) or 0) != CHECKPOINT_SCHEMA_VERSION:
        raise CheckpointError(f"Checkpoint-Manifest verwendet ein ungültiges Schema: {generation_id}")
    return value


def _verify_manifest_authentication(root: Path, generation_id: str, manifest: Mapping[str, Any]) -> None:
    auth = manifest.get("authentication")
    if auth in (None, {}):
        return
    unsigned = {key: value for key, value in manifest.items() if key != "authentication"}
    if not isinstance(auth, dict) or not verify_payload(root, unsigned, auth):
        raise CheckpointError(f"Checkpoint-Authentifizierung ist ungültig: {generation_id}")

def verify_checkpoint(root: Path | str, generation_id: str) -> CheckpointRecord:
    base = Path(root).expanduser().resolve()
    generation = _generations_dir(base) / generation_id
    if not generation.is_dir() or generation.name.startswith(".creating-"):
        raise CheckpointError(f"Checkpoint-Generation ist nicht vorhanden: {generation_id}")
    manifest = _generation_manifest(base, generation_id)
    if manifest.get("generation_id") != generation_id:
        raise CheckpointError("Generation-ID und Manifest stimmen nicht überein.")
    files = manifest.get("files")
    if not isinstance(files, list) or len(files) > MAX_CHECKPOINT_FILES:
        raise CheckpointError("Checkpoint-Manifest enthält eine ungültige Dateiliste.")
    total = 0
    seen_slots: set[str] = set()
    for item in files:
        if not isinstance(item, dict):
            raise CheckpointError("Checkpoint-Manifest enthält einen ungültigen Snapshot-Eintrag.")
        slot = item.get("snapshot")
        exists = item.get("exists")
        digest = item.get("sha256")
        size = item.get("size_bytes")
        target = item.get("target")
        if not isinstance(target, str) or not target or not isinstance(exists, bool) or not isinstance(size, int) or size < 0:
            raise CheckpointError("Checkpoint-Manifest enthält ungültige Zielmetadaten.")
        if not exists:
            if slot not in (None, "") or digest not in (None, "") or size != 0:
                raise CheckpointError("Nicht vorhandene Checkpoint-Ziele besitzen unerwartete Snapshot-Daten.")
            continue
        if not isinstance(slot, str) or not slot or slot in seen_slots or not isinstance(digest, str):
            raise CheckpointError("Checkpoint-Snapshotreferenz ist ungültig oder doppelt.")
        seen_slots.add(slot)
        snapshot = generation / "snapshots" / slot
        try:
            payload = snapshot.read_bytes()
        except OSError as exc:
            raise CheckpointError(f"Checkpoint-Snapshot fehlt oder ist nicht lesbar: {slot}") from exc
        if len(payload) != size or _sha256_bytes(payload) != digest:
            raise CheckpointError(f"Checkpoint-Snapshot ist beschädigt: {slot}")
        total += len(payload)
        if total > MAX_CHECKPOINT_TOTAL_BYTES:
            raise CheckpointError("Checkpoint überschreitet das Gesamtgrößenlimit.")
    declared_total = int(manifest.get("total_bytes", -1))
    if declared_total != total or int(manifest.get("file_count", -1)) != len(files):
        raise CheckpointError("Checkpoint-Gesamtmetadaten stimmen nicht mit den Snapshots überein.")
    generation_fingerprint(base, generation_id)
    _verify_manifest_authentication(base, generation_id, manifest)
    return CheckpointRecord(
        generation_id=generation_id,
        created_at_unix_ns=int(manifest.get("created_at_unix_ns", 0) or 0),
        file_count=len(files),
        total_bytes=total,
    )

def _scan_valid_generations(root: Path) -> tuple[list[CheckpointRecord], list[str]]:
    generations = _generations_dir(root)
    generations.mkdir(parents=True, exist_ok=True)
    valid: list[CheckpointRecord] = []
    invalid: list[str] = []
    for path in sorted(generations.iterdir()):
        if not path.is_dir() or path.name.startswith(".creating-"):
            continue
        try:
            valid.append(verify_checkpoint(root, path.name))
        except CheckpointError:
            invalid.append(path.name)
    valid.sort(key=lambda item: (item.created_at_unix_ns, item.generation_id))
    return valid, invalid

def _write_graph(root: Path, records: list[CheckpointRecord]) -> None:
    nodes: list[dict[str, Any]] = []
    parent = ""
    for record in records:
        manifest = _manifest_path(_generations_dir(root) / record.generation_id).read_bytes()
        nodes.append({
            "generation_id": record.generation_id,
            "created_at_unix_ns": record.created_at_unix_ns,
            "parent_generation_id": parent,
            "manifest_sha256": _sha256_bytes(manifest),
            "generation_fingerprint_sha256": generation_fingerprint(root, record.generation_id),
        })
        parent = record.generation_id
    atomic_write_json(_graph_path(root), {"schema_version": GRAPH_SCHEMA_VERSION, "nodes": nodes})

def reconcile_generation_graph(root: Path | str) -> list[CheckpointRecord]:
    base = Path(root).expanduser().resolve()
    _control_dir(base).mkdir(parents=True, exist_ok=True)
    records, _invalid = _scan_valid_generations(base)
    _write_graph(base, records)
    return [
        CheckpointRecord(
            item.generation_id,
            item.created_at_unix_ns,
            item.file_count,
            item.total_bytes,
            records[index - 1].generation_id if index else "",
        )
        for index, item in enumerate(records)
    ]

def list_checkpoints(root: Path | str, *, limit: int | None = None) -> list[CheckpointRecord]:
    records = reconcile_generation_graph(root)
    records.reverse()
    return records if limit is None else records[: max(0, int(limit))]

def cleanup_incomplete_checkpoint_creations(root: Path | str) -> tuple[str, ...]:
    base = Path(root).expanduser().resolve()
    generations = _generations_dir(base)
    generations.mkdir(parents=True, exist_ok=True)
    removed: list[str] = []
    for path in generations.glob(".creating-*"):
        if not path.is_dir():
            continue
        try:
            shutil.rmtree(path)
            removed.append(path.name)
        except OSError:
            continue
    if removed:
        fsync_directory(generations)
        _append_audit(base, "CHECKPOINT_INCOMPLETE_CLEANED", generations=removed)
    return tuple(sorted(removed))

def create_system_checkpoint(
    root: Path | str,
    sources: Mapping[str, Path | str] | Iterable[tuple[str, Path | str]],
    *,
    _crash_stage: str = "",
) -> CheckpointRecord:
    """Create a verified generation using a hidden staging directory and optimistic stable-read checks."""
    base = Path(root).expanduser().resolve()
    normalized = _normalize_sources(sources)
    control = _control_dir(base)
    generations = _generations_dir(base)
    generations.mkdir(parents=True, exist_ok=True)
    try:
        with exclusive_file_lock(_lock_path(base), timeout_seconds=10.0):
            cleanup_incomplete_checkpoint_creations(base)
            generation_id = f"{time.time_ns()}-{uuid.uuid4().hex[:12]}"
            staging = generations / f".creating-{generation_id}"
            snapshots = staging / "snapshots"
            snapshots.mkdir(parents=True, exist_ok=False)
            manifest_files: list[dict[str, Any]] = []
            total = 0
            stable_checks: list[tuple[Path, bool, str, int]] = []
            try:
                for index, (domain, path) in enumerate(normalized):
                    exists, payload, mtime_ns = _read_source(path)
                    digest = _sha256_bytes(payload) if exists else ""
                    slot = f"{index:04d}-{digest[:16]}.bin" if exists else ""
                    if exists:
                        total += len(payload)
                        if total > MAX_CHECKPOINT_TOTAL_BYTES:
                            raise CheckpointError("Checkpoint überschreitet das Gesamtgrößenlimit.")
                        snapshot = snapshots / slot
                        atomic_write_bytes(snapshot, payload)
                    manifest_files.append({
                        "domain": domain,
                        "target": str(path),
                        "exists": exists,
                        "snapshot": slot,
                        "sha256": digest,
                        "size_bytes": len(payload) if exists else 0,
                    })
                    stable_checks.append((path, exists, digest, mtime_ns))
                    if _crash_stage == f"after_snapshot_{index + 1}":
                        raise RuntimeError(f"fault-injection: crash after snapshot {index + 1}")
                # Second pass rejects a mixed generation if any cooperating/non-cooperating writer changed a source.
                for path, existed, digest, mtime_ns in stable_checks:
                    if path.exists() != existed:
                        raise CheckpointError(f"Checkpoint-Quelle änderte ihren Existenzzustand während der Aufnahme: {path}")
                    if not existed:
                        continue
                    try:
                        stat = path.stat()
                        current = path.read_bytes()
                    except OSError as exc:
                        raise CheckpointError(f"Checkpoint-Quelle konnte nicht erneut geprüft werden: {path}") from exc
                    if stat.st_mtime_ns != mtime_ns or _sha256_bytes(current) != digest:
                        raise CheckpointError(f"Checkpoint-Quelle änderte sich während der Generationserstellung: {path}")
                existing_records, _existing_invalid = _scan_valid_generations(base)
                parent_generation_id = existing_records[-1].generation_id if existing_records else ""
                parent_fingerprint_sha256 = generation_fingerprint(base, parent_generation_id) if parent_generation_id else ""
                manifest = {
                    "schema_version": CHECKPOINT_SCHEMA_VERSION,
                    "generation_id": generation_id,
                    "created_at_unix_ns": time.time_ns(),
                    "parent_generation_id": parent_generation_id,
                    "parent_fingerprint_sha256": parent_fingerprint_sha256,
                    "file_count": len(manifest_files),
                    "total_bytes": total,
                    "fingerprint_version": GENERATION_FINGERPRINT_VERSION,
                    "files": manifest_files,
                }
                manifest["fingerprint_sha256"] = _fingerprint_manifest(manifest)
                manifest["authentication"] = sign_payload(base, manifest)
                atomic_write_json(_manifest_path(staging), manifest)
                fsync_directory(snapshots)
                fsync_directory(staging)
                if _crash_stage == "after_manifest":
                    raise RuntimeError("fault-injection: crash after durable checkpoint manifest")
                final = generations / generation_id
                os.replace(staging, final)
                fsync_directory(generations)
                if _crash_stage == "after_publish":
                    raise RuntimeError("fault-injection: crash after checkpoint publication")
                record = verify_checkpoint(base, generation_id)
                records = reconcile_generation_graph(base)
                parent = next((item.parent_generation_id for item in records if item.generation_id == generation_id), "")
                _append_audit(base, "CHECKPOINT_CREATED", generation_id=generation_id, files=record.file_count, total_bytes=record.total_bytes)
                return CheckpointRecord(record.generation_id, record.created_at_unix_ns, record.file_count, record.total_bytes, parent)
            except Exception:
                if staging.exists() and _crash_stage == "":
                    shutil.rmtree(staging, ignore_errors=True)
                raise
    except SafeIoError as exc:
        raise CheckpointError("Checkpoint-Erstellung ist durch einen parallelen Vorgang blockiert.") from exc

def inspect_checkpoint_state(root: Path | str, *, repair: bool = False) -> CheckpointHealth:
    base = Path(root).expanduser().resolve()
    generations = _generations_dir(base)
    generations.mkdir(parents=True, exist_ok=True)
    residues = tuple(sorted(path.name for path in generations.glob(".creating-*") if path.is_dir()))
    if repair and residues:
        cleanup_incomplete_checkpoint_creations(base)
        residues = ()
    valid, invalid = _scan_valid_generations(base)
    if repair:
        _write_graph(base, valid)
    issues: list[str] = []
    if invalid:
        issues.append(f"{len(invalid)} beschädigte Checkpoint-Generation(en) erkannt.")
    if residues:
        issues.append(f"{len(residues)} unvollständige Checkpoint-Erstellung(en) erkannt.")
    pending_restore = _pending_restore_path(base).exists()
    if pending_restore:
        issues.append("Ein noch nicht abgeschlossener Checkpoint-Restore wartet auf Recovery.")
    return CheckpointHealth(
        status="ok" if not issues else "degraded",
        generation_count=len(valid),
        valid_generations=tuple(item.generation_id for item in valid),
        invalid_generations=tuple(invalid),
        creating_residue=residues,
        pending_restore=pending_restore,
        issues=tuple(issues),
    )

def _restore_entries(root: Path, generation_id: str) -> list[dict[str, Any]]:
    verify_checkpoint(root, generation_id)
    manifest = _generation_manifest(root, generation_id)
    result: list[dict[str, Any]] = []
    for item in manifest["files"]:
        result.append(dict(item))
    return result

def probe_checkpoint_restore(root: Path | str, generation_id: str) -> RestoreProbe:
    base = Path(root).expanduser().resolve()
    issues: list[str] = []
    try:
        entries = _restore_entries(base, generation_id)
    except CheckpointError as exc:
        return RestoreProbe(generation_id, False, 0, 0, (str(exc),))
    total = 0
    probed_parents: set[Path] = set()
    for item in entries:
        target = Path(item["target"])
        if item["exists"]:
            snapshot = _generations_dir(base) / generation_id / "snapshots" / item["snapshot"]
            try:
                payload = snapshot.read_bytes()
            except OSError:
                issues.append(f"Snapshot nicht lesbar: {item['snapshot']}")
                continue
            total += len(payload)
        parent = target.parent
        while not parent.exists() and parent != parent.parent:
            parent = parent.parent
        if not parent.exists():
            issues.append(f"Restore-Ziel besitzt keinen erreichbaren Elternordner: {target}")
            continue
        if parent in probed_parents:
            continue
        probed_parents.add(parent)
        probe_name = ""
        try:
            descriptor, probe_name = tempfile.mkstemp(prefix=".videobatch-restore-probe-", dir=parent)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(b"probe")
                handle.flush()
                os.fsync(handle.fileno())
            Path(probe_name).unlink(missing_ok=True)
            fsync_directory(parent)
        except (OSError, SafeIoError):
            if probe_name:
                try:
                    Path(probe_name).unlink(missing_ok=True)
                except OSError:
                    pass
            issues.append(f"Restore-Ziel-Dateisystem ist nicht dauerhaft beschreibbar: {target}")
    try:
        free = shutil.disk_usage(base).free
        if free < total + 1024 * 1024:
            issues.append("Nicht genügend freier Speicher für den Restore-Puffer.")
    except OSError:
        issues.append("Freier Speicher konnte vor dem Restore nicht geprüft werden.")
    return RestoreProbe(generation_id, not issues, len(entries), total, tuple(issues))

def _write_restore_journal(root: Path, generation_id: str, entries: list[dict[str, Any]]) -> None:
    journal = {
        "schema_version": RESTORE_SCHEMA_VERSION,
        "restore_id": uuid.uuid4().hex,
        "generation_id": generation_id,
        "generation_fingerprint_sha256": generation_fingerprint(root, generation_id),
        "authorization_policy": "trusted-generation-required",
        "prepared_at_unix_ns": time.time_ns(),
        "targets": [
            {
                "target": item["target"],
                "exists": item["exists"],
                "snapshot": item["snapshot"],
                "sha256": item["sha256"],
            }
            for item in entries
        ],
    }
    journal["authentication"] = sign_payload(root, journal)
    atomic_write_json(_pending_restore_path(root), journal)

def _load_restore_journal(root: Path) -> dict[str, Any]:
    try:
        value = json.loads(_pending_restore_path(root).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CheckpointError("Pending-Restore-Journal ist nicht sicher lesbar.") from exc
    if not isinstance(value, dict) or int(value.get("schema_version", 0) or 0) != RESTORE_SCHEMA_VERSION:
        raise CheckpointError("Pending-Restore-Journal besitzt ein ungültiges Schema.")
    generation_id = value.get("generation_id")
    targets = value.get("targets")
    if not isinstance(generation_id, str) or not generation_id or not isinstance(targets, list):
        raise CheckpointError("Pending-Restore-Journal ist unvollständig.")
    auth = value.get("authentication")
    unsigned = {key: item for key, item in value.items() if key != "authentication"}
    if not isinstance(auth, dict) or not verify_payload(root, unsigned, auth):
        raise CheckpointError("Pending-Restore-Journal ist nicht authentifiziert oder wurde verändert.")
    return value

def _apply_restore_locked(root: Path, journal: dict[str, Any], *, recovered: bool, _crash_after_writes: int | None = None) -> CheckpointRecord:
    generation_id = str(journal["generation_id"])
    from .checkpoint_trust_chain import require_trusted_generation
    require_trusted_generation(root, generation_id)
    if journal.get("generation_fingerprint_sha256") != generation_fingerprint(root, generation_id):
        raise CheckpointError("Restore-Journal ist nicht an den aktuellen Checkpoint-Fingerprint gebunden.")
    entries = _restore_entries(root, generation_id)
    expected = {(item["target"], item["snapshot"]): item for item in entries}
    targets = journal.get("targets", [])
    if len(targets) != len(entries):
        raise CheckpointError("Restore-Journal und Checkpoint besitzen unterschiedliche Zielmengen.")
    count = 0
    for item in targets:
        if not isinstance(item, dict):
            raise CheckpointError("Restore-Journal enthält einen ungültigen Zielsatz.")
        key = (item.get("target"), item.get("snapshot"))
        source = expected.get(key)
        if source is None or item.get("exists") != source["exists"] or item.get("sha256") != source["sha256"]:
            raise CheckpointError("Restore-Journal wurde gegenüber dem verifizierten Checkpoint verändert.")
        target = Path(str(source["target"]))
        if source["exists"]:
            snapshot = _generations_dir(root) / generation_id / "snapshots" / str(source["snapshot"])
            payload = snapshot.read_bytes()
            if _sha256_bytes(payload) != source["sha256"]:
                raise CheckpointError("Snapshot wurde nach der Restore-Probe beschädigt.")
            atomic_write_bytes(target, payload)
        else:
            try:
                target.unlink(missing_ok=True)
                if target.parent.exists():
                    fsync_directory(target.parent)
            except (OSError, SafeIoError) as exc:
                raise CheckpointError(f"Restore konnte ein zuvor nicht vorhandenes Ziel nicht entfernen: {target}") from exc
        count += 1
        if _crash_after_writes is not None and count >= _crash_after_writes:
            raise RuntimeError(f"fault-injection: crash after restore write {count}")
    pending = _pending_restore_path(root)
    pending.unlink(missing_ok=True)
    fsync_directory(pending.parent)
    record = verify_checkpoint(root, generation_id)
    _append_audit(root, "CHECKPOINT_RESTORE_RECOVERED" if recovered else "CHECKPOINT_RESTORED", generation_id=generation_id, target_count=len(entries))
    return record

def recover_pending_checkpoint_restore(root: Path | str) -> CheckpointRecord | None:
    base = Path(root).expanduser().resolve()
    if not _pending_restore_path(base).exists():
        return None
    try:
        with exclusive_file_lock(_lock_path(base), timeout_seconds=10.0):
            if not _pending_restore_path(base).exists():
                return None
            journal = _load_restore_journal(base)
            return _apply_restore_locked(base, journal, recovered=True)
    except SafeIoError as exc:
        raise CheckpointError("Checkpoint-Restore-Recovery ist durch einen parallelen Vorgang blockiert.") from exc

def restore_checkpoint(
    root: Path | str,
    generation_id: str,
    *,
    require_probe: bool = True,
    _crash_after_writes: int | None = None,
) -> CheckpointRecord:
    base = Path(root).expanduser().resolve()
    from .checkpoint_trust_chain import require_trusted_generation
    require_trusted_generation(base, generation_id)
    try:
        with exclusive_file_lock(_lock_path(base), timeout_seconds=10.0):
            if _pending_restore_path(base).exists():
                _apply_restore_locked(base, _load_restore_journal(base), recovered=True)
            if require_probe:
                probe = probe_checkpoint_restore(base, generation_id)
                if not probe.ok:
                    raise CheckpointError("Restore-Probe fehlgeschlagen: " + "; ".join(probe.issues))
            entries = _restore_entries(base, generation_id)
            _write_restore_journal(base, generation_id, entries)
            if _crash_after_writes == 0:
                raise RuntimeError("fault-injection: crash after durable restore intent")
            return _apply_restore_locked(base, _load_restore_journal(base), recovered=False, _crash_after_writes=_crash_after_writes)
    except SafeIoError as exc:
        raise CheckpointError("Checkpoint-Restore ist durch einen parallelen Vorgang blockiert.") from exc

def checkpoint_at_or_before(root: Path | str, target_unix_ns: int) -> CheckpointRecord:
    candidates = [item for item in reconcile_generation_graph(root) if item.created_at_unix_ns <= int(target_unix_ns)]
    if not candidates:
        raise CheckpointError("Für den gewünschten Zeitpunkt existiert kein verifizierter Checkpoint.")
    return candidates[-1]

def restore_point_in_time(root: Path | str, target_unix_ns: int, *, require_probe: bool = True) -> CheckpointRecord:
    record = checkpoint_at_or_before(root, target_unix_ns)
    return restore_checkpoint(root, record.generation_id, require_probe=require_probe)

def garbage_collect_checkpoints(root: Path | str, *, keep: int = DEFAULT_CHECKPOINT_RETENTION) -> tuple[str, ...]:
    base = Path(root).expanduser().resolve()
    keep = max(1, int(keep))
    try:
        with exclusive_file_lock(_lock_path(base), timeout_seconds=10.0):
            if _pending_restore_path(base).exists():
                raise CheckpointError("Checkpoint-GC ist während eines offenen Restore-Journals gesperrt.")
            records = reconcile_generation_graph(base)
            doomed = records[:-keep]
            retained = records[-keep:]
            if doomed and retained:
                write_prune_anchor(base, [
                    {"generation_id": item.generation_id, "fingerprint_sha256": generation_fingerprint(base, item.generation_id)}
                    for item in doomed
                ], retained[0].generation_id)
            removed: list[str] = []
            for record in doomed:
                path = _generations_dir(base) / record.generation_id
                try:
                    shutil.rmtree(path)
                    removed.append(record.generation_id)
                except OSError as exc:
                    raise CheckpointError(f"Alte Checkpoint-Generation konnte nicht entfernt werden: {record.generation_id}") from exc
            if removed:
                fsync_directory(_generations_dir(base))
            reconcile_generation_graph(base)
            if removed:
                _append_audit(base, "CHECKPOINT_GC", removed=removed, keep=keep)
            return tuple(removed)
    except SafeIoError as exc:
        raise CheckpointError("Checkpoint-GC ist durch einen parallelen Vorgang blockiert.") from exc
