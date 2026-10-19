"""Directory-index security and change-detection contracts."""
from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "project_file_index.py"
SPEC = importlib.util.spec_from_file_location("project_file_index", SCRIPT)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def test_create_modify_rename_delete_are_detected(tmp_path: Path) -> None:
    baseline = module.inventory(tmp_path)
    directory = tmp_path / "src"
    directory.mkdir()
    original = directory / "old.py"
    original.write_text("one", encoding="utf-8")
    updated = module.inventory(tmp_path)
    assert module.comparison(baseline, updated)["added"] == ["src/old.py"]

    original.write_text("two", encoding="utf-8")
    newer = module.inventory(tmp_path)
    assert module.comparison(updated, newer)["changed"] == ["src/old.py"]

    renamed = directory / "new.py"
    original.rename(renamed)
    moved = module.inventory(tmp_path)
    report = module.comparison(newer, moved)
    assert report["removed"] == ["src/old.py"]
    assert report["added"] == ["src/new.py"]

    renamed.unlink()
    assert module.comparison(moved, module.inventory(tmp_path))["removed"] == ["src/new.py"]


def test_generated_index_does_not_include_itself(tmp_path: Path) -> None:
    saved = tmp_path / "registries" / "PROJECT_FILE_INDEX.json"
    initial = module.inventory(tmp_path)
    module.write_atomic(saved, initial)
    assert module.inventory(tmp_path) == initial
    assert module.run_once(tmp_path, saved, staged=False, check=True) == 0


def test_git_internal_and_venvs_are_never_indexed(tmp_path: Path) -> None:
    for folder in (".git", ".venv", "dist"):
        p = tmp_path / folder
        p.mkdir()
        (p / "secret").write_text("secret", encoding="utf-8")
    assert module.inventory(tmp_path)["file_count"] == 0


def test_symlink_is_not_followed(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside-index-probe.txt"
    outside.write_text("x", encoding="utf-8")
    try:
        (tmp_path / "link.txt").symlink_to(outside)
        assert module.inventory(tmp_path)["file_count"] == 0
    finally:
        outside.unlink(missing_ok=True)


def test_categories_do_not_claim_release_approval() -> None:
    assert module.category("docs/archive/old.md") == "historical"
    assert module.lifecycle("tests/test_a.py") == "development"


def test_generated_index_is_excluded_from_release_payload(tmp_path: Path) -> None:
    """Avoid RELEASE_MANIFEST -> PROJECT_FILE_INDEX -> RELEASE_MANIFEST cycles."""
    from scripts.release_file_contract import included_release_file

    registry = tmp_path / "registries"
    registry.mkdir()
    generated = registry / "PROJECT_FILE_INDEX.json"
    generated.write_text("{}", encoding="utf-8")
    ordinary = registry / "STABLE_REGISTRY.json"
    ordinary.write_text("{}", encoding="utf-8")
    assert not included_release_file(tmp_path, generated)
    assert included_release_file(tmp_path, ordinary)
