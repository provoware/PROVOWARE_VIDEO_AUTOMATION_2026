#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "SOURCE_RECONCILIATION_CONTRACT.json"


@dataclass(frozen=True)
class ReconciliationResult:
    status: str
    findings: tuple[str, ...]

    @property
    def reconciled(self) -> bool:
        return self.status == "RECONCILED"

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reconciled": self.reconciled,
            "findings": list(self.findings),
        }


def load_contract(path: Path = CONTRACT_PATH) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Source-Reconciliation-Vertrag muss ein JSON-Objekt sein")
    return value


def evaluate(root: Path = ROOT, contract_path: Path = CONTRACT_PATH) -> ReconciliationResult:
    contract = load_contract(contract_path)
    required = contract.get("required_q1_16_source")
    if not isinstance(required, dict):
        return ReconciliationResult("BLOCKED", ("required_q1_16_source fehlt",))

    rel_path = str(required.get("required_file") or "").strip()
    if not rel_path:
        return ReconciliationResult("BLOCKED", ("required_file fehlt",))

    source_path = root / rel_path
    findings: list[str] = []
    if not source_path.is_file():
        findings.append(f"Q1.16-Quelldatei fehlt: {rel_path}")
        return ReconciliationResult("BLOCKED", tuple(findings))

    source = source_path.read_text(encoding="utf-8")
    required_symbols = required.get("required_symbols")
    if not isinstance(required_symbols, list) or not required_symbols:
        findings.append("required_symbols fehlt oder ist leer")
    else:
        for symbol in required_symbols:
            token = str(symbol).strip()
            if token and token not in source:
                findings.append(f"Q1.16-Symbol fehlt: {token}")

    required_stages = required.get("required_stages")
    if not isinstance(required_stages, list) or not required_stages:
        findings.append("required_stages fehlt oder ist leer")
    else:
        for stage in required_stages:
            token = str(stage).strip()
            if token and token not in source:
                findings.append(f"Q1.16-Stage fehlt: {token}")

    policy = contract.get("policy")
    if not isinstance(policy, dict) or policy.get("fail_closed") is not True:
        findings.append("fail_closed muss true sein")
    if not isinstance(policy, dict) or policy.get("q1_17_allowed_only_when_reconciled") is not True:
        findings.append("Q1.17-Gate muss auf reconciled gebunden sein")

    return ReconciliationResult(
        "RECONCILED" if not findings else "BLOCKED",
        tuple(findings),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prüft die kanonische Q1.16-Quellbasis vor Q1.17.")
    parser.add_argument(
        "--expect",
        choices=("RECONCILED", "BLOCKED", "ANY"),
        default="RECONCILED",
        help="Erwarteter Zustand. ANY dient reinen Statusabfragen.",
    )
    parser.add_argument("--json", action="store_true", help="Maschinenlesbare Ausgabe")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = evaluate()
    except Exception as exc:
        print(f"SOURCE_RECONCILIATION=ERROR · {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result.as_dict(), ensure_ascii=False, sort_keys=True))
    else:
        print(f"SOURCE_RECONCILIATION={result.status}")
        for finding in result.findings:
            print(f"- {finding}")

    if args.expect == "ANY":
        return 0
    return 0 if result.status == args.expect else 1


if __name__ == "__main__":
    raise SystemExit(main())
