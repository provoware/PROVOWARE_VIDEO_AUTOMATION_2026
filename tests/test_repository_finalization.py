from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def test_release_builders_exclude_historical_archive() -> None:
    manifest = (ROOT / "scripts/build_release_manifest.py").read_text(encoding="utf-8")
    portable = (ROOT / "scripts/build_portable_bundle.py").read_text(encoding="utf-8")
    assert '"archive"' in manifest
    assert '"docs/archive"' in portable


def test_changelog_has_one_title_and_unique_version_headings() -> None:
    content = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert content.count("# Changelog") == 1
    headings = re.findall(r"^## (.+)$", content, flags=re.MULTILINE)
    assert len(headings) == len(set(headings))


def test_temporary_audit_workflow_is_not_part_of_final_tree() -> None:
    assert not (ROOT / ".github/workflows/repository-release-audit.yml").exists()
    assert not (ROOT / ".github/scripts/apply_release_finalization.py").exists()
