#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = ROOT / ".github" / "workflows"
USES_RE = re.compile(r"^\s*(?:-\s*)?uses:\s*([^#\s]+)")
SHA40_RE = re.compile(r"^[0-9a-fA-F]{40}$")


@dataclass(frozen=True, slots=True)
class Finding:
    path: str
    line: int
    uses: str
    message: str


def _is_exempt(value: str) -> bool:
    return value.startswith("./") or value.startswith("docker://")


def inspect_workflows(workflow_dir: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in sorted([*workflow_dir.glob("*.yml"), *workflow_dir.glob("*.yaml")]):
        for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            match = USES_RE.match(raw)
            if not match:
                continue
            value = match.group(1)
            if _is_exempt(value):
                continue
            if "@" not in value:
                findings.append(Finding(path.name, line_no, value, "Externe Action ohne unveränderlichen Commit-SHA."))
                continue
            _, ref = value.rsplit("@", 1)
            if not SHA40_RE.fullmatch(ref):
                findings.append(Finding(path.name, line_no, value, "Externe Action muss auf exakt 40-stelligen Commit-SHA zeigen."))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Prüft externe GitHub Actions auf unveränderliche Commit-SHA-Pins.")
    parser.add_argument("--workflow-dir", type=Path, default=WORKFLOW_DIR)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    findings = inspect_workflows(args.workflow_dir)
    payload = {
        "schema_version": 1,
        "status": "pass" if not findings else "fail",
        "workflow_dir": str(args.workflow_dir),
        "findings": [asdict(item) for item in findings],
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif findings:
        for item in findings:
            print(f"✕ {item.path}:{item.line} · {item.uses} · {item.message}")
    else:
        print("GITHUB-ACTIONS-PINNING: BESTANDEN")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
