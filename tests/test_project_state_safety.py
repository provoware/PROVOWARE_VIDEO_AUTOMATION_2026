"""No data-loss behaviour for project loading and recovery."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from videobatch_fast import project_state


def test_corrupt_project_is_quarantined_before_fresh_state(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(project_state, "ensure_app_dirs", lambda: None)
    original = tmp_path / "project.vbfast.json"
    original.write_bytes(b"{incomplete project")
    selected, state, healed = project_state.load_project_state(original)
    assert selected == original
    assert healed
    assert state["project_name"] == "Neues Projekt"
    assert json.loads(original.read_text(encoding="utf-8"))["schema_version"] >= 1
    backups = list(tmp_path.glob("project.vbfast.corrupt.*.json"))
    assert len(backups) == 1
    assert backups[0].read_bytes() == b"{incomplete project"


def test_unreadable_project_is_not_quarantined_or_rewritten(
    tmp_path: Path, monkeypatch,
) -> None:
    monkeypatch.setattr(project_state, "ensure_app_dirs", lambda: None)
    file = tmp_path / "project.vbfast.json"
    before = b'{"project_name":"Unersetzlich"}'
    file.write_bytes(before)
    original_read = Path.read_text

    def denied(path: Path, *args, **kwargs):
        if path == file:
            raise PermissionError("kein Zugriff")
        return original_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", denied)
    with pytest.raises(PermissionError):
        project_state.load_project_state(file)
    assert file.read_bytes() == before
    assert list(tmp_path.glob("*.corrupt.*")) == []


def test_failed_quarantine_must_never_destroy_corrupt_project(
    tmp_path: Path, monkeypatch,
) -> None:
    monkeypatch.setattr(project_state, "ensure_app_dirs", lambda: None)
    file = tmp_path / "project.vbfast.json"
    file.write_bytes(b"broken")
    def cannot_backup(*_args, **_kwargs):
        raise PermissionError("disk read-only")
    monkeypatch.setattr(project_state, "quarantine_file", cannot_backup)
    with pytest.raises(PermissionError):
        project_state.load_project_state(file)
    assert file.read_bytes() == b"broken"


def test_json_list_is_not_silently_accepted_as_an_empty_project(
    tmp_path: Path, monkeypatch,
) -> None:
    monkeypatch.setattr(project_state, "ensure_app_dirs", lambda: None)
    file = tmp_path / "project.vbfast.json"
    file.write_text('["this is not a project"]', encoding="utf-8")
    _, state, healed = project_state.load_project_state(file)
    assert healed
    assert state["project_name"] == "Neues Projekt"
    assert list(tmp_path.glob("*.corrupt.*"))


def test_missing_user_selected_project_is_not_created(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(project_state, "ensure_app_dirs", lambda: None)
    monkeypatch.setattr(project_state, "default_project_file",
                        lambda: tmp_path / "default.vbfast.json")
    missing = tmp_path / "vanished.vbfast.json"
    with pytest.raises(FileNotFoundError):
        project_state.load_project_state(missing)
    assert not missing.exists()
    project, state, healed = project_state.load_project_state()
    assert project == tmp_path / "default.vbfast.json"
    assert project.is_file()
    assert not healed
