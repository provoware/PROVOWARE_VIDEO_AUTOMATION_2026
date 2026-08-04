#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from videobatch_fast.assurance import run_scenarios
from videobatch_fast.paths import state_dir
from videobatch_fast.safe_io import atomic_write_json


def main() -> int:
    results = run_scenarios()
    expected = {"pass", "blocked", "healed", "safe_failure"}
    failed = [result for result in results if result.status not in expected]
    report_dir = state_dir() / "assurance"
    report_dir.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": 1, "passed": len(results) - len(failed), "failed": len(failed), "results": [asdict(result) for result in results]}
    atomic_write_json(report_dir / "latest.json", payload)
    print(f"ANWENDUNGSSIMULATION: {len(results)-len(failed)}/{len(results)} erwartungsgemäß")
    for result in results:
        print(f"{'✓' if result.status in expected else '✕'} {result.scenario_id}: {result.status} · {result.message}")
        print(f"  Lösung: {result.solution}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
