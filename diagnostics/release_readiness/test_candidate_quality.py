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

@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("passed", True),
        ("failed", True),
        ("failed", -1),
        ("failed", 1),
        ("failed", "0"),
    ],
)
def test_core_regression_rejects_invalid_or_failed_counts(
    snapshot: dict, field: str, value: object,
) -> None:
    changed = copy.deepcopy(snapshot)
    changed["latest_observed_candidate_ci"]["core_regression"][field] = value
    save_snapshot(changed)
    with pytest.raises(ValueError, match="Kern"):
        generator.build()


@pytest.mark.parametrize("invalid", [None, [], "passed", 17, {"result": "failed"}])
def test_invalid_offline_quality_evidence_fails_closed(snapshot: dict, invalid: object) -> None:
    changed = copy.deepcopy(snapshot)
    changed["latest_observed_candidate_ci"]["offline_quality"] = invalid
    save_snapshot(changed)
    with pytest.raises(ValueError, match="Offline-Qualitätsnachweis"):
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
    # This synthetic path-contract test uses the CURRENT manifest. The PR240
    # evidence snapshot deliberately remains bound to its historical 518-file tree.
    assert generator._physical_acceptance_valid(manifest)
    assert calls[0][calls[0].index("--evidence-dir") + 1] == str(versioned)

    wrong = dict(snapshot["source_release_manifest"], files_sha256="0" * 64)
    assert not generator._physical_acceptance_valid(wrong)


def test_compact_manifest_uses_git_tracked_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Untracked files and non-executable permission bits cannot invalidate a Git release."""
    import subprocess

    monkeypatch.syspath_prepend(str(ROOT))
    from engine import _compact_manifest_snapshot

    contract = ROOT.parents[1] / "scripts/release_file_contract.py"
    target = tmp_path / "scripts/release_file_contract.py"
    target.parent.mkdir()
    target.write_bytes(contract.read_bytes())
    tracked = tmp_path / "tracked.txt"
    tracked.write_text("original\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True, timeout=10)
    subprocess.run(
        ["git", "add", "tracked.txt", "scripts/release_file_contract.py"],
        cwd=tmp_path, check=True, timeout=10,
    )

    baseline = _compact_manifest_snapshot(tmp_path)
    assert baseline[0] == 2

    extra = tmp_path / "src" / "untracked.py"
    extra.parent.mkdir()
    extra.write_text("untracked\n", encoding="utf-8")
    assert _compact_manifest_snapshot(tmp_path) == baseline

    tracked.chmod(0o664)
    assert _compact_manifest_snapshot(tmp_path) == baseline

    tracked.write_text("changed\n", encoding="utf-8")
    changed = _compact_manifest_snapshot(tmp_path)
    assert changed[0] == baseline[0]
    assert changed[1] != baseline[1]


@pytest.mark.parametrize(
    "failure", [FileNotFoundError("tracked file missing"), RuntimeError("Git index unavailable")],
)
def test_compact_manifest_read_errors_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: Exception,
) -> None:
    """An unreadable release source must yield a red finding, not a traceback."""
    monkeypatch.syspath_prepend(str(ROOT))
    import engine

    def broken_snapshot(_root: Path) -> tuple[int, str]:
        raise failure

    monkeypatch.setattr(engine, "_compact_manifest_snapshot", broken_snapshot)
    findings: list[engine.Finding] = []
    manifest = {"representation": "compact", "file_count": 1, "files_sha256": "0" * 64}
    assert engine.validate_manifest(tmp_path, manifest, findings) is False
    assert len(findings) == 1
    assert findings[0].code == "MANIFEST_COMPACT_INVALID"
    assert findings[0].severity == "error"
    assert str(failure) in findings[0].message

@pytest.mark.parametrize(
    "source",
    [
        "def selected_release_files(:\n    pass\n",
        "import provoware_missing_release_contract_dependency_2026\n",
    ],
)
def test_compact_manifest_invalid_selector_module_is_red(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source: str,
) -> None:
    """A broken release contract must produce a red finding, not crash the dashboard."""
    monkeypatch.syspath_prepend(str(ROOT))
    import engine

    contract = tmp_path / "scripts" / "release_file_contract.py"
    contract.parent.mkdir()
    contract.write_text(source, encoding="utf-8")
    findings: list[engine.Finding] = []
    manifest = {"representation": "compact", "file_count": 1, "files_sha256": "0" * 64}
    assert engine.validate_manifest(tmp_path, manifest, findings) is False
    assert len(findings) == 1
    assert findings[0].code == "MANIFEST_COMPACT_INVALID"
    assert findings[0].severity == "error"


def test_unknown_check_cannot_replace_required_gate(snapshot: dict) -> None:
    changed = copy.deepcopy(snapshot)
    changed["checks"][0]["name"] = "Erfundene Erfolgsprüfung"
    save_snapshot(changed)
    with pytest.raises(ValueError, match="Pflichtprüfungen"):
        generator.build()
