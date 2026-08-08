from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .checkpoint_store import (
    CheckpointError,
    CheckpointRecord,
    _append_audit,
    _audit_path,
    _generation_manifest,
    _generations_dir,
    _lock_path,
    _restore_entries,
    _scan_valid_generations,
    _sha256_bytes,
    generation_fingerprint,
    probe_checkpoint_restore,
    reconcile_generation_graph,
    restore_checkpoint,
    verify_checkpoint,
)
from .safe_io import SafeIoError, exclusive_file_lock, fsync_directory
from .checkpoint_trust_chain import inspect_trust_chain, require_trusted_generation


@dataclass(frozen=True, slots=True)
class RestoreFileDiff:
    domain: str
    target: str
    action: str
    current_exists: bool
    checkpoint_exists: bool
    current_sha256: str = ""
    checkpoint_sha256: str = ""
    current_size: int = 0
    checkpoint_size: int = 0


@dataclass(frozen=True, slots=True)
class RestoreDryRun:
    generation_id: str
    ok: bool
    fingerprint_sha256: str
    changed_count: int
    unchanged_count: int
    total_restore_bytes: int
    files: tuple[RestoreFileDiff, ...]
    issues: tuple[str, ...] = ()


def _generation_quarantine_dir(root: Path) -> Path:
    return root / ".videobatch-checkpoints" / "quarantine" / "generations"


def restore_dry_run(root: Path | str, generation_id: str) -> RestoreDryRun:
    base = Path(root).expanduser().resolve()
    probe = probe_checkpoint_restore(base, generation_id)
    if not probe.ok:
        return RestoreDryRun(generation_id, False, "", 0, 0, 0, (), probe.issues)
    try:
        entries = _restore_entries(base, generation_id)
        fingerprint = generation_fingerprint(base, generation_id)
    except CheckpointError as exc:
        return RestoreDryRun(generation_id, False, "", 0, 0, 0, (), (str(exc),))
    rows: list[RestoreFileDiff] = []
    changed = unchanged = restore_bytes = 0
    for item in entries:
        target = Path(str(item["target"]))
        checkpoint_exists = bool(item["exists"])
        current_exists = target.is_file()
        current_digest = ""
        current_size = 0
        if current_exists:
            try:
                current_payload = target.read_bytes()
            except OSError as exc:
                issue = f"Aktueller Zielzustand ist nicht lesbar: {target}: {exc}"
                return RestoreDryRun(generation_id, False, fingerprint, changed, unchanged, restore_bytes, tuple(rows), (issue,))
            current_digest = _sha256_bytes(current_payload)
            current_size = len(current_payload)
        checkpoint_digest = str(item.get("sha256") or "")
        checkpoint_size = int(item.get("size_bytes", 0) or 0)
        if current_exists == checkpoint_exists and (not checkpoint_exists or current_digest == checkpoint_digest):
            action = "unchanged"
            unchanged += 1
        elif checkpoint_exists and current_exists:
            action = "replace"
            changed += 1
            restore_bytes += checkpoint_size
        elif checkpoint_exists:
            action = "create"
            changed += 1
            restore_bytes += checkpoint_size
        else:
            action = "delete"
            changed += 1
        rows.append(RestoreFileDiff(
            domain=str(item.get("domain") or "unknown"), target=str(target), action=action,
            current_exists=current_exists, checkpoint_exists=checkpoint_exists,
            current_sha256=current_digest, checkpoint_sha256=checkpoint_digest,
            current_size=current_size, checkpoint_size=checkpoint_size,
        ))
    _append_audit(base, "CHECKPOINT_RESTORE_DRY_RUN", generation_id=generation_id, changed=changed, unchanged=unchanged, fingerprint_sha256=fingerprint)
    return RestoreDryRun(generation_id, True, fingerprint, changed, unchanged, restore_bytes, tuple(rows), ())


