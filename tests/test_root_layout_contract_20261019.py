"""Source-package and delivered-ZIP root must not overwhelm the user."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ESSENTIAL = {"STARTEN.sh", "README.md", "VERSION.json", "RELEASE_MANIFEST.json"}


def _root_files(directory: Path) -> set[str]:
    return {item.name for item in directory.iterdir() if item.is_file() or item.is_symlink()}


def test_repository_root_has_at_most_eight_files() -> None:
    found = _root_files(ROOT)
    assert len(found) <= 8, f"Im Hauptordner stehen {len(found)} statt höchstens acht Dateien: {sorted(found)}"
    assert ESSENTIAL <= found


def test_release_source_root_has_at_most_eight_files() -> None:
    from scripts.release_file_contract import selected_release_files

    selected = selected_release_files(ROOT)
    root_items = {path.name for path in selected if path.parent == ROOT}
    root_items.add("RELEASE_MANIFEST.json")  # inserted by package_release.py
    assert len(root_items) <= 8, f"Entpacktes Paket wäre überladen: {sorted(root_items)}"
    assert ESSENTIAL <= root_items


def test_extracted_package_root_and_cli_start(tmp_path: Path, monkeypatch) -> None:
    """Build actual ZIP, extract it and verify the isolated CLI entrypoint."""
    import subprocess
    import sys
    import zipfile

    from scripts import package_release

    output = tmp_path / "package.zip"
    monkeypatch.setattr(sys, "argv", ["package_release.py", "--output", str(output)])
    assert package_release.main() == 0
    extracted = tmp_path / "extracted"
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        archive.extractall(extracted)
    package_root = extracted / "VideoBatch_Fast_2.8.3-rc24"
    found = _root_files(package_root)
    assert len(found) <= 8, sorted(found)
    assert ESSENTIAL <= found
    completed = subprocess.run(
        ["bash", str(package_root / "scripts/cli/videobatch.sh"), "help"],
        cwd=package_root, text=True, capture_output=True, timeout=30, check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "VideoBatch Fast" in completed.stdout
