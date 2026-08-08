from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .checkpoint_store import CheckpointError, generation_fingerprint, verify_checkpoint
from .checkpoint_trust import CheckpointTrustError, rotate_key, sign_payload, verify_payload, verify_prune_anchor
from .safe_io import atomic_write_json

@dataclass(frozen=True, slots=True)
class GenerationTrust:
    generation_id: str
    trust_level: str
    authenticated: bool
    chain_valid: bool
    key_id: str = ""
    issues: tuple[str, ...] = ()

@dataclass(frozen=True, slots=True)
class TrustChainReport:
    status: str
    generations: tuple[GenerationTrust, ...]
    missing_generations: tuple[str, ...]
    audit_status: str
    issues: tuple[str, ...] = ()

    @property
    def healthy(self) -> bool:
        return self.status == "trusted"

def _control(root: Path) -> Path:
    return root / ".videobatch-checkpoints"

def _generations(root: Path) -> Path:
    return _control(root) / "generations"

def _manifest_path(root: Path, generation_id: str) -> Path:
    return _generations(root) / generation_id / "manifest.json"

def _read_manifest(root: Path, generation_id: str) -> dict[str, Any]:
    try:
        value = json.loads(_manifest_path(root, generation_id).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CheckpointError(f"Checkpoint-Manifest ist nicht lesbar: {generation_id}") from exc
    if not isinstance(value, dict):
        raise CheckpointError(f"Checkpoint-Manifest ist ungültig: {generation_id}")
    return value

def _manifest_authenticated(root: Path, manifest: dict[str, Any]) -> tuple[bool, str]:
    auth = manifest.get("authentication")
    if not isinstance(auth, dict) or not auth:
        return False, ""
    unsigned = {key: value for key, value in manifest.items() if key != "authentication"}
    return verify_payload(root, unsigned, auth), str(auth.get("key_id") or "")

def verify_audit_trust_chain(root: Path | str) -> tuple[str, tuple[str, ...]]:
    base = Path(root).expanduser().resolve()
    path = _control(base) / "audit.jsonl"
    if not path.exists():
        return "empty", ()
    issues: list[str] = []
    previous = ""
    authenticated_rows = 0
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        return "invalid", (f"Audit-Timeline nicht lesbar: {exc}",)
    import hashlib
    for index, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            issues.append(f"Audit-Zeile {index} ist kein gültiges JSON.")
            continue
        if not isinstance(row, dict) or int(row.get("schema_version", 1) or 1) < 2:
            continue
        declared_prev = row.get("previous_hash_sha256")
        declared_hash = row.get("entry_hash_sha256")
        auth = row.get("authentication")
        unsigned_hash = {k: v for k, v in row.items() if k not in {"entry_hash_sha256", "authentication"}}
        calculated = hashlib.sha256((json.dumps(unsigned_hash, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()).hexdigest()
        if declared_prev != previous:
            issues.append(f"Audit-Kette ist bei Zeile {index} unterbrochen.")
        if declared_hash != calculated:
            issues.append(f"Audit-Hash ist bei Zeile {index} ungültig.")
        signed = {k: v for k, v in row.items() if k != "authentication"}
        if not isinstance(auth, dict) or not verify_payload(base, signed, auth):
            issues.append(f"Audit-HMAC ist bei Zeile {index} ungültig.")
        else:
            authenticated_rows += 1
        previous = str(declared_hash or "")
    if issues:
        return "invalid", tuple(issues)
    return ("authenticated" if authenticated_rows else "legacy"), ()


def _evaluate_generation_trust(
    root: Path, gid: str, manifest: dict[str, Any], manifests: dict[str, dict[str, Any]],
    previous_expected: str, previous_fp: str, previous_trusted: bool, is_first: bool,
    authorized_pruned_parent: tuple[str, str] | None = None,
) -> tuple[GenerationTrust, str, str, str | None]:
    authenticated, key_id = _manifest_authenticated(root, manifest)
    parent = str(manifest.get("parent_generation_id") or "")
    parent_fp = str(manifest.get("parent_fingerprint_sha256") or "")
    row_issues: list[str] = []
    chain_valid = True
    missing: str | None = None
    chained = "parent_generation_id" in manifest and "parent_fingerprint_sha256" in manifest
    if chained:
        pruned_ok = bool(is_first and authorized_pruned_parent and (parent, parent_fp) == authorized_pruned_parent)
        if parent and parent not in manifests and not pruned_ok:
            missing = parent
            row_issues.append(f"Vorgängergeneration fehlt: {parent}")
            chain_valid = False
        if parent != previous_expected and not pruned_ok:
            row_issues.append("Generationsreihenfolge stimmt nicht mit der signierten Parent-Kette überein.")
            chain_valid = False
        if parent_fp != previous_fp and not pruned_ok:
            row_issues.append("Parent-Fingerprint stimmt nicht mit der vorherigen Generation überein.")
            chain_valid = False
        if not is_first and not pruned_ok and not previous_trusted:
            row_issues.append("Parent-Generation ist nicht vertrauenswürdig; Trust darf nicht über die Lücke fortgesetzt werden.")
            chain_valid = False
    elif not is_first:
        chain_valid = False
        row_issues.append("Legacy-Generation besitzt keine signierte Parent-Verkettung.")
    if authenticated and chain_valid and chained:
        level = "trusted"
    elif authenticated:
        level = "authenticated-unlinked"
    elif not chained:
        level = "legacy-unverified"
    else:
        level = "untrusted"
    try:
        current_fp = generation_fingerprint(root, gid)
    except CheckpointError:
        current_fp = ""
    return GenerationTrust(gid, level, authenticated, chain_valid, key_id, tuple(row_issues)), gid, current_fp, missing

def inspect_trust_chain(root: Path | str) -> TrustChainReport:
    base = Path(root).expanduser().resolve()
    generation_dir = _generations(base)
    if not generation_dir.exists():
        audit_status, audit_issues = verify_audit_trust_chain(base)
        return TrustChainReport("empty", (), (), audit_status, audit_issues)
    manifests: dict[str, dict[str, Any]] = {}
    records: list[tuple[int, str]] = []
    issues: list[str] = []
    for path in generation_dir.iterdir():
        if not path.is_dir() or path.name.startswith(".creating-"):
            continue
        try:
            verify_checkpoint(base, path.name)
            manifest = _read_manifest(base, path.name)
            manifests[path.name] = manifest
            records.append((int(manifest.get("created_at_unix_ns", 0) or 0), path.name))
        except CheckpointError as exc:
            issues.append(str(exc))
    records.sort()
    trust_rows: list[GenerationTrust] = []
    missing: set[str] = set()
    previous_expected = ""
    previous_fp = ""
    previous_trusted = True
    prune = verify_prune_anchor(base)
    authorized_pruned_parent: tuple[str, str] | None = None
    if prune and records and prune.get("first_retained_generation_id") == records[0][1]:
        removed = prune.get("removed")
        if isinstance(removed, list) and removed and isinstance(removed[-1], dict):
            authorized_pruned_parent = (str(removed[-1].get("generation_id") or ""), str(removed[-1].get("fingerprint_sha256") or ""))
    for index, (_created, gid) in enumerate(records):
        row, previous_expected, previous_fp, missing_parent = _evaluate_generation_trust(
            base, gid, manifests[gid], manifests, previous_expected, previous_fp, previous_trusted,
            index == 0, authorized_pruned_parent,
        )
        trust_rows.append(row)
        previous_trusted = row.trust_level == "trusted"
        if missing_parent:
            missing.add(missing_parent)
    audit_status, audit_issues = verify_audit_trust_chain(base)
    issues.extend(audit_issues)
    if issues or any(row.trust_level in {"untrusted", "authenticated-unlinked"} for row in trust_rows) or missing or audit_status == "invalid":
        status = "compromised"
    elif trust_rows and all(row.trust_level == "trusted" for row in trust_rows) and audit_status in {"authenticated", "empty"}:
        status = "trusted"
    elif trust_rows:
        status = "legacy"
    else:
        status = "empty"
    return TrustChainReport(status, tuple(trust_rows), tuple(sorted(missing)), audit_status, tuple(issues))

def migrate_legacy_checkpoints(root: Path | str) -> tuple[str, ...]:
    """Explicitly rebuild and authenticate the full generation chain, including legacy generations."""
    base = Path(root).expanduser().resolve()
    generation_dir = _generations(base)
    if not generation_dir.exists():
        return ()
    ordered: list[tuple[int, str]] = []
    for path in generation_dir.iterdir():
        if not path.is_dir() or path.name.startswith(".creating-"):
            continue
        manifest = _read_manifest(base, path.name)
        ordered.append((int(manifest.get("created_at_unix_ns", 0) or 0), path.name))
    ordered.sort()
    # Preflight the complete set before rewriting a single manifest.  This is
    # essential: migration must never turn an already authenticated but
    # tampered generation into a newly trusted generation merely because the
    # local signing key is available.
    for _created, gid in ordered:
        verify_checkpoint(base, gid)
    changed: list[str] = []
    parent = ""
    parent_fp = ""
    from .checkpoint_store import _fingerprint_manifest
    for _created, gid in ordered:
        manifest = _read_manifest(base, gid)
        needs_change = (
            manifest.get("parent_generation_id") != parent
            or manifest.get("parent_fingerprint_sha256") != parent_fp
            or not isinstance(manifest.get("authentication"), dict)
            or not manifest.get("authentication")
        )
        manifest["parent_generation_id"] = parent
        manifest["parent_fingerprint_sha256"] = parent_fp
        manifest["fingerprint_version"] = 2
        manifest.pop("authentication", None)
        manifest["fingerprint_sha256"] = _fingerprint_manifest(manifest)
        manifest["authentication"] = sign_payload(base, manifest)
        if needs_change:
            atomic_write_json(_manifest_path(base, gid), manifest)
            changed.append(gid)
        parent = gid
        parent_fp = str(manifest["fingerprint_sha256"])
    return tuple(changed)


def rotate_checkpoint_trust_key(root: Path | str) -> str:
    return rotate_key(root)


def require_trusted_generation(
    root: Path | str,
    generation_id: str,
    *,
    allow_legacy: bool = False,
    require_audit_integrity: bool = True,
) -> GenerationTrust:
    """Fail closed unless a recovery generation has an acceptable trust state.

    Individual SHA-256 integrity is not sufficient for autonomous recovery:
    inserted legacy generations and broken parent chains must not become
    automatic restore targets.  Explicit legacy migration remains the supported
    path for pre-authentication checkpoints.
    """
    report = inspect_trust_chain(root)
    row = next((item for item in report.generations if item.generation_id == generation_id), None)
    if row is None:
        raise CheckpointError(f"Recovery-Punkt ist nicht in der verifizierten Trust-Chain enthalten: {generation_id}")
    accepted = row.trust_level == "trusted" or (allow_legacy and row.trust_level == "legacy-unverified")
    if not accepted:
        detail = "; ".join(row.issues) if row.issues else row.trust_level
        raise CheckpointError(f"Recovery-Punkt ist nicht vertrauenswürdig: {generation_id}: {detail}")
    if require_audit_integrity and report.audit_status == "invalid":
        raise CheckpointError("Recovery wurde blockiert: Die authentifizierte Forensik-Auditkette ist beschädigt.")
    return row
