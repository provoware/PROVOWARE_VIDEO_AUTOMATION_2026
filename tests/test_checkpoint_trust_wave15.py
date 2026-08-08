from __future__ import annotations

import json
from pathlib import Path

import pytest

from videobatch_fast.checkpoint_store import CheckpointError, create_system_checkpoint, verify_checkpoint
from videobatch_fast.checkpoint_trust_chain import (
    inspect_trust_chain, migrate_legacy_checkpoints, rotate_checkpoint_trust_key,
    verify_audit_trust_chain,
)


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _manifest(root: Path, gid: str) -> Path:
    return root / ".videobatch-checkpoints" / "generations" / gid / "manifest.json"


def test_new_checkpoint_is_hmac_authenticated_and_trusted(tmp_path: Path):
    state = tmp_path / "project.json"
    _write(state, {"g": 1})
    record = create_system_checkpoint(tmp_path, {"project": state})
    manifest = json.loads(_manifest(tmp_path, record.generation_id).read_text())
    assert manifest["authentication"]["algorithm"] == "HMAC-SHA256"
    assert verify_checkpoint(tmp_path, record.generation_id).generation_id == record.generation_id
    report = inspect_trust_chain(tmp_path)
    assert report.status == "trusted"
    assert report.generations[0].trust_level == "trusted"


def test_manifest_replacement_or_edit_is_rejected_by_hmac(tmp_path: Path):
    state = tmp_path / "project.json"
    _write(state, {"g": 1})
    record = create_system_checkpoint(tmp_path, {"project": state})
    path = _manifest(tmp_path, record.generation_id)
    manifest = json.loads(path.read_text())
    manifest["created_at_unix_ns"] += 1
    # Recalculate the unkeyed fingerprint like an attacker could; HMAC must still fail.
    from videobatch_fast.checkpoint_store import _fingerprint_manifest
    manifest["fingerprint_sha256"] = _fingerprint_manifest(manifest)
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(CheckpointError, match="Authentifizierung"):
        verify_checkpoint(tmp_path, record.generation_id)
    assert inspect_trust_chain(tmp_path).status == "compromised"


def test_deleted_middle_generation_breaks_signed_parent_chain(tmp_path: Path):
    state = tmp_path / "project.json"
    _write(state, {"g": 1})
    first = create_system_checkpoint(tmp_path, {"project": state})
    _write(state, {"g": 2})
    middle = create_system_checkpoint(tmp_path, {"project": state})
    _write(state, {"g": 3})
    last = create_system_checkpoint(tmp_path, {"project": state})
    import shutil
    shutil.rmtree(_manifest(tmp_path, middle.generation_id).parent)
    report = inspect_trust_chain(tmp_path)
    assert report.status == "compromised"
    assert middle.generation_id in report.missing_generations
    assert last.generation_id in {row.generation_id for row in report.generations}
    assert first.generation_id in {row.generation_id for row in report.generations}


def test_inserted_unsigned_generation_is_detected(tmp_path: Path):
    state = tmp_path / "project.json"
    _write(state, {"g": 1})
    first = create_system_checkpoint(tmp_path, {"project": state})
    _write(state, {"g": 2})
    last = create_system_checkpoint(tmp_path, {"project": state})
    gen_root = tmp_path / ".videobatch-checkpoints" / "generations"
    fake = gen_root / f"{(first.created_at_unix_ns + last.created_at_unix_ns)//2}-fake"
    (fake / "snapshots").mkdir(parents=True)
    original = json.loads(_manifest(tmp_path, first.generation_id).read_text())
    original["generation_id"] = fake.name
    original["created_at_unix_ns"] = (first.created_at_unix_ns + last.created_at_unix_ns)//2
    original.pop("authentication", None)
    from videobatch_fast.checkpoint_store import _fingerprint_manifest
    original["fingerprint_sha256"] = _fingerprint_manifest(original)
    (fake / "manifest.json").write_text(json.dumps(original), encoding="utf-8")
    # Snapshot copy makes it structurally valid but unauthenticated.
    src_snap = _manifest(tmp_path, first.generation_id).parent / "snapshots"
    for src in src_snap.iterdir():
        (fake / "snapshots" / src.name).write_bytes(src.read_bytes())
    assert inspect_trust_chain(tmp_path).status == "compromised"


