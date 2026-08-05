import re
import subprocess
from pathlib import Path

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


def test_generated_ci_evidence_is_ignored_and_not_committed() -> None:
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")
    required_patterns = {
        "/CI_PACKAGE_METRICS.json",
        "/FFMPEG_TOOLCHAIN.json",
        "/RELEASE_LITERAL_HYGIENE.json",
        "/matrix-status-*.json",
        "/matrix-logs/",
        "/dist-matrix-*/",
    }
    assert required_patterns <= set(ignored.splitlines())

    tracked = set(
        subprocess.run(
            ["git", "ls-files"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
    )
    forbidden_files = {
        "CI_PACKAGE_METRICS.json",
        "FFMPEG_TOOLCHAIN.json",
        "RELEASE_LITERAL_HYGIENE.json",
    }
    assert forbidden_files.isdisjoint(tracked)
    assert not any(path.startswith("matrix-logs/") for path in tracked)
