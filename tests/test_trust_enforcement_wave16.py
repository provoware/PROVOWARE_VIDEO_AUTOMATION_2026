from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from videobatch_fast.checkpoint_forensics import safe_restore_checkpoint, select_best_recovery_checkpoint
from videobatch_fast.checkpoint_store import (
    CheckpointError,
    _fingerprint_manifest,
    create_system_checkpoint,
    generation_fingerprint,
    recover_pending_checkpoint_restore,
    restore_checkpoint,
)
from videobatch_fast.checkpoint_trust_chain import inspect_trust_chain, migrate_legacy_checkpoints


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _manifest(root: Path, generation_id: str) -> Path:
    return root / ".videobatch-checkpoints" / "generations" / generation_id / "manifest.json"


def _insert_unsigned_generation(root: Path, source_generation_id: str, *, created_at: int) -> str:
    generations = root / ".videobatch-checkpoints" / "generations"
    fake_id = f"{created_at}-inserted"
    source = generations / source_generation_id
    fake = generations / fake_id
    shutil.copytree(source, fake)
    path = fake / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["generation_id"] = fake_id
    manifest["created_at_unix_ns"] = created_at
    manifest["parent_generation_id"] = source_generation_id
    manifest["parent_fingerprint_sha256"] = generation_fingerprint(root, source_generation_id)
    manifest.pop("authentication", None)
    manifest["fingerprint_sha256"] = _fingerprint_manifest(manifest)
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return fake_id


def test_automatic_selection_ignores_newer_unsigned_inserted_generation(tmp_path: Path) -> None:
    state = tmp_path / "project.json"
    _write(state, {"g": 1})
    trusted = create_system_checkpoint(tmp_path, {"project": state})
    fake = _insert_unsigned_generation(tmp_path, trusted.generation_id, created_at=10**19)

    report = inspect_trust_chain(tmp_path)
    assert report.status == "compromised"
    assert next(item for item in report.generations if item.generation_id == fake).trust_level == "untrusted"
    assert select_best_recovery_checkpoint(tmp_path).generation_id == trusted.generation_id


def test_safe_restore_rejects_unsigned_inserted_generation(tmp_path: Path) -> None:
    state = tmp_path / "project.json"
    _write(state, {"g": 1})
    trusted = create_system_checkpoint(tmp_path, {"project": state})
    fake = _insert_unsigned_generation(tmp_path, trusted.generation_id, created_at=10**19)
    _write(state, {"g": 9})

    with pytest.raises(CheckpointError, match="nicht vertrauenswürdig"):
        safe_restore_checkpoint(tmp_path, fake)
    assert json.loads(state.read_text(encoding="utf-8")) == {"g": 9}


def test_trust_does_not_resume_after_untrusted_parent(tmp_path: Path) -> None:
    state = tmp_path / "project.json"
    _write(state, {"g": 1})
    first = create_system_checkpoint(tmp_path, {"project": state})
    fake = _insert_unsigned_generation(tmp_path, first.generation_id, created_at=first.created_at_unix_ns + 1)
    _write(state, {"g": 2})
    child = create_system_checkpoint(tmp_path, {"project": state})

    report = inspect_trust_chain(tmp_path)
    rows = {item.generation_id: item for item in report.generations}
    assert rows[fake].trust_level == "untrusted"
    assert rows[child.generation_id].trust_level == "authenticated-unlinked"
    assert any("Parent-Generation" in issue for issue in rows[child.generation_id].issues)
    assert select_best_recovery_checkpoint(tmp_path).generation_id == first.generation_id


def test_legacy_generation_requires_explicit_migration_before_restore(tmp_path: Path) -> None:
    state = tmp_path / "project.json"
    _write(state, {"g": 1})
    record = create_system_checkpoint(tmp_path, {"project": state})
    path = _manifest(tmp_path, record.generation_id)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest.pop("authentication", None)
    manifest.pop("parent_generation_id", None)
    manifest.pop("parent_fingerprint_sha256", None)
    manifest["fingerprint_sha256"] = _fingerprint_manifest(manifest)
    path.write_text(json.dumps(manifest), encoding="utf-8")
    _write(state, {"g": 2})

    with pytest.raises(CheckpointError, match="nicht vertrauenswürdig"):
        restore_checkpoint(tmp_path, record.generation_id)
    assert not (tmp_path / ".videobatch-checkpoints" / "pending-restore.json").exists()

    assert migrate_legacy_checkpoints(tmp_path) == (record.generation_id,)
    restore_checkpoint(tmp_path, record.generation_id)
    assert json.loads(state.read_text(encoding="utf-8")) == {"g": 1}


