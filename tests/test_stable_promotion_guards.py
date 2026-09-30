from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.promote_stable_workspace import copy_canonical_release_evidence, validate_promotion_source


def _write_candidate(root: Path, *, ready: bool) -> None:
    version = {"name": "Produkt", "build": "2.8.3-rc24", "version": "2.8.3-rc24", "channel": "rc"}
    status = {
        "version": version["build"], "stable_ready": ready,
        "stable_blockers": [] if ready else ["physische Abnahme"],
        "approved_quality_report": "report.json",
    }
    report = {
        "version": version["build"], "status": "passed", "stable_ready": ready,
        "stable_blockers": [] if ready else ["Langzeitrender"],
    }
    for name, value in (("VERSION.json", version), ("DEVELOPMENT_STATUS.json", status), ("report.json", report)):
        (root / name).write_text(json.dumps(value), encoding="utf-8")


def test_promotion_refuses_open_stable_evidence(tmp_path: Path) -> None:
    _write_candidate(tmp_path, ready=False)
    with pytest.raises(RuntimeError, match="Stable-Nachweise.*offen"):
        validate_promotion_source(tmp_path)


def test_promotion_derives_stable_build_from_version_contract(tmp_path: Path) -> None:
    _write_candidate(tmp_path, ready=True)
    version, stable_build = validate_promotion_source(tmp_path)
    assert version["build"] == "2.8.3-rc24"
    assert stable_build == "2.8.3"


def test_promotion_copies_only_canonical_release_evidence(tmp_path: Path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    (source / "diagnostics" / "release_readiness").mkdir(parents=True)
    destination.mkdir()
    payload = {"schema_version": 1, "stable_ready": True}
    path = source / "diagnostics" / "release_readiness" / "RELEASE_EVIDENCE.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    target = copy_canonical_release_evidence(source, destination)
    assert json.loads(target.read_text(encoding="utf-8")) == payload
