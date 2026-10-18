"""Test evidence reuse is exact, optional and never release-authorizing."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "test_evidence_registry.py"
sys.path.insert(0, str(SCRIPT.parent))
spec = importlib.util.spec_from_file_location("test_evidence_registry", SCRIPT)
assert spec and spec.loader
ledger = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ledger)


def sample() -> dict:
    return {"test_id": "docs_validation", "commit_sha": "a" * 40,
            "clean_checkout": True, "source_digest": "b" * 64,
            "environment_fingerprint": "c" * 64,
            "test_definition_digest": "d" * 64,
            "command": ["/usr/bin/python3", "scripts/validate_documentation.py"],
            "test_status": "not_run", "scope_mode": "full_tree_fallback"}


def test_only_same_successful_commit_can_be_reused() -> None:
    current = sample()
    passed = {**current, "test_status": "passed", "exit_code": 0,
              "reuse_allowed": True, "completed_unix": 1730000000}
    assert ledger.matches(passed, current)
    assert not ledger.matches({**passed, "commit_sha": "e" * 40}, current)
    assert not ledger.matches({**passed, "source_digest": "f" * 64}, current)
    assert not ledger.matches({**passed, "environment_fingerprint": "f" * 64}, current)
    assert not ledger.matches({**passed, "test_definition_digest": "f" * 64}, current)
    assert not ledger.matches({**passed, "test_status": "failed"}, current)
    assert not ledger.matches(passed, {**current, "clean_checkout": False})


def test_local_policy_never_has_release_commands() -> None:
    policy = ledger.load_policy()
    assert not policy["reused_evidence_is_release_authorization"]
    assert all(spec["cacheable"] for spec in policy["tests"].values())
    for spec in policy["tests"].values():
        command = " ".join(spec["argv"])
        assert "verify_release" not in command
        assert "test.sh" not in command


def test_changed_tree_invalidates_context(monkeypatch) -> None:
    monkeypatch.setattr(ledger, "git_identity", lambda: ("a" * 40, True))
    monkeypatch.setattr(ledger, "environment_digest", lambda: "c" * 64)
    monkeypatch.setattr(ledger, "snapshot", lambda: {"a": {"sha256": "1"}})
    policy = ledger.load_policy()
    first = ledger.current("docs_validation", policy)
    monkeypatch.setattr(ledger, "snapshot", lambda: {"a": {"sha256": "2"}})
    second = ledger.current("docs_validation", policy)
    assert first["source_digest"] != second["source_digest"]
    assert not ledger.matches({**first, "test_status": "passed"}, second)


def test_cli_caches_only_actual_success_and_exact_unchanged_inputs(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    monkeypatch.setattr(ledger, "git_identity", lambda: ("a" * 40, True))
    monkeypatch.setattr(ledger, "environment_digest", lambda: "c" * 64)
    source = {"module.py": {"sha256": "hash-a"}}
    monkeypatch.setattr(ledger, "snapshot", lambda: dict(source))
    launches = []

    def actual_execution(context, timeout):
        launches.append(context["test_id"])
        return 0, "OK from subprocess"

    monkeypatch.setattr(ledger, "execute", actual_execution)
    assert ledger.run("docs_validation", reuse=True) == 0
    assert ledger.run("docs_validation", reuse=True) == 0
    assert launches == ["docs_validation"]
    source["module.py"] = {"sha256": "hash-b"}
    assert ledger.run("docs_validation", reuse=True) == 0
    assert launches == ["docs_validation", "docs_validation"]


def test_input_mutation_during_test_is_not_pass(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    monkeypatch.setattr(ledger, "git_identity", lambda: ("a" * 40, True))
    monkeypatch.setattr(ledger, "environment_digest", lambda: "c" * 64)
    source = {"module.py": {"sha256": "hash-a"}}
    monkeypatch.setattr(ledger, "snapshot", lambda: dict(source))

    def altered_during_test(context, timeout):
        source["module.py"] = {"sha256": "hash-b"}
        return 0, "OK"

    monkeypatch.setattr(ledger, "execute", altered_during_test)
    assert ledger.run("docs_validation", reuse=False) == 1
    result = ledger.load_results()["results"]["docs_validation"]
    assert result["test_status"] == "stale"
    assert not result["reuse_allowed"]


def test_incomplete_or_forged_success_is_not_reusable() -> None:
    current = sample()
    passed = {**current, "test_status": "passed", "exit_code": 0,
              "reuse_allowed": True, "completed_unix": 1730000000}
    for field, bad in (("exit_code", 1), ("reuse_allowed", False),
                       ("completed_unix", None)):
        assert not ledger.matches({**passed, field: bad}, current)
    assert not ledger.matches({**current, "test_status": "passed"}, current)

def test_reviewed_scope_never_reuses_old_full_tree_evidence():
    current = sample()
    passed = {**current, "test_status": "passed", "exit_code": 0,
              "reuse_allowed": True, "completed_unix": 1730000000}
    assert ledger.matches(passed, current)
    assert not ledger.matches(passed, {**current, "scope_mode": "reviewed"})
    assert not ledger.matches({**passed, "scope_mode": "reviewed"}, current)
