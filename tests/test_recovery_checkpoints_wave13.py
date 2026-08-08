from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from videobatch_fast.checkpoint_store import (
    CheckpointError,
    checkpoint_at_or_before,
    cleanup_incomplete_checkpoint_creations,
    collect_recovery_sources,
    create_system_checkpoint,
    garbage_collect_checkpoints,
    inspect_checkpoint_state,
    list_checkpoints,
    probe_checkpoint_restore,
    reconcile_generation_graph,
    recover_pending_checkpoint_restore,
    restore_checkpoint,
    restore_point_in_time,
    verify_checkpoint,
)


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def test_checkpoint_captures_multiple_state_domains_and_restores_them(tmp_path: Path):
    project = tmp_path / "project.json"
    config = tmp_path / "config.json"
    queue = tmp_path / "jobs" / "retry_queue.json"
    history = tmp_path / "backups" / "history.json"
    meta = tmp_path / "backups" / "history.meta.json"
    for path, value in ((project, {"g": 1}), (config, {"ui": 1}), (queue, []), (history, []), (meta, {"schema_version": 1})):
        _write(path, value)
    sources = collect_recovery_sources(project_path=project, config_path=config, jobs_root=queue.parent, backup_dir=history.parent)
    record = create_system_checkpoint(tmp_path, sources)
    assert record.file_count == 5
    _write(project, {"g": 2})
    _write(config, {"ui": 2})
    restore_checkpoint(tmp_path, record.generation_id)
    assert json.loads(project.read_text()) == {"g": 1}
    assert json.loads(config.read_text()) == {"ui": 1}
    assert probe_checkpoint_restore(tmp_path, record.generation_id).ok is True


def test_generation_graph_forms_ordered_parent_chain(tmp_path: Path):
    state = tmp_path / "state.json"
    ids = []
    for generation in range(3):
        _write(state, {"g": generation})
        ids.append(create_system_checkpoint(tmp_path, {"project": state}).generation_id)
        time.sleep(0.001)
    records = reconcile_generation_graph(tmp_path)
    assert [item.generation_id for item in records] == ids
    assert records[0].parent_generation_id == ""
    assert records[1].parent_generation_id == ids[0]
    assert records[2].parent_generation_id == ids[1]


def test_crash_before_publish_leaves_no_visible_generation(tmp_path: Path):
    state = tmp_path / "state.json"
    _write(state, {"g": 1})
    with pytest.raises(RuntimeError):
        create_system_checkpoint(tmp_path, {"project": state}, _crash_stage="after_manifest")
    assert list_checkpoints(tmp_path) == []
    health = inspect_checkpoint_state(tmp_path)
    assert health.creating_residue
    assert cleanup_incomplete_checkpoint_creations(tmp_path)
    assert inspect_checkpoint_state(tmp_path).healthy


def test_crash_after_publish_is_reconciled_into_graph(tmp_path: Path):
    state = tmp_path / "state.json"
    _write(state, {"g": 1})
    with pytest.raises(RuntimeError):
        create_system_checkpoint(tmp_path, {"project": state}, _crash_stage="after_publish")
    records = reconcile_generation_graph(tmp_path)
    assert len(records) == 1
    assert verify_checkpoint(tmp_path, records[0].generation_id).generation_id == records[0].generation_id


def test_checkpoint_integrity_detects_snapshot_corruption(tmp_path: Path):
    state = tmp_path / "state.json"
    _write(state, {"g": 1})
    record = create_system_checkpoint(tmp_path, {"project": state})
    manifest_path = tmp_path / ".videobatch-checkpoints" / "generations" / record.generation_id / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    snapshot = manifest_path.parent / "snapshots" / manifest["files"][0]["snapshot"]
    snapshot.write_bytes(b"corrupt")
    with pytest.raises(CheckpointError):
        verify_checkpoint(tmp_path, record.generation_id)
    assert record.generation_id in inspect_checkpoint_state(tmp_path).invalid_generations


