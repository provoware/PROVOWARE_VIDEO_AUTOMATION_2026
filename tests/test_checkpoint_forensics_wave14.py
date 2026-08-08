from __future__ import annotations

import json
from pathlib import Path

import pytest

from videobatch_fast.checkpoint_store import (
    CheckpointError, create_system_checkpoint, generation_fingerprint, inspect_checkpoint_state,
    list_checkpoints, verify_checkpoint,
)
from videobatch_fast.checkpoint_forensics import (
    checkpoint_forensics_timeline, isolate_corrupt_generations, restore_dry_run,
    safe_restore_checkpoint, select_best_recovery_checkpoint,
)


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _manifest(root: Path, generation_id: str) -> Path:
    return root / ".videobatch-checkpoints" / "generations" / generation_id / "manifest.json"


def test_generation_fingerprint_binds_manifest_semantics(tmp_path: Path):
    state = tmp_path / "project.json"
    _write(state, {"g": 1})
    record = create_system_checkpoint(tmp_path, {"project": state})
    manifest_path = _manifest(tmp_path, record.generation_id)
    payload = json.loads(manifest_path.read_text())
    assert payload["fingerprint_sha256"] == generation_fingerprint(tmp_path, record.generation_id)
    payload["files"][0]["domain"] = "config"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(CheckpointError, match="fingerprint"):
        verify_checkpoint(tmp_path, record.generation_id)


def test_restore_dry_run_reports_detailed_create_replace_delete_and_unchanged(tmp_path: Path):
    unchanged = tmp_path / "same.json"
    replace = tmp_path / "replace.json"
    create = tmp_path / "create.json"
    delete = tmp_path / "delete.json"
    _write(unchanged, {"v": 1})
    _write(replace, {"v": 1})
    _write(create, {"v": 1})
    record = create_system_checkpoint(tmp_path, [
        ("project", unchanged), ("config", replace), ("queue", create), ("job-journal", delete)
    ])
    _write(replace, {"v": 2})
    create.unlink()
    _write(delete, {"v": 1})
    # For a checkpoint where target existed, absence means create. To test delete, make a new checkpoint with an absent target.
    absent = tmp_path / "absent.json"
    second = create_system_checkpoint(tmp_path, [("project", unchanged), ("config", replace), ("queue", absent)])
    _write(absent, {"new": True})
    dry2 = restore_dry_run(tmp_path, second.generation_id)
    assert dry2.ok
    assert {row.action for row in dry2.files} >= {"unchanged", "delete"}

    dry = restore_dry_run(tmp_path, record.generation_id)
    actions = {row.target: row.action for row in dry.files}
    assert dry.ok is True
    assert actions[str(unchanged.resolve())] == "unchanged"
    assert actions[str(replace.resolve())] == "replace"
    assert actions[str(create.resolve())] == "create"
    assert dry.changed_count == 3
    assert dry.unchanged_count == 1
    assert actions[str(delete.resolve())] == "delete"
    assert len(dry.fingerprint_sha256) == 64


def test_best_recovery_point_prefers_complete_domain_coverage_over_newer_partial_generation(tmp_path: Path):
    project = tmp_path / "project.json"
    config = tmp_path / "config.json"
    _write(project, {"g": 1})
    _write(config, {"g": 1})
    complete = create_system_checkpoint(tmp_path, [("project", project), ("config", config)])
    _write(project, {"g": 2})
    partial = create_system_checkpoint(tmp_path, [("project", project)])
    assert partial.created_at_unix_ns >= complete.created_at_unix_ns
    selected = select_best_recovery_checkpoint(tmp_path, required_domains=("project", "config"))
    assert selected.generation_id == complete.generation_id


def test_corrupt_generation_is_isolated_not_deleted(tmp_path: Path):
    state = tmp_path / "project.json"
    _write(state, {"g": 1})
    record = create_system_checkpoint(tmp_path, {"project": state})
    manifest = json.loads(_manifest(tmp_path, record.generation_id).read_text())
    snapshot = _manifest(tmp_path, record.generation_id).parent / "snapshots" / manifest["files"][0]["snapshot"]
    snapshot.write_bytes(b"corrupt")
    assert record.generation_id in inspect_checkpoint_state(tmp_path).invalid_generations
    assert isolate_corrupt_generations(tmp_path) == (record.generation_id,)
    assert record.generation_id not in inspect_checkpoint_state(tmp_path).invalid_generations
    quarantine = tmp_path / ".videobatch-checkpoints" / "quarantine" / "generations"
    assert any(path.name.startswith(record.generation_id) for path in quarantine.iterdir())


