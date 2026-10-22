"""Tests for the actual starter's update confirmation and fallback dispatch."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def _load_launcher():
    spec = importlib.util.spec_from_file_location(
        "videobatch_first_start_launcher_test", ROOT / "scripts" / "debug_launcher.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_normal_ui_ready_confirms_pending_update(tmp_path: Path, monkeypatch) -> None:
    launcher = _load_launcher()
    install = tmp_path / "install"
    install.mkdir()
    (tmp_path / ".install.update_pending.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(launcher, "ROOT", install)
    monkeypatch.setattr(launcher, "_tail", lambda *_: "UI_READY pid=100")
    monkeypatch.setattr(launcher, "_ready_pid", lambda *_: 100)
    observations = []

    def confirm(root, *, normal_ui_ready):
        observations.append((root, normal_ui_ready))
        return "confirmed"

    with patch("videobatch_fast.updates.finish_local_update_first_start", side_effect=confirm):
        assert launcher._finish_local_update_boot(Path("bootstrap.log"), started=True) is None
    assert observations == [(install, True)]


def test_failed_boot_rolls_back_and_restarts_only_once(tmp_path: Path, monkeypatch) -> None:
    launcher = _load_launcher()
    install = tmp_path / "install"
    install.mkdir()
    (tmp_path / ".install.update_pending.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(launcher, "ROOT", install)
    monkeypatch.setattr(launcher, "_tail", lambda *_: "")
    monkeypatch.setattr(launcher, "_ready_pid", lambda *_: None)
    calls = []
    monkeypatch.delenv("VIDEOBATCH_UPDATE_ROLLBACK_RETRY", raising=False)

    def rollback(root, *, normal_ui_ready):
        calls.append((root, normal_ui_ready))
        return "restored"

    def restart(args, **kwargs):
        assert args[1] == str(install / "scripts" / "debug_launcher.py")
        assert kwargs["env"]["VIDEOBATCH_UPDATE_ROLLBACK_RETRY"] == "1"
        return SimpleNamespace(returncode=0)

    with (
        patch("videobatch_fast.updates.finish_local_update_first_start", side_effect=rollback),
        patch.object(launcher.subprocess, "run", side_effect=restart),
    ):
        assert launcher._finish_local_update_boot(None, started=False) == 0
        monkeypatch.setenv("VIDEOBATCH_UPDATE_ROLLBACK_RETRY", "1")
        assert launcher._finish_local_update_boot(None, started=False) == 79
    assert calls == [(install, False), (install, False)]


def test_safe_mode_is_not_accepted_as_update_first_start(tmp_path: Path, monkeypatch) -> None:
    launcher = _load_launcher()
    install = tmp_path / "install"
    install.mkdir()
    (tmp_path / ".install.update_pending.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(launcher, "ROOT", install)
    monkeypatch.setattr(launcher, "_tail", lambda *_: "Qt im sicheren Startmodus öffnen")
    monkeypatch.setattr(launcher, "_ready_pid", lambda *_: 900)
    monkeypatch.setattr(launcher, "_process_exists", lambda *_: False)
    monkeypatch.setenv("VIDEOBATCH_UPDATE_ROLLBACK_RETRY", "1")
    observed = []
    def rollback(root, *, normal_ui_ready):
        observed.append(normal_ui_ready)
        return "restored"
    with patch("videobatch_fast.updates.finish_local_update_first_start", side_effect=rollback):
        assert launcher._finish_local_update_boot(None, started=True) == 79
    assert observed == [False]


def test_normal_safe_mode_without_update_is_not_terminated(tmp_path: Path, monkeypatch) -> None:
    launcher = _load_launcher()
    install = tmp_path / "install"
    install.mkdir()
    monkeypatch.setattr(launcher, "ROOT", install)
    monkeypatch.setattr(launcher, "_tail", lambda *_: "Qt im sicheren Startmodus öffnen")
    with patch.object(launcher.os, "kill", side_effect=AssertionError("must not stop ordinary safe mode")):
        assert launcher._finish_local_update_boot(None, started=True) is None
