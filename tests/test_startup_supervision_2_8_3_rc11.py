from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import toolchain  # noqa: E402
from toolchain_common import load_contract  # noqa: E402
from videobatch_fast.instance_lock import focus_request_token, request_existing_instance_focus  # noqa: E402
from videobatch_fast.startup_handshake import read_ready_marker, signal_ui_ready  # noqa: E402


def test_ui_ready_handshake_is_atomic_and_machine_readable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    marker = tmp_path / "ready.json"
    monkeypatch.setenv("VIDEOBATCH_UI_READY_FILE", str(marker))
    monkeypatch.setenv("VIDEOBATCH_SAFE_MODE", "1")
    assert signal_ui_ready() == marker
    payload = read_ready_marker(marker)
    assert payload is not None
    assert payload["pid"] == os.getpid()
    assert payload["safe_mode"] is True
    assert payload["existing_instance"] is False


def test_existing_instance_focus_request_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    before = focus_request_token()
    token = request_existing_instance_focus()
    assert token > before
    assert focus_request_token() == token


def test_runtime_marker_is_repaired_without_reinstall(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    contract = load_contract(ROOT)
    target = tmp_path / "runtime"
    python = target / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.write_text("#!/bin/sh\n", encoding="utf-8")
    python.chmod(0o755)
    monkeypatch.setattr(toolchain, "environment_path", lambda _contract, _scope: target)
    monkeypatch.setattr(toolchain, "venv_python", lambda _contract, _scope: python)
    monkeypatch.setattr(toolchain, "installed_versions", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(toolchain, "runtime_import_gate", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(toolchain, "write_ready_marker", lambda *_args, **_kwargs: (target / ".videobatch-ready.json").write_text("{}", encoding="utf-8"))
    repaired = toolchain.repair_environment_state(contract, "runtime")
    assert repaired == python
    assert (target / ".videobatch-ready.json").is_file()


def test_startup_supervisor_retries_normal_failure_in_safe_mode() -> None:
    source = (SCRIPTS / "bootstrap.py").read_text(encoding="utf-8")
    assert "launch_application(python, environment, sink, safe_mode=False, timeout=ready_timeout)" in source
    assert "launch_application(python, safe_environment, sink, safe_mode=True, timeout=ready_timeout)" in source
    assert "VIDEOBATCH_UI_READY_FILE" in source
    assert "APPLICATION EXITED" in source
    assert "UI_READY TIMEOUT" in source


def test_quality_environment_is_not_referenced_by_application_bootstrap() -> None:
    source = (SCRIPTS / "bootstrap.py").read_text(encoding="utf-8")
    assert '"prepare", "--scope", "runtime"' in source
    assert '"prepare", "--scope", "quality"' not in source


def test_startup_probe_uses_degraded_state_instead_of_blocked_state() -> None:
    source = (SCRIPTS / "startup_check.py").read_text(encoding="utf-8")
    assert 'status = "degraded" if failed else "warning" if warned else "ready"' in source
    assert '"status":"blocked"' not in source.replace(" ", "")


def test_second_launch_requests_focus_and_returns_success() -> None:
    source = (ROOT / "src" / "videobatch_fast" / "app.py").read_text(encoding="utf-8")
    assert "request_existing_instance_focus()" in source
    assert "signal_ui_ready(existing_instance=True)" in source
    assert "return 0" in source


def test_verified_system_python_is_last_resort_and_forces_safe_mode() -> None:
    source = (SCRIPTS / "bootstrap.py").read_text(encoding="utf-8")
    assert "def system_runtime_fallback" in source
    assert "SYSTEM_RUNTIME_FALLBACK_OK" in source
    assert "return fallback, True" in source
    assert "if runtime_fallback:" in source
    assert '"VIDEOBATCH_STARTUP_STATUS": "degraded"' in source


def test_graphical_bootstrap_returns_success_after_confirmed_ui_ready() -> None:
    source = (SCRIPTS / "bootstrap.py").read_text(encoding="utf-8")
    assert 'result = {"code": 1}' in source
    assert 'result["code"] = 0' in source
    assert 'return int(result["code"])' in source