def select_best_recovery_checkpoint(root: Path | str, *, required_domains: Iterable[str] = ()) -> CheckpointRecord:
    base = Path(root).expanduser().resolve()
    required = {str(item).strip() for item in required_domains if str(item).strip()}
    trust = inspect_trust_chain(base)
    if trust.audit_status == "invalid":
        raise CheckpointError("Automatische Recovery-Punktwahl ist gesperrt: Die Forensik-Auditkette ist beschädigt.")
    trusted_ids = {item.generation_id for item in trust.generations if item.trust_level == "trusted"}
    candidates: list[tuple[tuple[int, int, int, str], CheckpointRecord]] = []
    for record in reconcile_generation_graph(base):
        if record.generation_id not in trusted_ids:
            continue
        try:
            manifest = _generation_manifest(base, record.generation_id)
            domains = {str(item.get("domain") or "") for item in manifest.get("files", []) if isinstance(item, dict)}
            generation_fingerprint(base, record.generation_id)
        except CheckpointError:
            continue
        coverage = len(required & domains) if required else len(domains)
        complete = 1 if not required or required <= domains else 0
        candidates.append(((complete, coverage, record.created_at_unix_ns, record.generation_id), record))
    if not candidates:
        raise CheckpointError("Kein authentifizierter und vollständig verketteter Recovery-Punkt ist verfügbar.")
    selected = sorted(candidates, key=lambda item: item[0])[-1][1]
    _append_audit(base, "CHECKPOINT_RECOVERY_POINT_SELECTED", generation_id=selected.generation_id, required_domains=sorted(required))
    return selected


def isolate_corrupt_generations(root: Path | str) -> tuple[str, ...]:
    base = Path(root).expanduser().resolve()
    try:
        with exclusive_file_lock(_lock_path(base), timeout_seconds=10.0):
            _valid, invalid = _scan_valid_generations(base)
            if not invalid:
                return ()
            quarantine = _generation_quarantine_dir(base)
            quarantine.mkdir(parents=True, exist_ok=True)
            isolated: list[str] = []
            for generation_id in invalid:
                source = _generations_dir(base) / generation_id
                if not source.exists():
                    continue
                try:
                    os.replace(source, quarantine / f"{generation_id}-{time.time_ns()}")
                except OSError as exc:
                    raise CheckpointError(f"Beschädigte Generation konnte nicht isoliert werden: {generation_id}") from exc
                isolated.append(generation_id)
            if isolated:
                fsync_directory(_generations_dir(base))
                fsync_directory(quarantine)
                reconcile_generation_graph(base)
                _append_audit(base, "CHECKPOINT_GENERATIONS_QUARANTINED", generations=isolated)
            return tuple(isolated)
    except SafeIoError as exc:
        raise CheckpointError("Checkpoint-Quarantäne ist durch einen parallelen Vorgang blockiert.") from exc


def checkpoint_forensics_timeline(root: Path | str, *, limit: int = 50) -> list[dict[str, Any]]:
    base = Path(root).expanduser().resolve()
    try:
        lines = _audit_path(base).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return []
    events: list[dict[str, Any]] = []
    for line in lines:
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and isinstance(value.get("event"), str):
            events.append(value)
    return events[-max(0, int(limit)):]


def safe_restore_checkpoint(
    root: Path | str,
    generation_id: str,
    *,
    required_domains: Iterable[str] = (),
    allow_lower_quality: bool = False,
    require_probe: bool = True,
) -> CheckpointRecord:
    base = Path(root).expanduser().resolve()
    require_trusted_generation(base, generation_id)
    dry = restore_dry_run(base, generation_id)
    if not dry.ok:
        raise CheckpointError("Restore-Dry-Run fehlgeschlagen: " + "; ".join(dry.issues))
    if not allow_lower_quality:
        best = select_best_recovery_checkpoint(base, required_domains=required_domains)
        target_manifest = _generation_manifest(base, generation_id)
        best_manifest = _generation_manifest(base, best.generation_id)
        target_domains = {str(item.get("domain") or "") for item in target_manifest.get("files", []) if isinstance(item, dict)}
        best_domains = {str(item.get("domain") or "") for item in best_manifest.get("files", []) if isinstance(item, dict)}
        required = {str(item).strip() for item in required_domains if str(item).strip()}
        target_complete = not required or required <= target_domains
        best_complete = not required or required <= best_domains
        target_record = verify_checkpoint(base, generation_id)
        lower_coverage = (best_complete and not target_complete) or (best_complete == target_complete and len(best_domains) > len(target_domains))
        older_equivalent = best_complete == target_complete and len(best_domains) == len(target_domains) and best.created_at_unix_ns > target_record.created_at_unix_ns
        if lower_coverage:
            raise CheckpointError("Restore wurde blockiert: Ein verifizierter Recovery-Punkt mit besserer Zustandsabdeckung ist verfügbar.")
        if older_equivalent:
            raise CheckpointError("Restore wurde blockiert: Ein neuerer gleichwertiger verifizierter Recovery-Punkt ist verfügbar. Für eine bewusste Point-in-Time-Rücksetzung muss der Schutz explizit aufgehoben werden.")
    return restore_checkpoint(base, generation_id, require_probe=require_probe)
