"""Reject policy drift without weakening any configured quality threshold."""
from __future__ import annotations

import json
import sys
import pytest
from pathlib import Path

from scripts.internal_quality_gate import _configuration_findings, _exact_lock

ROOT = Path(__file__).resolve().parents[1]


def test_canonical_python_coverage_and_dependency_policies_agree() -> None:
    policy = json.loads((ROOT / "registries/CODE_QUALITY_REGISTRY.json").read_text())
    assert _configuration_findings(policy) == []


def test_changed_python_or_coverage_configuration_is_rejected(tmp_path: Path) -> None:
    policy = json.loads((ROOT / "registries/CODE_QUALITY_REGISTRY.json").read_text())
    toolchain = tmp_path / "config/contracts/TOOLCHAIN_CONTRACT.json"
    toolchain.parent.mkdir(parents=True)
    toolchain.write_bytes((ROOT / toolchain.relative_to(tmp_path)).read_bytes())
    source = (ROOT / "pyproject.toml").read_text()
    source = source.replace('requires-python = ">=3.11"', 'requires-python = ">=3.10"')
    source = source.replace('target-version = "py311"', 'target-version = "py310"')
    source = source.replace('fail_under = 80', 'fail_under = 1')
    (tmp_path / "pyproject.toml").write_text(source)
    findings = _configuration_findings(policy, tmp_path)
    assert len(findings) == 3
    assert {finding.code for finding in findings} == {"CONFIG_DRIFT"}


def test_lock_path_must_match_the_runtime_toolchain_contract() -> None:
    policy = json.loads((ROOT / "registries/CODE_QUALITY_REGISTRY.json").read_text())
    policy["dependency_policy"]["runtime_lock"] = "requirements.lock"
    findings = _configuration_findings(policy)
    assert [finding.code for finding in findings] == ["LOCK_PATH_DRIFT"]


def test_unpinned_dependency_is_rejected(tmp_path: Path) -> None:
    lock = tmp_path / "requirements.lock"
    lock.write_text("Pillow>=13.0.0\n")
    assert [finding.code for finding in _exact_lock(lock)] == ["LOCK_NOT_EXACT"]


@pytest.mark.parametrize("lines,branches,expected", [(80, 65, 0), (79, 65, 1), (80, 64, 1)])
def test_default_coverage_policy_preserves_explicit_minima(tmp_path, monkeypatch, lines, branches, expected) -> None:
    from scripts import coverage_policy

    report = tmp_path / "coverage.json"
    report.write_text(json.dumps({"totals": {
        "num_statements": 100, "covered_lines": lines,
        "num_branches": 100, "covered_branches": branches,
    }}))
    monkeypatch.setattr(sys, "argv", ["coverage_policy.py", str(report)])
    assert coverage_policy.main() == expected
    monkeypatch.setattr(sys, "argv", ["coverage_policy.py", str(report), "80", "65"])
    assert coverage_policy.main() == expected
