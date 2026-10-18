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


def test_moved_content_remains_byte_identical_to_original_git_blob() -> None:
    import hashlib
    moves = json.loads((ROOT / "registries/ROOT_MIGRATION_REGISTRY.json").read_text(encoding="utf-8"))["moves"]
    for entry in moves:
        data = (ROOT / entry["to"]).read_bytes()
        digest = hashlib.sha1(f"blob {len(data)}\\0".encode("ascii") + data).hexdigest()
        assert digest == entry["blob_sha"], f"Dateiinhalt unzulässig verändert: {entry['to']}"


def test_root_start_scripts_keep_valid_bash_syntax() -> None:
    import shutil
    import subprocess
    if shutil.which("bash") is None:
        return
    for name in ("STARTEN.sh", "start.sh", "videobatch.sh", "test.sh",
                 "verify_release.sh", "setup.sh", "quality.sh"):
        finished = subprocess.run(
            ["bash", "-n", str(ROOT / name)],
            capture_output=True, text=True, timeout=10, check=False,
        )
        assert finished.returncode == 0, f"{name}: {finished.stderr}"


def test_documented_root_migration_does_not_approve_release() -> None:
    registry = json.loads((ROOT / "registries/ROOT_MIGRATION_REGISTRY.json").read_text(encoding="utf-8"))
    assert registry["stable_release_approved"] is False
    assert "STARTEN.sh" in registry["preserved_entrypoints"]
