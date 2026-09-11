import importlib.util
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _release_contract_module():
    path = ROOT / "scripts/release_file_contract.py"
    spec = importlib.util.spec_from_file_location("release_file_contract_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
    assert "from release_file_contract import selected_release_files" in builder
    assert "from release_file_contract import selected_release_files" in validator
    assert "git\", \"-C\", str(root), \"ls-files\"" in contract
    assert '"archive"' in contract
    assert '"matrix-logs"' in contract


def test_git_backed_release_selection_ignores_untracked_workspace_files(
    tmp_path: Path,
) -> None:
    module = _release_contract_module()
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    tracked = tmp_path / "tracked.txt"
    tracked.write_text("tracked\n", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(tmp_path), "add", "tracked.txt"],
        check=True,
    )
    injected = tmp_path / ".github/workflows/ci-injected.yml"
    injected.parent.mkdir(parents=True)
    injected.write_text("name: injected\n", encoding="utf-8")

    selected = {
        path.relative_to(tmp_path).as_posix()
        for path in module.selected_release_files(tmp_path)
    }
    assert selected == {"tracked.txt"}


def test_fresh_extract_without_git_uses_filesystem_contract(tmp_path: Path) -> None:
    module = _release_contract_module()
    extract = tmp_path / "fresh-extract"
    extract.mkdir()
    (extract / "README.md").write_text("ok\n", encoding="utf-8")
    generated = extract / "matrix-logs" / "runtime.log"
    generated.parent.mkdir()
    generated.write_text("ignore\n", encoding="utf-8")

    selected = {
        path.relative_to(extract).as_posix()
        for path in module.selected_release_files(extract)
    }
    assert selected == {"README.md"}


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


def test_obsolete_multi_target_kubuntu_matrix_infrastructure_is_removed() -> None:
    obsolete = (
        ".github/actions/kubuntu-package-cache/action.yml",
        ".github/actions/kubuntu-package-cache/install-and-measure.sh",
        ".github/ci/kubuntu-packages.txt",
        "KUBUNTU_BUILD_MATRIX.json",
        "scripts/build_kubuntu_cache_report.py",
        "scripts/build_kubuntu_matrix_report.py",
        "scripts/write_kubuntu_matrix_status.py",
        "tests/test_kubuntu_cache_warmup.py",
        "tests/test_kubuntu_ci_reports.py",
        "tests/test_rc13_portable_signing_matrix.py",
    )
    assert all(not (ROOT / relative).exists() for relative in obsolete)

    workflow = (ROOT / ".github/workflows/kubuntu-build-matrix.yml").read_text(encoding="utf-8")
    assert "ubuntu-26.04" in workflow
    assert "QT_QPA_PLATFORM: wayland" in workflow
    assert "ubuntu-22.04" not in workflow
    assert "ubuntu-24.04" not in workflow


def test_superseded_historical_documents_are_outside_release_tree() -> None:
    archive = ROOT / "docs/archive/release-history"
    archived = (
        "ANALYSE_AUSGANGSTOOL.md",
        "DESIGN_SYSTEM_ANALYSIS_2_5.md",
        "DOKUMENTATIONS_AUDIT_2026-08-06.md",
        "QUALITY_TOOLCHAIN_2_8_3_RC3.md",
        "QUALITY_TOOLCHAIN_2_8_3_RC4.md",
        "SETUP_2_8_3_RC5.md",
        "VISUAL_LAYOUT_ANALYSIS_2_4.md",
        "FAIL_MEMORY_PASS.md",
        "STABLE_GATE_ITERATION_2.8.3-rc24_2026-08-04.md",
        "VIDEOBATCH_BILDVERGLEICH_CHECKLISTE_2026-08-07.txt",
    )
    assert all((archive / name).is_file() for name in archived)