def test_pending_restore_journal_is_authenticated_and_tampering_fails_closed(tmp_path: Path) -> None:
    state = tmp_path / "project.json"
    _write(state, {"g": 1})
    record = create_system_checkpoint(tmp_path, {"project": state})
    _write(state, {"g": 2})

    with pytest.raises(RuntimeError, match="durable restore intent"):
        restore_checkpoint(tmp_path, record.generation_id, _crash_after_writes=0)
    pending = tmp_path / ".videobatch-checkpoints" / "pending-restore.json"
    journal = json.loads(pending.read_text(encoding="utf-8"))
    assert journal["schema_version"] == 2
    assert journal["authorization_policy"] == "trusted-generation-required"
    assert journal["authentication"]["algorithm"] == "HMAC-SHA256"
    journal["prepared_at_unix_ns"] += 1
    pending.write_text(json.dumps(journal), encoding="utf-8")

    with pytest.raises(CheckpointError, match="nicht authentifiziert|verändert"):
        recover_pending_checkpoint_restore(tmp_path)
    assert json.loads(state.read_text(encoding="utf-8")) == {"g": 2}


def test_restore_journal_is_bound_to_exact_generation_fingerprint(tmp_path: Path) -> None:
    state = tmp_path / "project.json"
    _write(state, {"g": 1})
    record = create_system_checkpoint(tmp_path, {"project": state})
    _write(state, {"g": 2})
    with pytest.raises(RuntimeError):
        restore_checkpoint(tmp_path, record.generation_id, _crash_after_writes=0)

    pending = tmp_path / ".videobatch-checkpoints" / "pending-restore.json"
    journal = json.loads(pending.read_text(encoding="utf-8"))
    journal["generation_fingerprint_sha256"] = "0" * 64
    # Deliberately keep the old HMAC: binding changes must invalidate authorization.
    pending.write_text(json.dumps(journal), encoding="utf-8")
    with pytest.raises(CheckpointError, match="nicht authentifiziert|verändert"):
        recover_pending_checkpoint_restore(tmp_path)


def test_legacy_migration_never_reblesses_invalid_authenticated_generation(tmp_path: Path) -> None:
    state = tmp_path / "project.json"
    _write(state, {"g": 1})
    record = create_system_checkpoint(tmp_path, {"project": state})
    path = _manifest(tmp_path, record.generation_id)
    before = json.loads(path.read_text(encoding="utf-8"))
    tampered = dict(before)
    tampered["created_at_unix_ns"] += 123
    tampered["fingerprint_sha256"] = _fingerprint_manifest(tampered)
    path.write_text(json.dumps(tampered), encoding="utf-8")

    with pytest.raises(CheckpointError, match="Authentifizierung"):
        migrate_legacy_checkpoints(tmp_path)
    after = json.loads(path.read_text(encoding="utf-8"))
    assert after["authentication"] == before["authentication"]


def test_audit_tampering_blocks_safe_restore_even_for_authenticated_generation(tmp_path: Path) -> None:
    state = tmp_path / "project.json"
    _write(state, {"g": 1})
    record = create_system_checkpoint(tmp_path, {"project": state})
    audit = tmp_path / ".videobatch-checkpoints" / "audit.jsonl"
    rows = audit.read_text(encoding="utf-8").splitlines()
    first = json.loads(rows[0])
    first["event"] = "TAMPERED"
    rows[0] = json.dumps(first)
    audit.write_text("\n".join(rows) + "\n", encoding="utf-8")

    with pytest.raises(CheckpointError, match="Auditkette"):
        safe_restore_checkpoint(tmp_path, record.generation_id)
