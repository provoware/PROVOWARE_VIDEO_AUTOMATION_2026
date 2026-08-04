from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.verify_portable_reproducibility import inspect_build, verify


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _build_output(root: Path, name: str, payload: bytes = b"portable") -> Path:
    output = root / name
    appdir = output / "VideoBatch_Fast_current.AppDir"
    appdir.mkdir(parents=True)
    app_run = appdir / "AppRun"
    app_run.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    app_run.chmod(0o755)

    portable_tar = output / "VideoBatch_Fast_current-portable.tar.gz"
    portable_run = output / "VideoBatch_Fast_current-portable.run"
    portable_tar.write_bytes(payload)
    portable_run.write_bytes(payload)
    report = {
        "schema_version": 2,
        "status": "passed",
        "appdir": str(appdir),
        "portable_tar": {
            "path": str(portable_tar),
            "sha256": _sha256(payload),
            "size": len(payload),
        },
        "portable_run": {
            "path": str(portable_run),
            "sha256": _sha256(payload),
            "size": len(payload),
        },
    }
    (output / "PORTABLE_BUILD_REPORT.json").write_text(
        json.dumps(report),
        encoding="utf-8",
    )
    return output


def test_verify_uses_build_reports_instead_of_release_name(tmp_path: Path) -> None:
    first = _build_output(tmp_path, "first")
    second = _build_output(tmp_path, "second")
    report = tmp_path / "evidence.json"

    result = verify(first, second, report)

    assert result["status"] == "passed"
    assert result["byte_identical"] is True
    assert report.is_file()


def test_verify_rejects_non_identical_builds(tmp_path: Path) -> None:
    first = _build_output(tmp_path, "first", b"first")
    second = _build_output(tmp_path, "second", b"second")

    with pytest.raises(ValueError, match="nicht byteidentisch"):
        verify(first, second, tmp_path / "evidence.json")


def test_inspect_build_rejects_report_path_escape(tmp_path: Path) -> None:
    output = _build_output(tmp_path, "first")
    report_path = output / "PORTABLE_BUILD_REPORT.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["portable_run"]["path"] = str(tmp_path / "outside.run")
    (tmp_path / "outside.run").write_bytes(b"portable")
    report_path.write_text(json.dumps(report), encoding="utf-8")

    with pytest.raises(ValueError, match="außerhalb des Ausgabeordners"):
        inspect_build(output)
