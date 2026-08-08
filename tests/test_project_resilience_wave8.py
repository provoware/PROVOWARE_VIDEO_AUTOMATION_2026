from __future__ import annotations

import json
from pathlib import Path

import pytest

from videobatch_fast.project_backup import (
    ProjectBackupError,
    create_project_backup,
    list_project_backups,
    prune_project_backups,
)
from videobatch_fast.safe_io import SafeIoError, atomic_commit_file, atomic_write_bytes


def _project(path: Path, value: int = 0) -> None:
    path.write_text(json.dumps({"schema_version": 3, "project_name": f"Demo-{value}", "value": value}), encoding="utf-8")


def test_backup_survives_lost_history_and_self_heals(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    project = tmp_path / "demo.vbfast.json"
    _project(project)
    record = create_project_backup(project)
    history = record.path.parent / "history.json"
    history.unlink()

    records = list_project_backups()

    assert [item.path for item in records] == [record.path.resolve()]
    healed = json.loads(history.read_text(encoding="utf-8"))
    assert healed[0]["path"] == str(record.path.resolve())


def test_backup_survives_corrupt_history(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    project = tmp_path / "demo.vbfast.json"
    _project(project)
    record = create_project_backup(project)
    history = record.path.parent / "history.json"
    history.write_text("{broken", encoding="utf-8")

    records = list_project_backups()

    assert records and records[0].path == record.path.resolve()
    assert isinstance(json.loads(history.read_text(encoding="utf-8")), list)


def test_rotation_deletes_only_verified_managed_backups(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    project = tmp_path / "demo.vbfast.json"
    created = []
    for index in range(5):
        _project(project, index)
        created.append(create_project_backup(project).path)
    foreign = created[-1].parent / "foreign.vbfast-backup.zip"
    foreign.write_bytes(b"not-a-valid-backup")

    removed = prune_project_backups(keep=2)
    remaining = list_project_backups()

    assert len(removed) == 3
    assert len(remaining) == 2
    assert foreign.exists(), "Unknown/corrupt files must never be deleted by rotation"
    assert all(path.exists() is False for path in removed)


def test_atomic_write_keeps_old_target_when_replace_fails(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / "state.json"
    target.write_bytes(b"old")

    def fail_replace(_source, _target):
        raise OSError("simulated replace failure")

    monkeypatch.setattr("videobatch_fast.safe_io.os.replace", fail_replace)
    with pytest.raises(OSError):
        atomic_write_bytes(target, b"new")
    assert target.read_bytes() == b"old"
    assert not list(tmp_path.glob(".state.json.*.tmp"))


def test_atomic_commit_rejects_cross_directory_commit(tmp_path: Path) -> None:
    source_dir = tmp_path / "a"
    target_dir = tmp_path / "b"
    source_dir.mkdir()
    target_dir.mkdir()
    temporary = source_dir / "temp"
    temporary.write_bytes(b"payload")

    with pytest.raises(SafeIoError, match="selben Verzeichnis"):
        atomic_commit_file(temporary, target_dir / "final")


def test_backup_creation_reports_commit_failure_as_domain_error(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    project = tmp_path / "demo.vbfast.json"
    _project(project)

    def fail_commit(_source, _target):
        raise SafeIoError("simulated fsync/commit failure")

    monkeypatch.setattr("videobatch_fast.project_backup.atomic_commit_file", fail_commit)
    with pytest.raises(ProjectBackupError, match="nicht sicher erstellt"):
        create_project_backup(project)
    backup_dir = tmp_path / "state" / "videobatch-fast" / "backups" / "projects"
    assert not list(backup_dir.glob("*.vbfast-backup.zip"))
    assert not list(backup_dir.glob("*.tmp"))


def test_orphan_created_after_stale_history_is_still_latest(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    project = tmp_path / "demo.vbfast.json"
    _project(project, 1)
    first = create_project_backup(project)
    history = first.path.parent / "history.json"
    stale_history = history.read_bytes()

    _project(project, 2)
    second = create_project_backup(project)
    history.write_bytes(stale_history)  # Simulates crash/loss after archive commit but before history commit.

    records = list_project_backups(limit=2)

    assert [item.path for item in records] == [second.path.resolve(), first.path.resolve()]


def test_backup_listing_does_not_rewrite_unchanged_history(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    project = tmp_path / "demo.vbfast.json"
    _project(project)
    record = create_project_backup(project)
    history = record.path.parent / "history.json"
    before = history.stat().st_mtime_ns

    list_project_backups()
    after = history.stat().st_mtime_ns

    assert after == before
