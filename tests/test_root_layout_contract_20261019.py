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
