"""Candidate evidence is a provenance snapshot, never an implicit release approval."""
from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("pr240_quality_generator", ROOT / "generate_candidate_quality.py")
assert SPEC and SPEC.loader
generator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generator)


@pytest.fixture
def snapshot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    payload = json.loads((ROOT / "CANDIDATE_PR240_CI_EVIDENCE.json").read_text(encoding="utf-8"))
    target = tmp_path / "evidence.json"
    target.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(generator, "INPUT", target)
    monkeypatch.setattr(generator, "OUTPUT", tmp_path / "quality.json")
    return payload


def save_snapshot(payload: dict) -> None:
    generator.INPUT.write_text(json.dumps(payload), encoding="utf-8")


def test_report_is_reproducible_but_not_release_approval(
    snapshot: dict, monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = generator.build()
    assert result["candidate_commit"] == snapshot["source_commit"]
    assert result["measured_source_commit"] == snapshot["latest_observed_candidate_ci"]["source_commit"]
    assert result["measured_source_commit"] == result["candidate_commit"]
    assert result["verified_core_partition"]["passed"] == 167
    assert "Release contract sync" in result["blocking_checks"]
    assert result["release_approved"] is False
    assert result["ready_to_merge"] is False
    assert result["physical_ui_acceptance"] == "open"
    assert "Physische Kubuntu-/Wayland-Abnahme" in result["blocking_checks"]
    monkeypatch.setattr(sys, "argv", ["generator", "--check"])
    assert generator.main() == 1
    monkeypatch.setattr(sys, "argv", ["generator"])
    assert generator.main() == 0
    monkeypatch.setattr(sys, "argv", ["generator", "--check"])
    assert generator.main() == 0
    generator.OUTPUT.write_text("{}\n", encoding="utf-8")
    assert generator.main() == 1


@pytest.mark.parametrize("tamper", ["other_commit", "duplicate_check", "wrong_url", "fake_release"])
def test_modified_or_falsely_approved_evidence_is_rejected(snapshot: dict, tamper: str) -> None:
    changed = copy.deepcopy(snapshot)
    if tamper == "other_commit":
        changed["checks"][0]["source_commit"] = "0" * 40
    elif tamper == "duplicate_check":
        changed["checks"][1]["name"] = changed["checks"][0]["name"]
    elif tamper == "wrong_url":
        changed["checks"][0]["url"] += "/not-the-original-run"
    elif tamper == "fake_release":
        changed["stable_ready"] = True
    save_snapshot(changed)
    with pytest.raises(ValueError):
        generator.build()

def test_real_acceptance_is_required_and_release_remains_unapproved(
    snapshot: dict, monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Isolated mock tests the gate logic, not a real physical approval.
    monkeypatch.setattr(generator, "_physical_acceptance_valid", lambda _manifest: True)
    accepted = generator.build()
    assert accepted["ready_to_merge"] is True
    assert accepted["release_approved"] is False
    assert accepted["physical_ui_acceptance"] == "passed"
    snapshot["checks"][0]["conclusion"] = "failure"
    save_snapshot(snapshot)
    assert generator.build()["ready_to_merge"] is False

def test_versioned_export_path_matches_real_acceptance_validator(
    snapshot: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import subprocess

    candidate_root = tmp_path / "exported-evidence"
    manifest = json.loads(generator.RELEASE_MANIFEST.read_text(encoding="utf-8"))
    versioned = candidate_root / manifest["version"]
    versioned.mkdir(parents=True)
    for name in ("kubuntu_26_04_wayland.json", "long_render.json"):
        (versioned / name).write_text("{}", encoding="utf-8")

    calls = []

    def fake_run(argv, **_kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(generator, "ACCEPTANCE_DIR", candidate_root)
    monkeypatch.setattr(generator.subprocess, "run", fake_run)
    assert generator._physical_acceptance_valid(snapshot["source_release_manifest"])
    assert calls[0][calls[0].index("--evidence-dir") + 1] == str(versioned)

    wrong = dict(snapshot["source_release_manifest"], files_sha256="0" * 64)
    assert not generator._physical_acceptance_valid(wrong)
