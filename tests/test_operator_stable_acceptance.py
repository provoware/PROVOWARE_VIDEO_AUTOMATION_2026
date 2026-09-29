from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import pytest

from scripts.validate_operator_stable_acceptance import OperatorAcceptanceBlocked, validate_operator_acceptance

NOW = datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc)


def _write(root: Path, relative: str, value: dict) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _fixture(root: Path) -> tuple[str, str]:
    candidate = "2.8.3-rc24"
    _write(root, "VERSION.json", {"build": candidate, "version": candidate, "channel": "rc"})
    manifest = root / "RELEASE_MANIFEST.json"
    manifest.write_text('{"schema_version":3,"representation":"compact"}\n', encoding="utf-8")
    digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
    _write(root, "diagnostics/release_readiness/RELEASE_EVIDENCE.json", {
        "product": {"version": candidate},
        "stable_ready": True,
        "stable_gates": [
            {"id": "physical_kubuntu_26_04_wayland", "status": "passed"},
            {"id": "large_media_soak", "status": "passed"},
        ],
    })
    _write(root, "DEVELOPMENT_STATUS.json", {
        "version": candidate, "stable_ready": True, "stable_blockers": [], "approved_quality_report": "report.json",
    })
    _write(root, "report.json", {
        "version": candidate, "status": "passed", "stable_ready": True, "stable_blockers": [],
    })
    _write(root, "diagnostics/release_readiness/KUBUNTU_OPERATOR_ACCEPTANCE_2026-09-29.json", {
        "schema_version": 1, "evidence_type": "operator_baseline_acceptance", "candidate_id": candidate,
        "accepted_at": "2026-09-29T23:50:00+02:00", "result": "passed",
        "gate_id": "physical_kubuntu_26_04_wayland", "statement": "Basis in Ordnung.", "provenance": "project owner",
        "physical_test_reexecuted": False, "formal_kubuntu_26_04_json_claimed": False,
    })
    _write(root, "diagnostics/release_readiness/LONG_RENDER_OPERATOR_ACCEPTANCE_2026-09-29.json", {
        "schema_version": 1, "evidence_type": "operator_long_render_acceptance", "candidate_id": candidate,
        "accepted_at": "2026-09-29T23:50:00+02:00", "result": "passed",
        "gate_id": "large_media_soak", "statement": "Langzeitrender in Ordnung.", "provenance": "project owner",
        "measurements_reconstructed": False, "formal_long_render_json_claimed": False,
    })
    return candidate, digest


def test_operator_acceptance_accepts_explicit_green_contract(tmp_path: Path) -> None:
    candidate, digest = _fixture(tmp_path)
    result = validate_operator_acceptance(tmp_path, candidate, digest, now=NOW)
    assert result["status"] == "passed"
    assert result["acceptance_mode"] == "explicit_operator_signoff"


def test_operator_acceptance_rejects_manifest_drift(tmp_path: Path) -> None:
    candidate, digest = _fixture(tmp_path)
    (tmp_path / "RELEASE_MANIFEST.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(OperatorAcceptanceBlocked, match="geändert"):
        validate_operator_acceptance(tmp_path, candidate, digest, now=NOW)


def test_operator_acceptance_rejects_open_canonical_gate(tmp_path: Path) -> None:
    candidate, digest = _fixture(tmp_path)
    path = tmp_path / "diagnostics/release_readiness/RELEASE_EVIDENCE.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["stable_gates"][1]["status"] = "open"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(OperatorAcceptanceBlocked, match="Stable-Gates"):
        validate_operator_acceptance(tmp_path, candidate, digest, now=NOW)


def test_operator_acceptance_rejects_reconstructed_measurements(tmp_path: Path) -> None:
    candidate, digest = _fixture(tmp_path)
    path = tmp_path / "diagnostics/release_readiness/LONG_RENDER_OPERATOR_ACCEPTANCE_2026-09-29.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["measurements_reconstructed"] = True
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(OperatorAcceptanceBlocked, match="Messwerte"):
        validate_operator_acceptance(tmp_path, candidate, digest, now=NOW)
