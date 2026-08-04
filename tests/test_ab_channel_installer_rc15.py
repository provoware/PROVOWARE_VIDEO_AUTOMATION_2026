from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER_PATH = ROOT / "scripts" / "ab_launcher.py"
INSTALLER_PATH = ROOT / "scripts" / "ab_installer.py"
BUILDER_PATH = ROOT / "scripts" / "build_multipart_installer.py"
CHANNEL_BUILDER_PATH = ROOT / "scripts" / "build_channel_index.py"


def load_launcher():
    spec = importlib.util.spec_from_file_location("ab_launcher", LAUNCHER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fake_slot(root: Path, slot: str, result: int) -> None:
    target = root / "slots" / slot
    target.mkdir(parents=True)
    app = target / "AppRun"
    app.write_text(f"#!/usr/bin/env bash\nexit {result}\n", encoding="utf-8")
    app.chmod(0o755)


def switch(root: Path, slot: str) -> None:
    root.mkdir(parents=True, exist_ok=True)
    current = root / "current"
    current.unlink(missing_ok=True)
    current.symlink_to(f"slots/{slot}")


def test_boot_confirmation_commits_target_slot(tmp_path: Path) -> None:
    launcher = load_launcher()
    fake_slot(tmp_path, "A", 0)
    fake_slot(tmp_path, "B", 0)
    switch(tmp_path, "B")
    old_state = {"schema_version": 2, "version": "old", "active_slot": "A", "history": []}
    (tmp_path / "installation_state.json").write_text(json.dumps(old_state), encoding="utf-8")
    target_state = {"schema_version": 2, "version": "new", "release_sequence": 2, "components": {}, "history": []}
    transaction = {"schema_version": 1, "previous_slot": "A", "target_slot": "B", "target_state": target_state}
    (tmp_path / "pending_transaction.json").write_text(json.dumps(transaction), encoding="utf-8")
    assert launcher.recover_or_launch(tmp_path, []) == 0
    state = json.loads((tmp_path / "installation_state.json").read_text())
    assert state["active_slot"] == "B"
    assert state["previous_slot"] == "A"
    assert state["pending_boot"] is False
    assert not (tmp_path / "pending_transaction.json").exists()


def test_failed_first_boot_rolls_back_atomically(tmp_path: Path) -> None:
    launcher = load_launcher()
    fake_slot(tmp_path, "A", 0)
    fake_slot(tmp_path, "B", 9)
    switch(tmp_path, "B")
    (tmp_path / "installation_state.json").write_text(json.dumps({"schema_version": 2, "version": "old", "active_slot": "A", "history": []}), encoding="utf-8")
    transaction = {"schema_version": 1, "previous_slot": "A", "target_slot": "B", "target_state": {"version": "new", "history": []}}
    (tmp_path / "pending_transaction.json").write_text(json.dumps(transaction), encoding="utf-8")
    assert launcher.recover_or_launch(tmp_path, []) == 0
    assert launcher.slot_from_current(tmp_path) == "A"
    state = json.loads((tmp_path / "installation_state.json").read_text())
    assert state["active_slot"] == "A"
    assert state["history"][-1]["event"] == "automatic_boot_rollback"


def test_power_loss_before_symlink_switch_keeps_confirmed_slot(tmp_path: Path) -> None:
    launcher = load_launcher()
    fake_slot(tmp_path, "A", 0)
    fake_slot(tmp_path, "B", 0)
    switch(tmp_path, "A")
    (tmp_path / "installation_state.json").write_text(json.dumps({"schema_version": 2, "version": "old", "active_slot": "A", "history": []}), encoding="utf-8")
    transaction = {"schema_version": 1, "phase": "prepared", "previous_slot": "A", "target_slot": "B", "target_state": {"version": "new"}}
    (tmp_path / "pending_transaction.json").write_text(json.dumps(transaction), encoding="utf-8")
    assert launcher.recover_or_launch(tmp_path, []) == 0
    assert launcher.slot_from_current(tmp_path) == "A"
    assert not (tmp_path / "pending_transaction.json").exists()


def test_install_contract_contains_signed_channel_and_ab_guards() -> None:
    installer = INSTALLER_PATH.read_text(encoding="utf-8")
    builder = BUILDER_PATH.read_text(encoding="utf-8")
    channel = CHANNEL_BUILDER_PATH.read_text(encoding="utf-8")
    for token in (
        "pending_transaction.json",
        "atomic_switch",
        "release_sequence",
        "download_required_parts",
        "https",
        "automatic_boot_rollback",
        "slot_manifests",
    ):
        assert token in installer or token in builder
    assert "channel-index.ed25519" in channel
    assert "download_only_changed_components" in channel
    assert "component_part_signatures_required" in channel


def test_scripts_compile_and_launcher_self_test() -> None:
    subprocess.run([sys.executable, "-m", "py_compile", str(LAUNCHER_PATH), str(INSTALLER_PATH), str(BUILDER_PATH), str(CHANNEL_BUILDER_PATH)], check=True)
    completed = subprocess.run([sys.executable, str(LAUNCHER_PATH), "--self-test"], text=True, stdout=subprocess.PIPE, check=False)
    assert completed.returncode == 0
    assert "AB_LAUNCHER_OK" in completed.stdout
