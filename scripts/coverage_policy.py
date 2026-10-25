#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) not in (2, 4):
        print("Nutzung: coverage_policy.py COVERAGE_JSON [MIN_LINE MIN_BRANCH]", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    registry = Path(__file__).resolve().parents[1] / "registries/CODE_QUALITY_REGISTRY.json"
    policy = json.loads(registry.read_text(encoding="utf-8"))["python"]
    min_line = float(sys.argv[2]) if len(sys.argv) == 4 else float(policy["line_coverage_minimum_percent"])
    min_branch = float(sys.argv[3]) if len(sys.argv) == 4 else float(policy["branch_coverage_minimum_percent"])
    payload = json.loads(path.read_text(encoding="utf-8"))
    totals = payload.get("totals", {})
    statements = int(totals.get("num_statements", 0) or 0)
    covered_lines = int(totals.get("covered_lines", 0) or 0)
    branches = int(totals.get("num_branches", 0) or 0)
    covered_branches = int(totals.get("covered_branches", 0) or 0)
    line_percent = (covered_lines / statements * 100.0) if statements else 0.0
    branch_percent = (covered_branches / branches * 100.0) if branches else 100.0
    combined = float(totals.get("percent_covered", 0.0) or 0.0)
    print(
        f"Coveragevertrag · Zeilen {line_percent:.2f}%/{min_line:.2f}% · "
        f"Branches {branch_percent:.2f}%/{min_branch:.2f}% · kombiniert {combined:.2f}%"
    )
    errors: list[str] = []
    if line_percent + 1e-9 < min_line:
        errors.append(f"Zeilenabdeckung {line_percent:.2f}% unterschreitet {min_line:.2f}%")
    if branch_percent + 1e-9 < min_branch:
        errors.append(f"Branch-Abdeckung {branch_percent:.2f}% unterschreitet {min_branch:.2f}%")
    if errors:
        for error in errors:
            print(f"COVERAGE_BLOCKIERT: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
