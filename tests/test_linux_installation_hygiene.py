from __future__ import annotations

import json
import os
from pathlib import Path

from videobatch_fast.linux_installation import normalize_linux_installation


def _managed_root(path: Path, *, version: str, sequence: int, controller_versions: tuple[str, ...] = ()) -> None:
    (path / "slots/A").mkdir(parents=True)
    (path / "controller/versions").mkdir(parents=True)
    (path / "installation_state.json").write_text(
        json.dumps(
            {
                "product": "VideoBatch Fast",
                "version": version,
                "release_sequence": sequence,
                "active_slot": "A",
            }
        ),
        encoding="utf-8",
    )
    for name in controller_versions:
        (path / "controller/versions" / name).mkdir()
    if controller_versions:
        os.symlink(f"versions/{controller_versions[-1]}", path / "controller/current")
        if len(controller_versions) > 1:
            os.symlink(f"versions/{controller_versions[-2]}", path / "controller/previous")


def test_one_xdg_menu_entry_replaces_user_duplicates(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    data = tmp_path / "xdg-data"
    state = tmp_path / "xdg-state"
    project = tmp_path / "project"
    launcher = project / "start.sh"
    launcher.parent.mkdir(parents=True)
    launcher.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_DATA_HOME", str(data))
    monkeypatch.setenv("XDG_STATE_HOME", str(state))
    monkeypatch.delenv("VIDEOBATCH_INSTALL_ROOT", raising=False)

    apps = data / "applications"
    apps.mkdir(parents=True)
    (apps / "VideoBatch-Fast-old.desktop").write_text(
        "[Desktop Entry]\nName=VideoBatch Fast\nExec=/tmp/old/STARTEN.sh\n",
        encoding="utf-8",
    )
    unrelated = apps / "other.desktop"
    unrelated.write_text("[Desktop Entry]\nName=Other\nExec=/usr/bin/true\n", encoding="utf-8")

    report = normalize_linux_installation(project_root=project, launcher=launcher)

    canonical = apps / "videobatch-fast.desktop"
    assert canonical.is_file()
    assert "X-Provoware-AppId=videobatch-fast" in canonical.read_text(encoding="utf-8")
    assert not (apps / "VideoBatch-Fast-old.desktop").exists()
    assert unrelated.is_file()
    assert report["desktop_entries_removed"]


def test_confirmed_standard_install_retires_old_managed_root_and_prunes_controllers(
    tmp_path: Path, monkeypatch
) -> None:
    home = tmp_path / "home"
    data = tmp_path / "data"
    state = tmp_path / "state"
    canonical = data / "VideoBatchFast"
    legacy = data / "videobatch-fast"
    _managed_root(canonical, version="3.0.0", sequence=30, controller_versions=("v1", "v2", "v3"))
    _managed_root(legacy, version="2.8.3", sequence=20, controller_versions=("old",))

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_DATA_HOME", str(data))
    monkeypatch.setenv("XDG_STATE_HOME", str(state))
    monkeypatch.setenv("VIDEOBATCH_INSTALL_ROOT", str(canonical))

    report = normalize_linux_installation(project_root=tmp_path / "project", launcher=tmp_path / "start.sh")

    assert not legacy.exists()
    retired = state / "VideoBatchFast/installer/retired-installations"
    assert len([path for path in retired.iterdir() if path.is_dir()]) == 1
    assert not (canonical / "controller/versions/v1").exists()
    assert (canonical / "controller/versions/v2").is_dir()
    assert (canonical / "controller/versions/v3").is_dir()
    assert str(legacy) in report["legacy_installations_retired"]
    assert report["controller_versions_removed"] == ["v1"]


def test_pending_ab_transaction_blocks_destructive_cleanup(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    data = tmp_path / "data"
    state = tmp_path / "state"
    canonical = data / "VideoBatchFast"
    legacy = data / "videobatch-fast"
    _managed_root(canonical, version="3.0.0", sequence=30, controller_versions=("v1", "v2", "v3"))
    _managed_root(legacy, version="2.8.3", sequence=20, controller_versions=("old",))
    (canonical / "pending_transaction.json").write_text("{}", encoding="utf-8")

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_DATA_HOME", str(data))
    monkeypatch.setenv("XDG_STATE_HOME", str(state))
    monkeypatch.setenv("VIDEOBATCH_INSTALL_ROOT", str(canonical))

    report = normalize_linux_installation(project_root=tmp_path / "project", launcher=tmp_path / "start.sh")

    assert legacy.is_dir()
    assert (canonical / "controller/versions/v1").is_dir()
    assert report["destructive_cleanup_allowed"] is False
    assert report["legacy_installations_retired"] == []
