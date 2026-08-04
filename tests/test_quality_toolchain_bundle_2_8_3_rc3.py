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
