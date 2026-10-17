#!/usr/bin/env python3
"""Derive candidate-only quality/status from explicit run evidence.

Never modifies the historical RC24 evidence or release status artifacts.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "CANDIDATE_PR240_CI_EVIDENCE.json"
OUTPUT = ROOT / "CANDIDATE_PR240_QUALITY_STATUS.json"


def build() -> dict:
    evidence = json.loads(INPUT.read_text(encoding="utf-8"))
    if evidence.get("kind") != "development_candidate_ci_evidence":
        raise ValueError("Unbekannter Kandidaten-Nachweistyp")
    checks = evidence.get("checks")
    if not isinstance(checks, list) or len(checks) != 8:
        raise ValueError("Acht einzelne Prüfungen sind erforderlich")
    source = evidence["source_commit"]
    if any(item.get("source_commit") != source for item in checks):
        raise ValueError("Die Prüfnachweise müssen denselben Quellcommit betreffen")
    measured = evidence.get("latest_observed_candidate_ci", {})
    regression = measured.get("core_regression", {})
    if regression.get("source_commit") not in (None, measured.get("source_commit")):
        raise ValueError("Widersprüchliche Testherkunft")
    if not isinstance(regression.get("passed"), int) or regression["passed"] <= 0:
        raise ValueError("Keine belegte positive Kern-Testzahl")
    results = {item["name"]: item["conclusion"] for item in checks}
    failures = sorted(name for name, value in results.items() if value != "success")
    return {
        "schema_version": 1,
        "kind": "candidate_only_status",
        "candidate_commit": source,
        "manifest": evidence["source_release_manifest"],
        "historical_release_evidence_separate": True,
        "ci_checks": results,
        "verified_core_partition": {
            "passed": regression["passed"],
            "failed": regression["failed"],
            "job_id": regression["job_id"],
            "workflow_run_id": regression["workflow_run_id"],
        },
        "quality_tools": measured["offline_quality"],
        "blocking_checks": failures,
        "physical_ui_acceptance": "open",
        "release_approved": False,
        "ready_to_merge": False,
        "note": "CI records describe the cited candidate snapshot; never extrapolate to later commits.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = json.dumps(build(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != rendered:
            print("Kandidaten-Qualitätsbericht fehlt oder weicht vom Nachweis ab")
            return 1
        print("Kandidaten-Qualitätsbericht konsistent")
        return 0
    OUTPUT.write_text(rendered, encoding="utf-8")
    print(f"Kandidaten-Qualitätsbericht erzeugt: {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
