from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_canonical_release_evidence_is_the_only_status_source() -> None:
    evidence = json.loads(
        (ROOT / "diagnostics/release_readiness/RELEASE_EVIDENCE.json").read_text(
            encoding="utf-8"
        )
    )

    assert evidence["tests"]["passed"] == 323
    assert evidence["manifest"]["file_count"] == 365

    open_gates = {
        gate["id"]
        for gate in evidence["stable_gates"]
        if gate["status"] != "passed"
    }
    assert open_gates == {
        "physical_kde_x11_wayland",
        "large_media_soak",
    }

    result = subprocess.run(
        [
            sys.executable,
            "diagnostics/release_readiness/generate_from_evidence.py",
            "--check",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_diagnostic_regression_is_not_part_of_release_manifest() -> None:
    manifest = json.loads(
        (ROOT / "RELEASE_MANIFEST.json").read_text(encoding="utf-8")
    )
    paths = {
        item["path"]
        for item in manifest["files"]
        if isinstance(item, dict) and "path" in item
    }
    assert "tests/diagnostics/test_canonical_release_evidence.py" not in paths
