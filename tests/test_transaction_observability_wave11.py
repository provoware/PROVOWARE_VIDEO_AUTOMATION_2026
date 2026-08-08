from __future__ import annotations

import json
from pathlib import Path

import pytest

from videobatch_fast.transaction_store import (
    TransactionError,
    inspect_transaction_state,
    prune_orphan_revisions,
    recover_pending_transaction,
    rollback_pending_transaction,
    transaction_audit_timeline,
    transactional_write_json,
)


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def control(root: Path) -> Path:
    return root / ".videobatch-transactions"


def test_corrupt_pending_is_quarantined_and_never_applied(tmp_path: Path):
    target = tmp_path / "state.json"
    transactional_write_json(tmp_path, {target: {"safe": True}})
    pending = control(tmp_path) / "pending.json"
    pending.write_text(
        '{"schema_version":1,"transaction_id":"bad","writes":[{"path":"state.json","value":{"safe":false},"sha256":"wrong"}],"revisions":{"state.json":2}}',
        encoding="utf-8",
    )
    with pytest.raises(TransactionError):
        recover_pending_transaction(tmp_path)
    assert read(target) == {"safe": True}
    assert not pending.exists()
    quarantined = list((control(tmp_path) / "quarantine").glob("pending.json.*.quarantine"))
    assert len(quarantined) == 1
    assert any(e.get("event") == "TRANSACTION_QUARANTINED" for e in transaction_audit_timeline(tmp_path))


def test_controlled_rollback_restores_pretransaction_state(tmp_path: Path):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    transactional_write_json(tmp_path, {a: {"generation": 1}, b: {"generation": 1}})
    with pytest.raises(RuntimeError):
        transactional_write_json(
            tmp_path,
            {a: {"generation": 2}, b: {"generation": 2}},
            _crash_after_writes=1,
        )
    assert read(a) == {"generation": 2}
    assert read(b) == {"generation": 1}
    result = rollback_pending_transaction(tmp_path)
    assert result is not None
    assert read(a) == {"generation": 1}
    assert read(b) == {"generation": 1}
    assert not (control(tmp_path) / "pending.json").exists()
    assert any(e.get("event") == "TRANSACTION_ROLLED_BACK" for e in transaction_audit_timeline(tmp_path))


def test_rollback_removes_target_that_did_not_exist_before(tmp_path: Path):
    a = tmp_path / "new.json"
    with pytest.raises(RuntimeError):
        transactional_write_json(tmp_path, {a: {"created": True}}, _crash_after_writes=1)
    assert a.exists()
    rollback_pending_transaction(tmp_path)
    assert not a.exists()


def test_corrupt_commit_marker_is_quarantined_by_health_check(tmp_path: Path):
    target = tmp_path / "state.json"
    transactional_write_json(tmp_path, {target: {"ok": True}})
    commit = control(tmp_path) / "last-commit.json"
    commit.write_text('{"schema_version":999,"transaction_id":"future","revisions":{}}', encoding="utf-8")
    health = inspect_transaction_state(tmp_path)
    assert health.status == "degraded"
    assert not commit.exists()
    assert health.quarantined_count >= 1
    assert any("Commit-Marker" in issue for issue in health.issues)


def test_corrupt_revision_registry_is_quarantined_without_touching_user_data(tmp_path: Path):
    target = tmp_path / "state.json"
    transactional_write_json(tmp_path, {target: {"safe": True}})
    revisions = control(tmp_path) / "revisions.json"
    revisions.write_text('{"schema_version":1,"revisions":{"state.json":-7}}', encoding="utf-8")
    health = inspect_transaction_state(tmp_path)
    assert health.status == "degraded"
    assert read(target) == {"safe": True}
    assert not revisions.exists()
    assert health.quarantined_count >= 1


def test_orphan_revision_detection_and_metadata_only_prune(tmp_path: Path):
    target = tmp_path / "state.json"
    transactional_write_json(tmp_path, {target: {"ok": True}})
    target.unlink()
    health = inspect_transaction_state(tmp_path)
    assert health.orphan_revisions == ("state.json",)
    assert prune_orphan_revisions(tmp_path) == ("state.json",)
    healed = inspect_transaction_state(tmp_path)
    assert healed.orphan_revisions == ()


def test_health_check_recovers_valid_pending_on_startup_mode(tmp_path: Path):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    with pytest.raises(RuntimeError):
        transactional_write_json(tmp_path, {a: {"x": 1}, b: {"x": 1}}, _crash_after_writes=1)
    health = inspect_transaction_state(tmp_path, recover=True)
    assert health.healthy
    assert read(a) == {"x": 1}
    assert read(b) == {"x": 1}
    assert any(e.get("event") == "TRANSACTION_RECOVERED" for e in transaction_audit_timeline(tmp_path))


def test_audit_timeline_survives_malformed_line(tmp_path: Path):
    target = tmp_path / "state.json"
    transactional_write_json(tmp_path, {target: {"ok": True}})
    audit = control(tmp_path) / "audit.jsonl"
    with audit.open("a", encoding="utf-8") as handle:
        handle.write("not-json\n")
    events = transaction_audit_timeline(tmp_path)
    assert events
    assert all(isinstance(item, dict) for item in events)


def test_backup_history_and_project_state_crash_recovery_are_independent(monkeypatch, tmp_path: Path):
    import videobatch_fast.project_backup as backup

    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    monkeypatch.setattr(backup, "project_backup_directory", lambda: backup_dir)
    project = tmp_path / "project.json"
    project.write_text('{"schema_version":3,"project_name":"W11-old"}', encoding="utf-8")
    record = backup.create_project_backup(project)

    project_root = tmp_path / "project-tx"
    project_root.mkdir()
    project_state = project_root / "project-state.json"
    with pytest.raises(RuntimeError):
        transactional_write_json(project_root, {project_state: {"project_name": "W11-new"}}, _crash_after_writes=0)

    # Backup integrity remains independently reconstructable while project-state WAL is pending.
    records = backup.list_project_backups(limit=10)
    assert [item.path for item in records] == [record.path]
    health = inspect_transaction_state(project_root, recover=True)
    assert health.healthy
    assert read(project_state) == {"project_name": "W11-new"}
