from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

from scripts.validate_stable_acceptance import AcceptanceBlocked, REQUIRED_CHECKS, validate_evidence
from scripts.validate_version_contract import validate
from videobatch_fast.automated_desktop_approval import verify_automated_desktop_approval

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 8, 4, 12, 0, tzinfo=timezone.utc)


def _write_evidence(directory: Path, candidate: str = "2.8.3-rc24", digest: str = "a" * 64) -> None:
    for kind, required in REQUIRED_CHECKS.items():
        payload = {
            "schema_version": 1,
            "evidence_type": kind,
            "candidate_id": candidate,
            "manifest_sha256": digest,
            "environment": {"system": "Kubuntu 24.04", "session_or_target": kind},
            "timestamp": "2026-08-04T10:00:00Z",
            "result": "passed",
            "checks": {name: True for name in required},
        }
        (directory / f"{kind}.json").write_text(json.dumps(payload), encoding="utf-8")


def test_stable_acceptance_blocks_missing_evidence(tmp_path: Path) -> None:
    with pytest.raises(AcceptanceBlocked, match="kde_x11.json fehlt") as error:
        validate_evidence(tmp_path, "2.8.3-rc24", "a" * 64, now=NOW)
    for section in ("Ursache:", "Auswirkung:", "Automatische Schutzmaßnahme:", "Lösung:", "Alternative:"):
        assert section in str(error.value)


def test_stable_acceptance_blocks_wrong_candidate_hash(tmp_path: Path) -> None:
    _write_evidence(tmp_path, digest="b" * 64)
    with pytest.raises(AcceptanceBlocked, match="gehört nicht"):
        validate_evidence(tmp_path, "2.8.3-rc24", "a" * 64, now=NOW)


def test_stable_acceptance_blocks_only_one_kde_session(tmp_path: Path) -> None:
    _write_evidence(tmp_path)
    (tmp_path / "kde_wayland.json").unlink()
    with pytest.raises(AcceptanceBlocked, match="kde_wayland.json fehlt"):
        validate_evidence(tmp_path, "2.8.3-rc24", "a" * 64, now=NOW)


def test_stable_acceptance_blocks_failed_long_render(tmp_path: Path) -> None:
    _write_evidence(tmp_path)
    path = tmp_path / "long_render.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["result"] = "failed"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(AcceptanceBlocked, match="kein bestandenes Ergebnis"):
        validate_evidence(tmp_path, "2.8.3-rc24", "a" * 64, now=NOW)


def test_stable_acceptance_accepts_complete_evidence_set(tmp_path: Path) -> None:
    _write_evidence(tmp_path)
    validate_evidence(tmp_path, "2.8.3-rc24", "a" * 64, now=NOW)


def test_stable_version_contract_is_supported(tmp_path: Path) -> None:
    current = json.loads((ROOT / "VERSION.json").read_text(encoding="utf-8"))
    pyproject_text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    current_pep = re.search(r'(?m)^version\s*=\s*"([^"]+)"', pyproject_text).group(1)
    for relative in (
        "VERSION.json", "pyproject.toml", "TOOLCHAIN_CONTRACT.json", "VISUAL_INSPECTION_MANIFEST.json",
        "DEVELOPMENT_STATUS.json",
        "QUALITY_ENVIRONMENT_STATUS.json", "registries/UI_BLUEPRINT.json", "registries/UI_COMPONENT_REGISTRY.json",
        "registries/VISUAL_INSPECTION_REGISTRY.json", "registries/PLUGIN_APPROVAL_REGISTRY.json",
        "registries/VISUAL_REGRESSION_REGISTRY.json", "registries/VISUAL_APPROVAL_REGISTRY.json",
    ):
        source = ROOT / relative
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        text = source.read_text(encoding="utf-8").replace(current["build"], "2.8.3").replace(current_pep, "2.8.3")
        target.write_text(text, encoding="utf-8")
    version = json.loads((tmp_path / "VERSION.json").read_text(encoding="utf-8"))
    version.update({"version": "2.8.3", "build": "2.8.3", "channel": "stable"})
    (tmp_path / "VERSION.json").write_text(json.dumps(version), encoding="utf-8")
    assert validate(tmp_path) == []


def test_automated_desktop_approval_detects_tampering(tmp_path: Path, monkeypatch) -> None:
    import videobatch_fast.automated_desktop_approval as module

    screenshot = tmp_path / "visual_inspection" / "live_desktop_approval.png"
    screenshot.parent.mkdir(parents=True)
    screenshot.write_bytes(b"x" * 20_000)
    report = {
        "schema_version": 1,
        "build": "2.8.3-rc13",
        "status": "passed",
        "generated_at": "2026-08-02T12:00:00Z",
        "session_type": "x11",
        "screenshot": "visual_inspection/live_desktop_approval.png",
        "screenshot_sha256": hashlib.sha256(screenshot.read_bytes()).hexdigest(),
        "checks": [{"name": "Fenster", "passed": True, "detail": "ok"}],
    }
    (tmp_path / module.REPORT_NAME).write_text(json.dumps(report), encoding="utf-8")
    monkeypatch.setattr(module, "build_label", lambda: "2.8.3-rc13")
    assert module.verify_automated_desktop_approval(tmp_path).valid
    screenshot.write_bytes(b"changed")
    assert module.verify_automated_desktop_approval(tmp_path).status == "invalid"


def test_finalization_entrypoints_are_bound() -> None:
    entry = (ROOT / "videobatch.sh").read_text(encoding="utf-8")
    stable = (ROOT / "stable_release.sh").read_text(encoding="utf-8")
    wrapper = (ROOT / "FINALISIEREN.sh").read_text(encoding="utf-8")
    assert "finalize|finalisieren" in entry
    assert "scripts/finalize_release.py" in entry
    assert "check_visual_approval.py\" --require" in stable
    assert "validate_stable_acceptance.py" in stable
    assert "--acceptance-evidence" in (ROOT / "scripts/finalize_release.py").read_text(encoding="utf-8")
    assert "videobatch.sh\" finalize" in wrapper
