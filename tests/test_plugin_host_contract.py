"""Plugin protocol unit tests; mocked isolation is not an OS-sandbox acceptance."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from videobatch_fast import plugin_host as host


def test_isolation_failure_prevents_any_plugin_execution(monkeypatch) -> None:
    def blocked():
        raise host.SandboxUnavailable("unavailable")
    monkeypatch.setattr(host, "apply_plugin_sandbox", blocked)
    payload = {}
    with pytest.raises(host.SandboxUnavailable):
        host._execute_validator("def validate(payload):\n payload['executed'] = True\n return True\n", payload)
    assert payload == {}


@pytest.mark.parametrize("source,error", [
    ("def broken(:", SyntaxError),
    ("validate = 7", RuntimeError),
    ("def validate(payload):\n return open('not-created')", NameError),
    ("def validate(payload):\n return __import__('os')", NameError),
])
def test_invalid_or_privileged_validator_code_is_rejected(monkeypatch, source, error) -> None:
    monkeypatch.setattr(host, "apply_plugin_sandbox", lambda: None)
    with pytest.raises(error):
        host._execute_validator(source, {})


@pytest.mark.parametrize("payload", [{"value": 1}, {"value": 5}])
def test_trusted_validator_obeys_payload_without_general_python_builtins(monkeypatch, payload) -> None:
    monkeypatch.setattr(host, "apply_plugin_sandbox", lambda: None)
    result = host._execute_validator("def validate(payload):\n return int(payload.get('value', 0)) > 2", payload)
    assert result is (payload["value"] > 2)


@pytest.mark.parametrize("capability,payload", [("validator", "[]"), ("network", "{}"), ("validator", "broken")])
def test_protocol_rejects_invalid_inputs_before_execution(tmp_path: Path, monkeypatch, capsys, capability, payload) -> None:
    def forbidden(*_args):
        raise AssertionError("must not execute")
    monkeypatch.setattr(host, "_execute_validator", forbidden)
    assert host.main([str(tmp_path), capability, payload]) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["ok"] is False
    assert "must not execute" not in result["error"]


def test_protocol_reports_missing_isolation_distinctly(tmp_path: Path, monkeypatch, capsys) -> None:
    (tmp_path / "plugin.py").write_text("def validate(payload):\n return True")
    def blocked():
        raise host.SandboxUnavailable("unavailable")
    monkeypatch.setattr(host, "apply_plugin_sandbox", blocked)
    assert host.main([str(tmp_path), "validator", "{}"]) == 3
    result = json.loads(capsys.readouterr().out)
    assert result["ok"] is False
    assert "OS-Isolierung" in result["error"]


def test_protocol_rejects_bad_argument_count(capsys) -> None:
    assert host.main(["only-one-argument"]) == 2
    assert json.loads(capsys.readouterr().out)["ok"] is False
