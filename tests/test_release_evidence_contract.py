from __future__ import annotations

import json
from pathlib import Path


def test_canonical_release_evidence_contract() -> None:
    root = Path(__file__).resolve().parents[1]
    evidence_path = root / "diagnostics" / "release_readiness" / "RELEASE_EVIDENCE.json"
    data = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    assert data["tests"]["failed"] == 0
    assert data["manifest"]["file_count"] == 365
    assert data["stable_ready"] is False
    assert len(data["stable_gates"]) == 6


def test_no_transfer_artifacts_present() -> None:
    root = Path(__file__).resolve().parents[1]
    forbidden = (
        root / ".github" / "scripts" / "release-evidence-payload.b64",
        root / ".github" / "scripts" / "release-evidence-trigger",
        root / ".github" / "workflows" / "temporary-apply-release-evidence.yml",
    )
    assert not any(path.exists() for path in forbidden)
