#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).with_name("release_readiness_dashboard.py")


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture(root: Path, *, contradictory: bool, all_pass: bool = False) -> list[Path]:
    ready = root / "START_HIER_save_.md"
    ready.write_text("ok\n", encoding="utf-8")
    manifest_count = 1
    write_json(root / "RELEASE_MANIFEST.json", {
        "build": "2.8.3-rc24",
        "channel": "rc",
        "file_count": manifest_count,
        "files": [{"path": "START_HIER_save_.md"}],
    })
    blockers = [] if all_pass else ["quality", "desktop"]
    write_json(root / "DEVELOPMENT_STATUS.json", {
        "version": "2.8.3-rc24",
        "stable_ready": all_pass,
        "approved_quality_report": "VideoBatch_BUILD_REPORT_save_.json",
        "stable_blockers": blockers,
    })
    external = {
        "ruff_0_16_1": "passed" if all_pass else "not executed",
        "mypy_2_3_0": "passed" if all_pass else "not executed",
        "bandit_1_9_4": "passed" if all_pass else "not executed",
        "pip_audit_2_10_1": "passed" if all_pass else "not executed",
        "physical_kde_x11_wayland": "passed" if all_pass else "required",
        "large_media_soak": "passed" if all_pass else "required",
    }
    write_json(root / "QUALITY_ENVIRONMENT_STATUS.json", {
        "build": "2.8.3-rc24",
        "stable_ready": all_pass,
        "internal_gates": {
            "tests": {"passed": 323 if not contradictory else 253, "failed": 0},
            "release_manifest_files": manifest_count if not contradictory else 4,
        },
        "external_gates": external,
    })
    write_json(root / "RELEASE_FILE_STATUS.json", {
        "version": "2.8.3-rc24",
        "ready": [{"path": "START_HIER_save_.md"}],
        "unfinished": [],
    })
    write_json(root / "VideoBatch_BUILD_REPORT_save_.json", {
        "name": "VideoBatch Fast",
        "version": "2.8.3-rc24",
        "release_channel": "rc",
        "stable_ready": all_pass,
        "release_manifest_files": manifest_count,
        "stable_blockers": blockers,
        "tests": {"passed": 323, "line_coverage_percent": 82.43},
    })
    write_json(root / "ci.json", {
        "status": "pass" if all_pass else "unknown",
        "checks": [{"name": "suite", "status": "pass"}] if all_pass else [],
        "source": "selftest",
    })
    return [path for path in root.iterdir() if path.is_file()]


def run_case(*, contradictory: bool, all_pass: bool, expected_code: int, expected_status: str) -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        inputs = fixture(root, contradictory=contradictory, all_pass=all_pass)
        before = {path.name: sha(path) for path in inputs}
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(root), "--ci-file", "ci.json"],
            text=True,
            capture_output=True,
        )
        assert proc.returncode == expected_code, (proc.returncode, proc.stdout, proc.stderr)
        status_path = root / "build/release-readiness/RELEASE_READINESS_STATUS.json"
        result = json.loads(status_path.read_text(encoding="utf-8"))
        assert result["overall_status"] == expected_status, result
        assert (root / "build/release-readiness/RELEASE_READINESS_DASHBOARD.md").is_file()
        assert (root / "build/release-readiness/RELEASE_READINESS_DASHBOARD.html").is_file()
        after = {path.name: sha(path) for path in inputs}
        assert before == after, "input evidence mutated"


def main() -> int:
    run_case(contradictory=True, all_pass=False, expected_code=2, expected_status="red")
    run_case(contradictory=False, all_pass=False, expected_code=1, expected_status="yellow")
    run_case(contradictory=False, all_pass=True, expected_code=0, expected_status="green")
    print("SELFTEST PASS · red/yellow/green · inputs unchanged · 3 outputs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
