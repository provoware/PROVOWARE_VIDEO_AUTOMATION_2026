#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from selftest import fixture

SCRIPT = Path(__file__).with_name("release_readiness_dashboard.py")


def main() -> int:
    temporary, root, _value = fixture()
    try:
        ci_path = root / "ci.json"
        ci_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "status": "running",
                    "checks": [{"name": "matrix", "status": "running"}],
                    "source": "running-status-selftest",
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--root",
                str(root),
                "--ci-file",
                "ci.json",
            ],
            text=True,
            capture_output=True,
        )
        assert proc.returncode == 1, (proc.returncode, proc.stdout, proc.stderr)
        result = json.loads(
            (root / "build/release-readiness/RELEASE_READINESS_STATUS.json").read_text(
                encoding="utf-8"
            )
        )
        ci_gate = next(gate for gate in result["gates"] if gate["id"] == "ci")
        assert ci_gate["status"] == "running", ci_gate
        assert result["overall_status"] == "yellow", result
        assert any(
            item["code"] == "CI_NOT_FINAL" and "running" in item["message"]
            for item in result["findings"]
        ), result["findings"]
    finally:
        temporary.cleanup()
    print("RUNNING STATUS SELFTEST PASS · CI remains precisely LÄUFT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