def test_forensics_timeline_survives_malformed_audit_line(tmp_path: Path):
    state = tmp_path / "project.json"
    _write(state, {"g": 1})
    record = create_system_checkpoint(tmp_path, {"project": state})
    restore_dry_run(tmp_path, record.generation_id)
    audit = tmp_path / ".videobatch-checkpoints" / "audit.jsonl"
    with audit.open("a", encoding="utf-8") as handle:
        handle.write("{broken\n")
    rows = checkpoint_forensics_timeline(tmp_path, limit=10)
    assert any(row["event"] == "CHECKPOINT_CREATED" for row in rows)
    assert any(row["event"] == "CHECKPOINT_RESTORE_DRY_RUN" for row in rows)


def test_safe_restore_blocks_lower_coverage_generation(tmp_path: Path):
    project = tmp_path / "project.json"
    config = tmp_path / "config.json"
    _write(project, {"g": 1})
    partial = create_system_checkpoint(tmp_path, [("project", project)])
    _write(config, {"c": 1})
    complete = create_system_checkpoint(tmp_path, [("project", project), ("config", config)])
    _write(project, {"g": 9})
    with pytest.raises(CheckpointError, match="besserer Zustandsabdeckung"):
        safe_restore_checkpoint(tmp_path, partial.generation_id, required_domains=("project", "config"))
    safe_restore_checkpoint(tmp_path, complete.generation_id, required_domains=("project", "config"))
    assert json.loads(project.read_text()) == {"g": 1}



def test_safe_restore_blocks_older_equivalent_generation_without_explicit_override(tmp_path: Path):
    project = tmp_path / "project.json"
    _write(project, {"g": 1})
    old = create_system_checkpoint(tmp_path, [("project", project)])
    _write(project, {"g": 2})
    newest = create_system_checkpoint(tmp_path, [("project", project)])
    with pytest.raises(CheckpointError, match="neuerer gleichwertiger"):
        safe_restore_checkpoint(tmp_path, old.generation_id, required_domains=("project",))
    safe_restore_checkpoint(tmp_path, old.generation_id, required_domains=("project",), allow_lower_quality=True)
    assert json.loads(project.read_text()) == {"g": 1}
    assert newest.created_at_unix_ns > old.created_at_unix_ns


def test_end_to_end_checkpoint_corruption_diagnose_select_probe_restore_recheckpoint(tmp_path: Path):
    project, config = tmp_path / "project.json", tmp_path / "config.json"
    _write(project, {"g": 1})
    _write(config, {"c": 1})
    good = create_system_checkpoint(tmp_path, [("project", project), ("config", config)])
    _write(project, {"g": 2})
    bad = create_system_checkpoint(tmp_path, [("project", project), ("config", config)])
    manifest = json.loads(_manifest(tmp_path, bad.generation_id).read_text())
    snapshot = _manifest(tmp_path, bad.generation_id).parent / "snapshots" / manifest["files"][0]["snapshot"]
    snapshot.write_bytes(b"broken")

    health = inspect_checkpoint_state(tmp_path)
    assert bad.generation_id in health.invalid_generations
    isolate_corrupt_generations(tmp_path)
    selected = select_best_recovery_checkpoint(tmp_path, required_domains=("project", "config"))
    assert selected.generation_id == good.generation_id
    dry = restore_dry_run(tmp_path, selected.generation_id)
    assert dry.ok
    safe_restore_checkpoint(tmp_path, selected.generation_id, required_domains=("project", "config"))
    assert json.loads(project.read_text()) == {"g": 1}
    healed = create_system_checkpoint(tmp_path, [("project", project), ("config", config)])
    assert verify_checkpoint(tmp_path, healed.generation_id).generation_id == healed.generation_id
    assert len(list_checkpoints(tmp_path)) == 2
