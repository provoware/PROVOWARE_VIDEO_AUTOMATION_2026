from __future__ import annotations

import json
from pathlib import Path

import pytest

from videobatch_fast.transaction_store import (
    TransactionConflictError,
    TransactionError,
    current_revision,
    recover_pending_transaction,
    transactional_write_json,
)


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_cross_file_transaction_commits_same_generation(tmp_path: Path):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    result = transactional_write_json(tmp_path, {a: {"value": 1}, b: {"value": 2}})
    assert read(a) == {"value": 1}
    assert read(b) == {"value": 2}
    assert result.revisions == {"a.json": 1, "b.json": 1}
    assert not (tmp_path / ".videobatch-transactions" / "pending.json").exists()


def test_crash_after_first_file_is_roll_forward_recovered(tmp_path: Path):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    transactional_write_json(tmp_path, {a: {"old": True}, b: {"old": True}})
    with pytest.raises(RuntimeError):
        transactional_write_json(
            tmp_path,
            {a: {"generation": 2}, b: {"generation": 2}},
            expected_revisions={a: 1, b: 1},
            _crash_after_writes=1,
        )
    assert read(a) == {"generation": 2}
    assert read(b) == {"old": True}
    recovered = recover_pending_transaction(tmp_path)
    assert recovered is not None and recovered.recovered
    assert read(a) == {"generation": 2}
    assert read(b) == {"generation": 2}
    assert current_revision(tmp_path, a) == 2
    assert current_revision(tmp_path, b) == 2


def test_crash_after_wal_before_data_is_recovered(tmp_path: Path):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    with pytest.raises(RuntimeError):
        transactional_write_json(tmp_path, {a: {"x": 1}, b: {"x": 1}}, _crash_after_writes=0)
    assert not a.exists() and not b.exists()
    recover_pending_transaction(tmp_path)
    assert read(a) == {"x": 1} and read(b) == {"x": 1}


def test_optimistic_revision_rejects_lost_update(tmp_path: Path):
    target = tmp_path / "state.json"
    transactional_write_json(tmp_path, {target: {"writer": "first"}})
    transactional_write_json(tmp_path, {target: {"writer": "second"}}, expected_revisions={target: 1})
    with pytest.raises(TransactionConflictError):
        transactional_write_json(tmp_path, {target: {"writer": "stale"}}, expected_revisions={target: 1})
    assert read(target) == {"writer": "second"}
    assert current_revision(tmp_path, target) == 2


def test_pending_transaction_is_completed_before_next_writer(tmp_path: Path):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    with pytest.raises(RuntimeError):
        transactional_write_json(tmp_path, {a: {"tx": 1}, b: {"tx": 1}}, _crash_after_writes=1)
    transactional_write_json(tmp_path, {a: {"tx": 2}}, expected_revisions={a: 1})
    assert read(a) == {"tx": 2}
    assert read(b) == {"tx": 1}
    assert current_revision(tmp_path, a) == 2
    assert current_revision(tmp_path, b) == 1


def test_target_outside_root_is_rejected(tmp_path: Path):
    with pytest.raises(TransactionError):
        transactional_write_json(tmp_path, {tmp_path.parent / "escape.json": {"x": 1}})


def test_corrupt_journal_fails_closed_without_overwriting_data(tmp_path: Path):
    target = tmp_path / "state.json"
    transactional_write_json(tmp_path, {target: {"safe": True}})
    pending = tmp_path / ".videobatch-transactions" / "pending.json"
    pending.write_text('{"schema_version":1,"transaction_id":"bad","writes":[{"path":"state.json","value":{"safe":false},"sha256":"wrong"}],"revisions":{"state.json":2}}', encoding="utf-8")
    with pytest.raises(TransactionError):
        recover_pending_transaction(tmp_path)
    assert read(target) == {"safe": True}


def test_commit_marker_matches_latest_transaction(tmp_path: Path):
    target = tmp_path / "state.json"
    result = transactional_write_json(tmp_path, {target: {"ok": True}})
    marker = read(tmp_path / ".videobatch-transactions" / "last-commit.json")
    assert marker["transaction_id"] == result.transaction_id
    assert marker["revisions"] == {"state.json": 1}


def test_backup_history_and_integrity_meta_move_together(monkeypatch, tmp_path: Path):
    import videobatch_fast.project_backup as backup

    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    monkeypatch.setattr(backup, "project_backup_directory", lambda: backup_dir)
    project = tmp_path / "project.json"
    project.write_text('{"schema_version":3,"project_name":"W10"}', encoding="utf-8")
    record = backup.create_project_backup(project)
    history = read(backup_dir / "history.json")
    meta = read(backup_dir / "history.meta.json")
    assert history[0]["path"] == str(record.path)
    assert meta["count"] == len(history) == 1
    assert len(meta["history_sha256"]) == 64
    assert current_revision(backup_dir, backup_dir / "history.json") >= 1
    assert current_revision(backup_dir, backup_dir / "history.meta.json") >= 1


def test_backup_history_meta_mismatch_fails_to_history_rebuild(monkeypatch, tmp_path: Path):
    import videobatch_fast.project_backup as backup

    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    monkeypatch.setattr(backup, "project_backup_directory", lambda: backup_dir)
    project = tmp_path / "project.json"
    project.write_text('{"schema_version":3,"project_name":"W10"}', encoding="utf-8")
    record = backup.create_project_backup(project)
    meta = read(backup_dir / "history.meta.json")
    meta["history_sha256"] = "0" * 64
    (backup_dir / "history.meta.json").write_text(json.dumps(meta), encoding="utf-8")
    listed = backup.list_project_backups()
    assert [item.path for item in listed] == [record.path]
    repaired_meta = read(backup_dir / "history.meta.json")
    assert repaired_meta["history_sha256"] != "0" * 64
