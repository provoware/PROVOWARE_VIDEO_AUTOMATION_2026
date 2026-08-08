from __future__ import annotations

import json
import zipfile
from pathlib import Path

from videobatch_fast.project_backup import (
    ProjectBackupError, create_project_backup, latest_project_backup, restore_project_backup, verify_project_backup,
)


def test_project_backup_is_verified_and_history_is_real(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    project = tmp_path / "demo.vbfast.json"
    project.write_text(json.dumps({"project_name": "Demo", "jobs": []}), encoding="utf-8")

    record = create_project_backup(project)

    assert record.path.is_file()
    with zipfile.ZipFile(record.path) as archive:
        assert archive.testzip() is None
        assert project.name in archive.namelist()
        manifest = json.loads(archive.read("backup_manifest.json"))
        assert manifest["scope"] == "project_state_only"
    latest = latest_project_backup()
    assert latest is not None
    assert latest.path == record.path
    assert latest.sha256 == record.sha256


def test_project_backup_history_skips_missing_file(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    project = tmp_path / "demo.vbfast.json"
    project.write_text("{}", encoding="utf-8")
    record = create_project_backup(project)
    record.path.unlink()
    assert latest_project_backup() is None


def test_project_backup_restore_is_verified_and_non_destructive(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    project = tmp_path / "demo.vbfast.json"
    project.write_text(json.dumps({"project_name": "Demo", "media_tags": {"/a": ["X"]}}), encoding="utf-8")
    record = create_project_backup(project)
    manifest = verify_project_backup(record.path)
    assert manifest["source_sha256"] == record.sha256
    restored = restore_project_backup(record.path, tmp_path / "restored.vbfast.json")
    assert restored.read_bytes() == project.read_bytes()
    try:
        restore_project_backup(record.path, restored)
    except ProjectBackupError as exc:
        assert "existiert bereits" in str(exc)
    else:
        raise AssertionError("Existing project must not be overwritten implicitly")


def test_latest_backup_skips_corrupt_archive(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    project = tmp_path / "demo.vbfast.json"
    project.write_text("{}", encoding="utf-8")
    record = create_project_backup(project)
    record.path.write_bytes(b"not-a-zip")
    assert latest_project_backup() is None


def test_list_project_backups_returns_only_verified_records(monkeypatch, tmp_path: Path) -> None:
    from videobatch_fast.project_backup import list_project_backups

    monkeypatch.setattr("videobatch_fast.project_backup.state_dir", lambda: tmp_path / "state")
    project = tmp_path / "project.vbfast.json"
    project.write_text('{"jobs": []}', encoding="utf-8")
    first = create_project_backup(project)
    project.write_text('{"jobs": [1]}', encoding="utf-8")
    second = create_project_backup(project)
    records = list_project_backups()
    assert [item.path for item in records[:2]] == [second.path, first.path]
    first.path.write_bytes(b"broken")
    records = list_project_backups()
    assert [item.path for item in records] == [second.path]


def test_project_backup_rejects_non_object_json(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    project = tmp_path / "broken.vbfast.json"
    project.write_text("[]", encoding="utf-8")
    try:
        create_project_backup(project)
    except ProjectBackupError as exc:
        assert "Projektobjekt" in str(exc)
    else:
        raise AssertionError("A project backup must reject non-object JSON")


def test_project_backup_manifest_tracks_project_schema(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    project = tmp_path / "schema.vbfast.json"
    project.write_text(json.dumps({"schema_version": 3, "jobs": []}), encoding="utf-8")
    record = create_project_backup(project)
    manifest = verify_project_backup(record.path)
    assert manifest["project_schema_version"] == 3


def test_project_backup_rejects_oversized_declared_payload(monkeypatch, tmp_path: Path) -> None:
    from videobatch_fast.project_backup import MAX_PROJECT_STATE_BYTES

    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    archive_path = tmp_path / "oversized.vbfast-backup.zip"
    manifest = {
        "schema_version": 1,
        "scope": "project_state_only",
        "source_name": "project.vbfast.json",
        "source_sha256": "0" * 64,
        "source_size_bytes": MAX_PROJECT_STATE_BYTES + 1,
    }
    # A sparse/highly compressible member still has the dangerous uncompressed size.
    payload = b" " * (MAX_PROJECT_STATE_BYTES + 1)
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("project.vbfast.json", payload)
        archive.writestr("backup_manifest.json", json.dumps(manifest))
    try:
        verify_project_backup(archive_path)
    except ProjectBackupError as exc:
        assert "Größenlimit" in str(exc)
    else:
        raise AssertionError("Oversized project members must be rejected before reading")
