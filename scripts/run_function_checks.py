#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMANDS = [
    ("Registry", [sys.executable, str(ROOT / "scripts" / "validate_registries.py")]),
    ("Schnellmodi", [sys.executable, str(ROOT / "scripts" / "validate_quick_modes.py")]),
    ("Anwendungssimulation", [sys.executable, str(ROOT / "scripts" / "run_assurance_lab.py")]),
    ("Unit- und Integrationstests", [sys.executable, "-m", "unittest", "discover", "-s", str(ROOT / "tests"), "-v"]),
]


def main() -> int:
    results = []
    for index, (name, command) in enumerate(COMMANDS, start=1):
        print(f"[{index}/{len(COMMANDS)}] {name}")
        started = time.monotonic()
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, errors="replace")
        elapsed = time.monotonic() - started
        results.append({"name": name, "returncode": result.returncode, "elapsed": elapsed, "stdout": result.stdout[-12000:], "stderr": result.stderr[-12000:]})
        print(f"  {'BESTANDEN' if result.returncode == 0 else 'FEHLGESCHLAGEN'} · {elapsed:.2f} s")
        if result.returncode:
            print((result.stderr or result.stdout)[-3000:])
            break
    report = {"schema_version": 1, "passed": all(item["returncode"] == 0 for item in results), "results": results}
    path = ROOT / "diagnostics"
    path.mkdir(exist_ok=True)
    (path / "function_checks_latest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if report["passed"] and len(results) == len(COMMANDS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
