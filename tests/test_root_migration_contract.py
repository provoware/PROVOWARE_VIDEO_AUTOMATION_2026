"""The documented root migration preserves entrypoints and frozen RC24 evidence."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_renamed_files_and_classification_match() -> None:
    moves = json.loads((ROOT / "registries/ROOT_MIGRATION_REGISTRY.json").read_text(encoding="utf-8"))["moves"]
    labels = json.loads((ROOT / "docs/DOCUMENTATION_CLASSIFICATION.json").read_text(encoding="utf-8"))["documents"]
    for entry in moves:
        assert not (ROOT / entry["from"]).exists()
        assert (ROOT / entry["to"]).is_file()
        assert entry["to"] in labels
        assert entry["from"] not in labels


def test_start_scripts_and_historical_ready_files_exist() -> None:
    for path in ("STARTEN.sh", "start.sh", "videobatch.sh", "test.sh", "VERSION.json", "RELEASE_MANIFEST.json"):
        assert (ROOT / path).is_file()
    evidence = json.loads((ROOT / "diagnostics/release_readiness/RELEASE_EVIDENCE.json").read_text(encoding="utf-8"))
    for record in evidence["release_files"]["ready"]:
        assert (ROOT / record["path"]).is_file()
    assert not evidence["stable_ready"]
