import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_release_tools_share_one_file_selection_contract() -> None:
    builder = (ROOT / "scripts/build_release_manifest.py").read_text(
        encoding="utf-8"
    )
    validator = (ROOT / "scripts/validate_release_manifest.py").read_text(
        encoding="utf-8"
    )
    contract = (ROOT / "scripts/release_file_contract.py").read_text(
        encoding="utf-8"
    )
    assert "from release_file_contract import included_release_file" in builder
    assert "from release_file_contract import included_release_file" in validator
    assert '"archive"' in contract
    assert '"matrix-logs"' in contract


def test_release_builders_exclude_historical_archive() -> None:
    portable = (ROOT / "scripts/build_portable_bundle.py").read_text(encoding="utf-8")
    assert '"docs/archive"' in portable


def test_changelog_has_one_title_and_unique_version_headings() -> None:
    content = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert content.count("# Changelog") == 1
    headings = re.findall(r"^## (.+)$", content, flags=re.MULTILINE)
    assert len(headings) == len(set(headings))


def test_temporary_audit_workflow_is_not_part_of_final_tree() -> None:
    assert not (ROOT / ".github/workflows/repository-release-audit.yml").exists()
    assert not (ROOT / ".github/scripts/apply_release_finalization.py").exists()


def test_generated_ci_evidence_is_ignored_and_not_packaged() -> None:
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

    manifest = json.loads(
        (ROOT / "RELEASE_MANIFEST.json").read_text(encoding="utf-8")
    )
    packaged = {
        str(item.get("path", ""))
        for item in manifest.get("files", [])
        if isinstance(item, dict)
    }
    forbidden_files = {
        "CI_PACKAGE_METRICS.json",
        "FFMPEG_TOOLCHAIN.json",
        "RELEASE_LITERAL_HYGIENE.json",
    }
    assert forbidden_files.isdisjoint(packaged)
    assert not any(path.startswith("matrix-logs/") for path in packaged)


def test_release_contract_excludes_local_coverage_reports(tmp_path: Path) -> None:
    from scripts.release_file_contract import included_release_file

    for name in ("coverage.json", "coverage_w20.json", "coverage_w999.json"):
        path = tmp_path / name
        path.write_text("{}\n", encoding="utf-8")
        assert not included_release_file(tmp_path, path)

    product_json = tmp_path / "COVERAGE_POLICY.json"
    product_json.write_text("{}\n", encoding="utf-8")
    assert included_release_file(tmp_path, product_json)
