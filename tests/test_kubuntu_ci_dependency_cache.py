from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "ci" / "kubuntu-apt-packages.txt"
INSTALLER = ROOT / "scripts" / "install_kubuntu_ci_dependencies.sh"
ACTION = ROOT / ".github" / "actions" / "prepare-kubuntu-ci" / "action.yml"
WORKFLOWS = (
    ROOT / ".github" / "workflows" / "kubuntu-pr-matrix.yml",
    ROOT / ".github" / "workflows" / "kubuntu-build-matrix.yml",
)


def _packages() -> list[str]:
    return [
        line.split("#", 1)[0].strip()
        for line in MANIFEST.read_text(encoding="utf-8").splitlines()
        if line.split("#", 1)[0].strip()
    ]


def test_minimal_package_profile_excludes_desktop_metapackages() -> None:
    packages = _packages()
    assert packages == sorted(packages)
    assert set(packages) == {
        "dbus-x11",
        "ffmpeg",
        "python3",
        "python3-pip",
        "python3-tk",
        "python3-venv",
        "weston",
        "xvfb",
    }
    assert "plasma-workspace" not in packages


def test_installer_preserves_signature_validation_and_fallback() -> None:
    text = INSTALLER.read_text(encoding="utf-8")
    assert "apt-get" in text
    assert "Acquire::Retries=5" in text
    assert "Dir::Cache::archives" in text
    assert "APT::Keep-Downloaded-Packages=true" in text
    assert "--no-install-recommends" in text
    assert "ffmpeg ffprobe Xvfb weston dbus-launch" in text
    assert "import tkinter" in text
    assert "CI_DEPENDENCY_REPORT.json" in text


def test_composite_action_uses_os_scoped_restore_and_trusted_save() -> None:
    text = ACTION.read_text(encoding="utf-8")
    assert "actions/cache/restore@v4" in text
    assert "actions/cache/save@v4" in text
    assert "inputs.os" in text
    assert "matrix.session" not in text
    assert "inputs.save-cache == 'true'" in text
    assert "hashFiles('ci/kubuntu-apt-packages.txt')" in text
    assert "hashFiles('requirements-toolchain.lock')" in text


def test_both_matrix_workflows_use_the_shared_dependency_action() -> None:
    for workflow in WORKFLOWS:
        text = workflow.read_text(encoding="utf-8")
        assert "uses: ./.github/actions/prepare-kubuntu-ci" in text
        assert "plasma-workspace" not in text
        assert "CI_DEPENDENCY_REPORT.json" in text


def test_manifest_only_changes_trigger_pr_matrix() -> None:
    text = WORKFLOWS[0].read_text(encoding="utf-8")
    assert "- ci/**" in text
    assert "- .github/actions/prepare-kubuntu-ci/**" in text
