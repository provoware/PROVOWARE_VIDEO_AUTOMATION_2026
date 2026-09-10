from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_toolchain_wheelhouse as builder  # noqa: E402


def _assert_headless_user_blocked(tmp_path: Path) -> None:
    argv = ["build_toolchain_wheelhouse.py", "--output", str(tmp_path), "--index-url", "https://pypi.org/simple"]
    with (
        mock.patch.object(sys, "argv", argv),
        mock.patch.dict(os.environ, {"VIDEOBATCH_ALLOW_PUBLIC_PYPI": "1"}, clear=True),
        mock.patch.object(builder, "preflight") as preflight,
    ):
        assert builder.main() == 4
        preflight.assert_not_called()


def test_headless_user_online_request_is_blocked_before_preflight(tmp_path: Path) -> None:
    _assert_headless_user_blocked(tmp_path)


def _assert_incomplete_ci_markers_blocked(tmp_path: Path) -> None:
    argv = ["build_toolchain_wheelhouse.py", "--output", str(tmp_path), "--index-url", "https://pypi.org/simple"]
    for environment in (
        {"GITHUB_ACTIONS": "true"},
        {"VIDEOBATCH_CI_ALLOW_PUBLIC_PYPI": "1"},
        {"GITHUB_ACTIONS": "false", "VIDEOBATCH_CI_ALLOW_PUBLIC_PYPI": "1"},
    ):
        with (
            mock.patch.object(sys, "argv", argv),
            mock.patch.dict(os.environ, environment, clear=True),
            mock.patch.object(builder, "preflight") as preflight,
        ):
            assert builder.main() == 4
            preflight.assert_not_called()


def test_ci_online_exception_requires_explicit_github_actions_marker(tmp_path: Path) -> None:
    _assert_incomplete_ci_markers_blocked(tmp_path)


def _assert_explicit_ci_marker_reaches_preflight(tmp_path: Path) -> None:
    argv = ["build_toolchain_wheelhouse.py", "--output", str(tmp_path), "--index-url", "https://pypi.org/simple"]
    environment = {"GITHUB_ACTIONS": "true", "VIDEOBATCH_CI_ALLOW_PUBLIC_PYPI": "1"}
    with (
        mock.patch.object(sys, "argv", argv),
        mock.patch.dict(os.environ, environment, clear=True),
        mock.patch.object(builder, "preflight", return_value=["DNS-Auflösung fehlgeschlagen: absichtlich"]),
    ):
        assert builder.main() == 5


def test_explicit_ci_online_exception_reaches_preflight(tmp_path: Path) -> None:
    _assert_explicit_ci_marker_reaches_preflight(tmp_path)


def _assert_failed_download_preserves_existing_wheelhouse(tmp_path: Path) -> None:
    tmp_path.mkdir(parents=True, exist_ok=True)
    output = tmp_path / "wheelhouse"
    output.mkdir()
    sentinel = output / "verified.txt"
    sentinel.write_text("unverändert", encoding="utf-8")
    argv = ["build_toolchain_wheelhouse.py", "--output", str(output), "--index-url", "https://pypi.org/simple"]
    with (
        mock.patch.object(sys, "argv", argv),
        mock.patch.dict(
            os.environ,
            {"GITHUB_ACTIONS": "true", "VIDEOBATCH_CI_ALLOW_PUBLIC_PYPI": "1"},
            clear=True,
        ),
        mock.patch.object(builder, "preflight", return_value=[]),
        mock.patch.object(builder.subprocess, "run", return_value=subprocess.CompletedProcess([], 1)),
    ):
        assert builder.main() == 1
    assert sentinel.read_text(encoding="utf-8") == "unverändert"
    assert not list(tmp_path.glob(".wheelhouse.build-*"))


def test_failed_download_preserves_existing_wheelhouse(tmp_path: Path) -> None:
    _assert_failed_download_preserves_existing_wheelhouse(tmp_path)


def _assert_publish_atomic(tmp_path: Path) -> None:
    tmp_path.mkdir(parents=True, exist_ok=True)
    output = tmp_path / "wheelhouse"
    staging = tmp_path / ".wheelhouse.build-test"
    output.mkdir()
    staging.mkdir()
    (output / "old.txt").write_text("alt", encoding="utf-8")
    (staging / "new.txt").write_text("neu", encoding="utf-8")
    builder.publish(staging, output)
    assert not (output / "old.txt").exists()
    assert (output / "new.txt").read_text(encoding="utf-8") == "neu"
    assert not (tmp_path / ".wheelhouse.previous").exists()


def test_publish_replaces_complete_directory_atomically(tmp_path: Path) -> None:
    _assert_publish_atomic(tmp_path)


def _assert_qt_isolated_from_legacy_runtime() -> None:
    runtime_lock = (ROOT / "requirements.lock").read_text(encoding="utf-8")
    qt_lock = (ROOT / "requirements-qt.txt").read_text(encoding="utf-8")
    contract = json.loads((ROOT / "TOOLCHAIN_CONTRACT.json").read_text(encoding="utf-8"))
    runtime_packages = {name.lower() for name in contract["packages"]["runtime"]}
    qt_names = ("PySide6", "PySide6-Addons", "PySide6-Essentials", "shiboken6")

    for name in qt_names:
        assert name.lower() not in runtime_packages
        assert f"{name}==6.11.2" not in runtime_lock
        assert f"{name}==6.11.2" in qt_lock

    assert "-r requirements.lock" in qt_lock


def test_qt_dependencies_are_isolated_from_legacy_runtime() -> None:
    _assert_qt_isolated_from_legacy_runtime()


def _assert_offline_install_flags() -> None:
    toolchain_source = (ROOT / "scripts" / "toolchain.py").read_text(encoding="utf-8")
    for token in ('"--no-index"', '"--find-links"', '"--require-hashes"'):
        assert token in toolchain_source, f"Offline-Installationsflag fehlt: {token}"

    workflow = (ROOT / ".github" / "workflows" / "qt6-phase3-smoke.yml").read_text(encoding="utf-8")
    for token in (
        "PIP_NO_INDEX=1",
        "--no-index",
        "--find-links",
        "--require-hashes",
        "requirements-qt.txt",
        "QT_HASH_MANIFEST",
    ):
        assert token in workflow, f"Qt-Offline-Gate fehlt: {token}"


def test_runtime_and_qt_install_are_no_index_and_hash_pinned() -> None:
    _assert_offline_install_flags()


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="videobatch-offline-gate-") as raw:
        base = Path(raw)
        _assert_headless_user_blocked(base / "headless")
        _assert_incomplete_ci_markers_blocked(base / "markers")
        _assert_explicit_ci_marker_reaches_preflight(base / "authorized")
        _assert_failed_download_preserves_existing_wheelhouse(base / "failure")
        _assert_publish_atomic(base / "atomic")
        _assert_qt_isolated_from_legacy_runtime()
        _assert_offline_install_flags()
    print("OFFLINE_QT_CONSENT_ISOLATION_AND_INSTALL_CONTRACT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
