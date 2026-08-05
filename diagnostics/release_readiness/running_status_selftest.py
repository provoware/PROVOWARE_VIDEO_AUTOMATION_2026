#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from selftest import fixture

SCRIPT = Path(__file__).with_name("release_readiness_dashboard.py")


def main() -> int:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        fixture(root, contradictory=False, all_pass=False)
        ci_path = root / "ci.json"
        ci = json.loads(ci_path.read_text(encoding="utf-8"))
        ci["status"] = "running"
        ci["checks"] = [{"name": "matrix", "status": "running"}]
        ci_path.write_text(json.dumps(ci, indent=2) + "\n", encoding="utf-8")

        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(root), "--ci-file", "ci.json"],
            text=True,
            capture_output=True,
        )
        assert proc.returncode == 1, (proc.returncode, proc.stdout, proc.stderr)
        result = json.loads(
            (root / "build/release-readiness/RELEASE_READINESS_STATUS.json").read_text(encoding="utf-8")
        )
        ci_gate = next(gate for gate in result["gates"] if gate["id"] == "ci")
        assert ci_gate["status"] == "running", ci_gate
        assert result["ci"]["raw_status"] == "running", result["ci"]
        assert result["ci"]["status"] == "in_progress", result["ci"]
        assert any(
            item["code"] == "CI_NOT_FINAL" and "running" in item["message"]
            for item in result["findings"]
        ), result["findings"]
    print("RUNNING STATUS SELFTEST PASS · live CI remains precisely LÄUFT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
