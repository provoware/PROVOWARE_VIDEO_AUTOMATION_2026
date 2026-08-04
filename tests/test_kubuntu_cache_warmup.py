from pathlib import Path


WORKFLOW = Path(".github/workflows/kubuntu-cache-warmup.yml")
PACKAGE_LIST = Path(".github/ci/kubuntu-packages.txt")


def test_warmup_is_main_only_weekly_and_manually_runnable() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "cron: '17 4 * * 1'" in text
    assert "timezone: Europe/Berlin" in text
    assert "workflow_dispatch:" in text
    assert "branches:\n      - main" in text
    assert "if: github.ref == 'refs/heads/main'" in text


def test_warmup_uses_rotating_scoped_caches() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "date -u +%G-W%V" in text
    assert "actions/cache@v4" in text
    assert "apt-v4-${{ matrix.os }}-" in text
    assert "pip-v4-${{ matrix.os }}-" in text
    assert "steps.cache_epoch.outputs.week" in text
    assert "hashFiles('.github/ci/kubuntu-packages.txt')" in text
    assert "hashFiles('requirements-toolchain.lock')" in text


def test_warmup_is_small_and_does_not_replace_full_matrix() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "ubuntu-22.04" in text
    assert "ubuntu-24.04" in text
    assert "x11" not in text.lower()
    assert "wayland" not in text.lower()
    assert "kubuntu_matrix_smoke.sh" not in text
    assert "--no-install-recommends" in text
    assert "command -v ffmpeg" in text
    assert "command -v ffprobe" in text
    assert "command -v Xvfb" in text
    assert "command -v weston" in text
    assert "dpkg-query -W plasma-workspace" in text


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
