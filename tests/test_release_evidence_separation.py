"""Historical RC24 and current integration evidence must never be conflated."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts import validate_release_contract_sync as contract


def test_historical_manifest_is_pinned_original_blob() -> None:
    raw = contract.HISTORICAL_MANIFEST_PATH.read_bytes()
    blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\x00" + raw).hexdigest()
    assert blob == contract.HISTORICAL_MANIFEST_GIT_BLOB
    archived = json.loads(raw)
    assert archived["file_count"] == 496
    assert archived["visual_approval"]["valid"] is False
    original = json.loads(contract.EVIDENCE_PATH.read_text(encoding="utf-8"))
    assert original["manifest"]["file_count"] == 496
    assert original["tests"]["passed"] == 325


def test_historical_manifest_corruption_is_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    forged = tmp_path / "historic.json"
    forged.write_text('{"file_count": 517}\n', encoding="utf-8")
    monkeypatch.setattr(contract, "HISTORICAL_MANIFEST_PATH", forged)
    with pytest.raises(contract.ContractSyncError, match="Historisches RC24-Manifest wurde verändert"):
        contract.validate()


def test_current_candidate_does_not_inherit_historical_release_approval() -> None:
    archived = json.loads(contract.HISTORICAL_MANIFEST_PATH.read_text(encoding="utf-8"))
    current = json.loads(contract.MANIFEST_PATH.read_text(encoding="utf-8"))
    assert archived["file_count"] == 496
    assert current["file_count"] >= 517
    assert current["visual_approval"]["valid"] is False
    with pytest.raises(contract.ContractSyncError):
        contract.validate()
