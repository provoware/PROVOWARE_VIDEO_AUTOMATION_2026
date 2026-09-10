from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_toolchain_wheelhouse as builder  # noqa: E402


def test_preflight_reports_dns_and_missing_pip() -> None:
    failed = subprocess.CompletedProcess([], 1, "pip fehlt")
    with (
        mock.patch.object(builder.subprocess, "run", return_value=failed),
        mock.patch.object(builder.socket, "getaddrinfo", side_effect=builder.socket.gaierror("dns")),
    ):
        errors = builder.preflight("https://pypi.org/simple")
    assert any("pip fehlt" in error for error in errors)
    assert any("DNS-Auflösung" in error for error in errors)


def test_no_legacy_python_orchestrators_remain() -> None:
    for filename in (
        "quality_toolchain.py", "runtime_toolchain.py", "quality_wheelhouse_common.py",
        "runtime_wheelhouse_common.py", "build_quality_wheelhouse.py", "build_runtime_wheelhouse.py",
    ):
        assert not (SCRIPTS / filename).exists()


def test_missing_system_pip_uses_temporary_venv(tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def fake_run(command, **_kwargs):
        calls.append(list(command))
        if command[1:3] == ["-m", "venv"]:
            target = Path(command[-1])
            (target / "bin").mkdir(parents=True, exist_ok=True)
            (target / "bin" / "python").write_text("#!/bin/sh\n", encoding="utf-8")
            return subprocess.CompletedProcess(command, 0, stdout="")
        if command[-3:] == ["-m", "pip", "--version"]:
            return subprocess.CompletedProcess(command, 0, stdout="pip 25.0")
        raise AssertionError(command)

    with (
        mock.patch.object(builder.importlib.util, "find_spec", return_value=None),
        mock.patch.object(builder.tempfile, "gettempdir", return_value=str(tmp_path)),
        mock.patch.object(builder.subprocess, "run", side_effect=fake_run),
    ):
        command, bootstrap = builder.resolve_pip_runner()

    assert bootstrap is not None
    assert command == [str(bootstrap / "bin" / "python"), "-m", "pip"]
    assert any(call[1:3] == ["-m", "venv"] for call in calls)
    builder.safe_remove_tree(bootstrap, allowed_parent=bootstrap.parent)


def test_missing_system_pip_is_repairable_not_network_fatal(tmp_path: Path) -> None:
    output = tmp_path / "wheelhouse"
    argv = ["build_toolchain_wheelhouse.py", "--output", str(output), "--index-url", "https://pypi.org/simple"]
    failed_download = subprocess.CompletedProcess([], 23, stdout="download-test-error")
    with (
        mock.patch.object(sys, "argv", argv),
        mock.patch.dict(
            "os.environ",
            {
                "GITHUB_ACTIONS": "true",
                "VIDEOBATCH_CI_ALLOW_PUBLIC_PYPI": "1",
                "VIDEOBATCH_ALLOW_PUBLIC_PYPI": "1",
            },
            clear=True,
        ),
        mock.patch.object(builder, "preflight", return_value=["pip fehlt; temporäre isolierte pip-Umgebung wird versucht"]),
        mock.patch.object(builder, "resolve_pip_runner", return_value=([sys.executable, "-m", "pip"], None)),
        mock.patch.object(builder.subprocess, "run", return_value=failed_download),
    ):
        assert builder.main() == 23
