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


def test_failed_download_preserves_existing_wheelhouse(tmp_path: Path) -> None:
    output = tmp_path / "wheelhouse"
    output.mkdir()
    sentinel = output / "verified.txt"
    sentinel.write_text("unverändert", encoding="utf-8")
    argv = ["build_toolchain_wheelhouse.py", "--output", str(output), "--index-url", "https://pypi.org/simple"]
    with (
        mock.patch.object(sys, "argv", argv),
        mock.patch.dict("os.environ", {"VIDEOBATCH_ALLOW_PUBLIC_PYPI": "1"}, clear=True),
        mock.patch.object(builder, "preflight", return_value=[]),
        mock.patch.object(builder.subprocess, "run", return_value=subprocess.CompletedProcess([], 1)),
    ):
        assert builder.main() == 1
    assert sentinel.read_text(encoding="utf-8") == "unverändert"
    assert not list(tmp_path.glob(".wheelhouse.build-*"))


def test_publish_replaces_complete_directory_atomically(tmp_path: Path) -> None:
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
