from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import pytest

from videobatch_fast.fault_lab import run_fault_lab
from videobatch_fast import probe

ROOT = Path(__file__).resolve().parents[1]


def _load_script(name: str):
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(name.replace(".py", ""), path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_portable_contract_is_explicit_and_runtime_only():
    contract = json.loads((ROOT / "PORTABLE_RUNTIME_CONTRACT.json").read_text(encoding="utf-8"))
    assert contract["release_target"] == json.loads((ROOT / "VERSION.json").read_text(encoding="utf-8"))["build"]
    assert contract["policy"]["network_not_required_at_runtime"] is True
    assert contract["policy"]["quality_tools_are_not_part_of_user_runtime"] is True
    assert {"aac", "libx264"}.issubset(contract["ffmpeg"]["required_encoders"])


def test_portable_manifest_rejects_tampering(tmp_path: Path):
    runtime = _load_script("portable_runtime.py")
    (tmp_path / "file.txt").write_text("original", encoding="utf-8")
    runtime.write_manifest(tmp_path, metadata={"release_target": "test"})
    assert runtime.verify_manifest(tmp_path) == []
    (tmp_path / "file.txt").write_text("changed", encoding="utf-8")
    assert any("stimmt nicht" in item for item in runtime.verify_manifest(tmp_path))


def test_probe_prefers_explicit_portable_binaries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    ffmpeg = tmp_path / "ffmpeg"
    ffprobe = tmp_path / "ffprobe"
    for path in (ffmpeg, ffprobe):
        path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        path.chmod(0o755)
    monkeypatch.setenv("VIDEOBATCH_FFMPEG", str(ffmpeg))
    monkeypatch.setenv("VIDEOBATCH_FFPROBE", str(ffprobe))
    assert probe.ffmpeg_path() == str(ffmpeg)
    assert probe.ffprobe_path() == str(ffprobe)


def test_fault_lab_contract_and_all_scenarios_pass():
    contract = json.loads((ROOT / "FAULT_LAB_CONTRACT.json").read_text(encoding="utf-8"))
    results = run_fault_lab()
    assert len(results) == len(contract["scenarios"]) == 12
    assert {item.scenario_id for item in results} == set(contract["scenarios"])
    assert all(item.status == "pass" for item in results), results


def test_bootstrap_has_portable_fast_path_and_launcher_override():
    source = (ROOT / "scripts/bootstrap.py").read_text(encoding="utf-8")
    assert 'VIDEOBATCH_PORTABLE' in source
    assert 'VIDEOBATCH_PORTABLE_LAUNCHER' in source
    assert 'PORTABLE_RUNTIME_VERIFIED' in source


def test_fault_lab_is_available_from_main_entry_and_help_center():
    shell = (ROOT / "videobatch.sh").read_text(encoding="utf-8")
    services = (ROOT / "src/videobatch_fast/ui_services_mixin.py").read_text(encoding="utf-8")
    assert "fault-lab)" in shell
    assert "on_run_fault_lab=self._run_fault_lab" in services