def test_restore_crash_midway_rolls_forward_on_restart(tmp_path: Path):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    _write(a, {"g": 1})
    _write(b, {"g": 1})
    record = create_system_checkpoint(tmp_path, [("project", a), ("config", b)])
    _write(a, {"g": 2})
    _write(b, {"g": 2})
    with pytest.raises(RuntimeError):
        restore_checkpoint(tmp_path, record.generation_id, _crash_after_writes=1)
    assert json.loads(a.read_text()) == {"g": 1}
    assert json.loads(b.read_text()) == {"g": 2}
    recovered = recover_pending_checkpoint_restore(tmp_path)
    assert recovered is not None
    assert json.loads(a.read_text()) == json.loads(b.read_text()) == {"g": 1}
    assert inspect_checkpoint_state(tmp_path).pending_restore is False


def test_restore_preserves_missing_file_semantics(tmp_path: Path):
    missing = tmp_path / "queue.json"
    existing = tmp_path / "project.json"
    _write(existing, {"g": 1})
    record = create_system_checkpoint(tmp_path, [("project", existing), ("queue", missing)])
    _write(missing, ["new"])
    restore_checkpoint(tmp_path, record.generation_id)
    assert not missing.exists()


def test_point_in_time_selects_latest_generation_not_after_target(tmp_path: Path):
    state = tmp_path / "state.json"
    _write(state, {"g": 1})
    first = create_system_checkpoint(tmp_path, {"project": state})
    _write(state, {"g": 2})
    second = create_system_checkpoint(tmp_path, {"project": state})
    _write(state, {"g": 3})
    selected = checkpoint_at_or_before(tmp_path, second.created_at_unix_ns)
    assert selected.generation_id == second.generation_id
    restore_point_in_time(tmp_path, first.created_at_unix_ns)
    assert json.loads(state.read_text()) == {"g": 1}


def test_retention_gc_removes_old_generations_and_repairs_graph(tmp_path: Path):
    state = tmp_path / "state.json"
    ids = []
    for generation in range(5):
        _write(state, {"g": generation})
        ids.append(create_system_checkpoint(tmp_path, {"project": state}).generation_id)
    removed = garbage_collect_checkpoints(tmp_path, keep=2)
    assert removed == tuple(ids[:3])
    remaining = reconcile_generation_graph(tmp_path)
    assert [item.generation_id for item in remaining] == ids[3:]
    assert remaining[0].parent_generation_id == ""
    assert remaining[1].parent_generation_id == ids[3]


def test_gc_refuses_to_run_during_pending_restore(tmp_path: Path):
    state = tmp_path / "state.json"
    _write(state, {"g": 1})
    record = create_system_checkpoint(tmp_path, {"project": state})
    _write(state, {"g": 2})
    with pytest.raises(RuntimeError):
        restore_checkpoint(tmp_path, record.generation_id, _crash_after_writes=0)
    with pytest.raises(CheckpointError):
        garbage_collect_checkpoints(tmp_path, keep=1)
    recover_pending_checkpoint_restore(tmp_path)
    assert garbage_collect_checkpoints(tmp_path, keep=1) == ()


def test_restore_probe_fails_before_any_write_for_corrupt_checkpoint(tmp_path: Path):
    state = tmp_path / "state.json"
    _write(state, {"g": 1})
    record = create_system_checkpoint(tmp_path, {"project": state})
    manifest_path = tmp_path / ".videobatch-checkpoints" / "generations" / record.generation_id / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    snapshot = manifest_path.parent / "snapshots" / manifest["files"][0]["snapshot"]
    snapshot.write_bytes(b"broken")
    _write(state, {"g": 9})
    probe = probe_checkpoint_restore(tmp_path, record.generation_id)
    assert probe.ok is False
    with pytest.raises(CheckpointError):
        restore_checkpoint(tmp_path, record.generation_id)
    assert json.loads(state.read_text()) == {"g": 9}
