"""Regressionen für kompakte Release-Manifeste und entpackte ZIP-Strukturen."""
from __future__ import annotations

import hashlib
import json
import stat
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from scripts import package_release


def _fixture_project(root: Path) -> dict:
    (root / "README.md").write_text("# Testpaket\n", encoding="utf-8")
    start = root / "STARTEN.sh"
    start.write_text('#!/usr/bin/env bash\nprintf "PAKET_START_OK\\n"\n', encoding="utf-8")
    start.chmod(0o755)
    (root / "VERSION.json").write_text(
        json.dumps({"build": "2.8.3-rc24"}) + "\n", encoding="utf-8"
    )
    records = package_release._records()
    digest = hashlib.sha256(
        json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": 3,
        "representation": "compact",
        "file_count": len(records),
        "files_sha256": digest,
    }


def test_compact_release_zip_extracts_and_starter_runs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = tmp_path / "source"
    project.mkdir()
    monkeypatch.setattr(package_release, "ROOT", project)
    manifest = _fixture_project(project)
    (project / "RELEASE_MANIFEST.json").write_text(
        json.dumps(manifest) + "\n", encoding="utf-8"
    )
    archive = tmp_path / "release.zip"
    monkeypatch.setattr(sys, "argv", ["package_release.py", "--output", str(archive)])
    assert package_release.main() == 0

    with zipfile.ZipFile(archive) as zf:
        zf.extractall(tmp_path / "unpacked")
        root_paths = {
            Path(info.filename).parts[1]
            for info in zf.infolist()
            if not info.is_dir() and len(Path(info.filename).parts) == 2
        }
    assert len(root_paths) <= 8
    assert {"STARTEN.sh", "README.md", "VERSION.json", "RELEASE_MANIFEST.json"} <= root_paths
    unpacked = tmp_path / "unpacked" / "VideoBatch_Fast_2.8.3-rc24"
    # Bash reads the fixture launcher regardless of the user's umask.
    run = subprocess.run(["bash", str(unpacked / "STARTEN.sh")], capture_output=True, text=True, check=False)
    assert run.returncode == 0
    assert "PAKET_START_OK" in run.stdout
    with zipfile.ZipFile(archive) as zf:
        launcher = next(x for x in zf.infolist() if x.filename.endswith("/STARTEN.sh"))
        assert ((launcher.external_attr >> 16) & stat.S_IXUSR) != 0


def test_stale_compact_manifest_fails_without_creating_zip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = tmp_path / "source"
    project.mkdir()
    monkeypatch.setattr(package_release, "ROOT", project)
    manifest = _fixture_project(project)
    manifest["files_sha256"] = "0" * 64
    (project / "RELEASE_MANIFEST.json").write_text(
        json.dumps(manifest) + "\n", encoding="utf-8"
    )
    archive = tmp_path / "invalid.zip"
    monkeypatch.setattr(sys, "argv", ["package_release.py", "--output", str(archive)])
    with pytest.raises(ValueError, match="nicht mit den Paketdateien"):
        package_release.main()
    assert not archive.exists()


def test_package_root_budget_is_enforced(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = tmp_path / "source"
    project.mkdir()
    monkeypatch.setattr(package_release, "ROOT", project)
    for number in range(7):
        (project / f"extra-{number}.txt").write_text("x", encoding="utf-8")
    manifest = _fixture_project(project)
    (project / "RELEASE_MANIFEST.json").write_text(
        json.dumps(manifest) + "\n", encoding="utf-8"
    )
    archive = tmp_path / "overfull.zip"
    monkeypatch.setattr(sys, "argv", ["package_release.py", "--output", str(archive)])
    with pytest.raises(ValueError, match="höchstens acht Hauptordnerdateien"):
        package_release.main()
    assert not archive.exists()


def test_real_checkout_package_extracts_and_cli_help_runs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Exercise the genuine manifest, files and extracted CLI, not only a fixture."""
    project = Path(__file__).resolve().parents[1]
    assert package_release.ROOT == project
    archive = tmp_path / "checkout-release.zip"
    monkeypatch.setattr(sys, "argv", ["package_release.py", "--output", str(archive)])
    assert package_release.main() == 0

    with zipfile.ZipFile(archive) as zf:
        members = [item.filename for item in zf.infolist() if not item.is_dir()]
        prefixes = {Path(name).parts[0] for name in members}
        assert len(prefixes) == 1
        prefix = next(iter(prefixes))
        root_paths = {
            Path(name).parts[1] for name in members if len(Path(name).parts) == 2
        }
        assert len(root_paths) <= 8
        assert {"STARTEN.sh", "README.md", "VERSION.json", "RELEASE_MANIFEST.json"} <= root_paths
        zf.extractall(tmp_path / "real-unpacked")

    extracted = tmp_path / "real-unpacked" / prefix
    cli = extracted / "scripts" / "cli" / "videobatch.sh"
    assert cli.is_file()
    output = subprocess.run(
        ["bash", str(cli), "help"],
        cwd=extracted, text=True, capture_output=True, check=False, timeout=20,
    )
    assert output.returncode == 0, output.stderr
    assert "VideoBatch Fast" in output.stdout
