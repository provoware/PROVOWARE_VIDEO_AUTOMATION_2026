from __future__ import annotations

import json
import warnings
import zipfile
from pathlib import Path

from videobatch_fast.project_backup import ProjectBackupError, create_project_backup, verify_project_backup
from videobatch_fast.project_state import MAX_PROJECT_STATE_BYTES, PROJECT_SCHEMA_VERSION, load_project_state


def _expect_backup_error(path: Path, needle: str) -> None:
    try:
        verify_project_backup(path)
    except ProjectBackupError as exc:
        assert needle in str(exc)
    else:
        raise AssertionError("Invalid backup must be rejected")


def test_project_loader_quarantines_non_object_json(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    project = tmp_path / "bad.vbfast.json"
    project.write_text("[]", encoding="utf-8")
    loaded_path, state, recovered = load_project_state(project)
    assert loaded_path == project
    assert recovered is True
    assert state["schema_version"] == PROJECT_SCHEMA_VERSION
    assert json.loads(project.read_text(encoding="utf-8"))["schema_version"] == PROJECT_SCHEMA_VERSION
    assert list(tmp_path.glob("bad.vbfast.corrupt.*.json"))


def test_project_loader_quarantines_future_schema(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    project = tmp_path / "future.vbfast.json"
    project.write_text(json.dumps({"schema_version": PROJECT_SCHEMA_VERSION + 1}), encoding="utf-8")
    _path, state, recovered = load_project_state(project)
    assert recovered is True
    assert state["schema_version"] == PROJECT_SCHEMA_VERSION
    assert list(tmp_path.glob("future.vbfast.corrupt.*.json"))


def test_project_loader_rejects_oversized_state_without_json_parse(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    project = tmp_path / "huge.vbfast.json"
    project.write_bytes(b" " * (MAX_PROJECT_STATE_BYTES + 1))
    _path, state, recovered = load_project_state(project)
    assert recovered is True
    assert state["schema_version"] == PROJECT_SCHEMA_VERSION
    quarantined = list(tmp_path.glob("huge.vbfast.corrupt.*.json"))
    assert len(quarantined) == 1
    assert quarantined[0].stat().st_size == MAX_PROJECT_STATE_BYTES + 1


def test_backup_rejects_duplicate_zip_members(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    archive_path = tmp_path / "duplicate.zip"
    manifest = {"schema_version": 1, "scope": "project_state_only", "source_name": "project.json", "source_sha256": "0" * 64, "source_size_bytes": 2}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr("project.json", b"{}")
            archive.writestr("backup_manifest.json", json.dumps(manifest))
            archive.writestr("project.json", b"{}")
    _expect_backup_error(archive_path, "doppelte ZIP-Einträge")


def test_backup_rejects_unexpected_extra_member(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    project = tmp_path / "demo.vbfast.json"
    project.write_text("{}", encoding="utf-8")
    record = create_project_backup(project)
    modified = tmp_path / "extra.zip"
    with zipfile.ZipFile(record.path, "r") as source, zipfile.ZipFile(modified, "w") as target:
        for info in source.infolist():
            target.writestr(info.filename, source.read(info.filename))
        target.writestr("unexpected.txt", "x")
    _expect_backup_error(modified, "unerwartete Zusatzdateien")


def test_backup_rejects_unknown_manifest_schema(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    project = tmp_path / "demo.vbfast.json"
    project.write_text("{}", encoding="utf-8")
    record = create_project_backup(project)
    modified = tmp_path / "schema.zip"
    with zipfile.ZipFile(record.path, "r") as source, zipfile.ZipFile(modified, "w") as target:
        manifest = json.loads(source.read("backup_manifest.json"))
        manifest["schema_version"] = 999
        for info in source.infolist():
            payload = json.dumps(manifest).encode() if info.filename == "backup_manifest.json" else source.read(info.filename)
            target.writestr(info.filename, payload)
    _expect_backup_error(modified, "Manifest-Schemaversion")