def test_key_rotation_keeps_old_generations_verifiable_and_uses_new_key(tmp_path: Path):
    state = tmp_path / "project.json"
    _write(state, {"g": 1})
    old = create_system_checkpoint(tmp_path, {"project": state})
    old_key = json.loads(_manifest(tmp_path, old.generation_id).read_text())["authentication"]["key_id"]
    new_key = rotate_checkpoint_trust_key(tmp_path)
    assert new_key != old_key
    _write(state, {"g": 2})
    new = create_system_checkpoint(tmp_path, {"project": state})
    assert json.loads(_manifest(tmp_path, new.generation_id).read_text())["authentication"]["key_id"] == new_key
    assert verify_checkpoint(tmp_path, old.generation_id).generation_id == old.generation_id
    assert inspect_trust_chain(tmp_path).status == "trusted"


def test_explicit_legacy_migration_builds_authenticated_chain(tmp_path: Path):
    state = tmp_path / "project.json"
    _write(state, {"g": 1})
    first = create_system_checkpoint(tmp_path, {"project": state})
    _write(state, {"g": 2})
    second = create_system_checkpoint(tmp_path, {"project": state})
    for gid in (first.generation_id, second.generation_id):
        path = _manifest(tmp_path, gid)
        manifest = json.loads(path.read_text())
        manifest.pop("authentication", None)
        manifest.pop("parent_generation_id", None)
        manifest.pop("parent_fingerprint_sha256", None)
        from videobatch_fast.checkpoint_store import _fingerprint_manifest
        manifest["fingerprint_sha256"] = _fingerprint_manifest(manifest)
        path.write_text(json.dumps(manifest), encoding="utf-8")
    assert inspect_trust_chain(tmp_path).status == "legacy"
    assert migrate_legacy_checkpoints(tmp_path) == (first.generation_id, second.generation_id)
    assert inspect_trust_chain(tmp_path).status == "trusted"


def test_audit_tampering_breaks_authenticated_audit_chain(tmp_path: Path):
    state = tmp_path / "project.json"
    _write(state, {"g": 1})
    create_system_checkpoint(tmp_path, {"project": state})
    _write(state, {"g": 2})
    create_system_checkpoint(tmp_path, {"project": state})
    assert verify_audit_trust_chain(tmp_path)[0] == "authenticated"
    audit = tmp_path / ".videobatch-checkpoints" / "audit.jsonl"
    lines = audit.read_text().splitlines()
    row = json.loads(lines[0])
    row["event"] = "TAMPERED"
    lines[0] = json.dumps(row)
    audit.write_text("\n".join(lines) + "\n")
    status, issues = verify_audit_trust_chain(tmp_path)
    assert status == "invalid"
    assert issues


def test_partial_checkpoint_directory_compromise_is_reported_not_silently_trusted(tmp_path: Path):
    state = tmp_path / "project.json"
    _write(state, {"g": 1})
    good = create_system_checkpoint(tmp_path, {"project": state})
    _write(state, {"g": 2})
    bad = create_system_checkpoint(tmp_path, {"project": state})
    path = _manifest(tmp_path, bad.generation_id)
    manifest = json.loads(path.read_text())
    snap = path.parent / "snapshots" / manifest["files"][0]["snapshot"]
    snap.write_bytes(b"compromised")
    report = inspect_trust_chain(tmp_path)
    assert report.status == "compromised"
    assert any(bad.generation_id in issue or "beschädigt" in issue for issue in report.issues)
    assert verify_checkpoint(tmp_path, good.generation_id).generation_id == good.generation_id


def test_authenticated_gc_prune_anchor_preserves_trust_chain(tmp_path: Path):
    from videobatch_fast.checkpoint_store import garbage_collect_checkpoints
    state = tmp_path / "project.json"
    records = []
    for value in range(4):
        _write(state, {"g": value})
        records.append(create_system_checkpoint(tmp_path, {"project": state}))
    removed = garbage_collect_checkpoints(tmp_path, keep=2)
    assert removed == (records[0].generation_id, records[1].generation_id)
    report = inspect_trust_chain(tmp_path)
    assert report.status == "trusted"
    assert not report.missing_generations


def test_forged_or_missing_prune_anchor_does_not_hide_deleted_prefix(tmp_path: Path):
    import shutil
    state = tmp_path / "project.json"
    _write(state, {"g": 1})
    first = create_system_checkpoint(tmp_path, {"project": state})
    _write(state, {"g": 2})
    create_system_checkpoint(tmp_path, {"project": state})
    shutil.rmtree(_manifest(tmp_path, first.generation_id).parent)
    anchor = tmp_path / ".videobatch-checkpoints" / "trust-prune-anchor.json"
    anchor.write_text(json.dumps({"schema_version": 1, "removed": [{"generation_id": first.generation_id, "fingerprint_sha256": "0" * 64}], "first_retained_generation_id": "x", "authentication": {}}))
    assert inspect_trust_chain(tmp_path).status == "compromised"
