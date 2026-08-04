from pathlib import Path


WORKFLOW = Path(".github/workflows/kubuntu-cache-warmup.yml")
PRODUCTION_WORKFLOW = Path(".github/workflows/kubuntu-build-matrix.yml")
ACTION = Path(".github/actions/kubuntu-package-cache/action.yml")
INSTALLER = Path(
    ".github/actions/kubuntu-package-cache/install-and-measure.sh"
)
PACKAGE_LIST = Path(".github/ci/kubuntu-packages.txt")


def test_warmup_is_main_only_weekly_and_manually_runnable() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "cron: '17 4 * * 1'" in text
    assert "timezone: Europe/Berlin" in text
    assert "workflow_dispatch:" in text
    assert "branches:\n      - main" in text
    assert "if: github.ref == 'refs/heads/main'" in text


def test_shared_action_uses_rotating_scoped_caches() -> None:
    text = ACTION.read_text(encoding="utf-8")

    assert "date -u +%G-W%V" in text
    assert text.count("actions/cache@v4") == 2
    assert "apt-v4-${{ inputs.os }}-" in text
    assert "pip-v4-${{ inputs.os }}-" in text
    assert "steps.fingerprint.outputs.week" in text
    assert "sha256sum .github/ci/kubuntu-packages.txt" in text
    assert "sha256sum requirements-toolchain.lock" in text


def test_warmup_reuses_shared_action_without_full_application_matrix() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "ubuntu-22.04" in text
    assert "ubuntu-24.04" in text
    assert "uses: ./.github/actions/kubuntu-package-cache" in text
    assert "session: cache-warmup" in text
    assert "mode: warmup" in text
    assert "kubuntu_matrix_smoke.sh" not in text


def test_warmup_builds_read_only_cache_inventory_report() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "name: Explain current cache state" in text
    assert "repos/$GITHUB_REPOSITORY/actions/caches?per_page=100" in text
    assert "scripts/build_kubuntu_cache_report.py" in text
    assert "KUBUNTU_CACHE_STATUS.json" in text
    assert "KUBUNTU_CACHE_STATUS.md" in text
    assert "gh api --method DELETE" not in text


def test_production_matrix_uses_same_shared_cache_action() -> None:
    text = PRODUCTION_WORKFLOW.read_text(encoding="utf-8")

    assert text.count("uses: ./.github/actions/kubuntu-package-cache") == 1
    assert "session: ${{ matrix.session }}" in text
    assert "mode: matrix" in text
    assert "apt-get -o Acquire::Retries=5 install" not in text
    assert "scripts/write_kubuntu_matrix_status.py" in text
    assert "scripts/build_kubuntu_matrix_report.py" in text
    assert "CI_PACKAGE_METRICS.json" in text
    assert "Close selected issue after complete success" in text


def test_installer_keeps_minimal_install_and_tool_validation() -> None:
    text = INSTALLER.read_text(encoding="utf-8")

    assert "--no-install-recommends" in text
    assert "Acquire::Retries=5" in text
    assert "command -v ffmpeg" in text
    assert "command -v ffprobe" in text
    assert "command -v Xvfb" in text
    assert "command -v weston" in text
    assert "dpkg-query -W plasma-workspace" in text
    assert "CI_PACKAGE_METRICS.json" in text
    assert "GITHUB_STEP_SUMMARY" in text


def test_apt_simulation_has_its_own_timeout_and_clear_error() -> None:
    text = INSTALLER.read_text(encoding="utf-8")

    bounded_simulation = (
        "timeout --signal=TERM --kill-after=30s 3m \\\n"
        "    apt-get \\\n"
        "      -o Dir::Cache::archives=\"$APT_ARCHIVES\" \\\n"
        "      --simulate install -y --no-install-recommends"
    )
    assert bounded_simulation in text
    assert 'simulate_result="${PIPESTATUS[0]}"' in text
    assert "apt_simulation_success" in text
    assert "Paketvorberechnung abgebrochen" in text
    assert "matrix-logs/apt-simulate.log" in text


def test_warmup_has_read_only_repository_permissions() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "permissions:\n  contents: read\n  actions: read" in text
    assert "contents: write" not in text
    assert "actions: write" not in text
    assert "pull_request_target" not in text


def test_package_contract_remains_explicit_and_minimal() -> None:
    packages = [
        line.strip()
        for line in PACKAGE_LIST.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]

    assert packages == [
        "python3",
        "python3-tk",
        "python3-pip",
        "ffmpeg",
        "xvfb",
        "weston",
        "dbus-x11",
        "plasma-workspace",
    ]
