"""Development evidence must not rewrite the historical RC24 contract."""
from __future__ import annotations

import json

import pytest

from scripts import validate_release_contract_sync as release_sync


def test_development_evidence_is_separate_and_stable_remains_blocked() -> None:
    result = release_sync.validate()
    assert result["status"] == "development_consistent"
    assert result["stable_ready"] is False
    assert result["historical_release_manifest_files"] == 496
    assert result["manifest_files"] > 496


def test_development_manifest_digest_mismatch_fails_closed(tmp_path, monkeypatch) -> None:
    original = json.loads(release_sync.DEVELOPMENT_PATH.read_text(encoding="utf-8"))
    original["manifest_files_sha256"] = "0" * 64
    altered = tmp_path / "DEVELOPMENT_EVIDENCE.json"
    altered.write_text(json.dumps(original), encoding="utf-8")
    monkeypatch.setattr(release_sync, "DEVELOPMENT_PATH", altered)
    with pytest.raises(release_sync.ContractSyncError, match="Entwicklungsnachweis"):
        release_sync.validate()
