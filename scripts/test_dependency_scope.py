#!/usr/bin/env python3
"""Conservative dependency scope report. Never authorizes test skipping."""
from __future__ import annotations

import argparse
import json

from project_file_index import ROOT, snapshot
from sha256_contract import dependency_digest, digest_json

POLICY = ROOT / "registries" / "TEST_EVIDENCE_POLICY.json"


def scoped_report(test_id: str, files: dict | None = None) -> dict:
    data = json.loads(POLICY.read_text(encoding="utf-8"))
    tests = data.get("tests", {})
    if test_id not in tests:
        raise ValueError(f"Unbekannte Prüfung: {test_id}")
    inventory = snapshot() if files is None else files
    # Phase 2: explicit dependency paths; absent or incomplete graphs remain
    # advisory and deliberately fall back to the FULL file inventory.
    spec = tests[test_id]
    declared = spec.get("dependency_paths")
    complete = spec.get("dependencies_reviewed") is True
    if complete:
        if not isinstance(declared, list) or not declared:
            raise ValueError("Abhängigkeiten als vollständig markiert, aber nicht definiert")
        paths = declared
    else:
        paths = sorted(inventory)
    digest = dependency_digest(inventory, paths)
    return {"test_id": test_id, "source_digest": digest,
            "scope": "reviewed" if complete else "full_tree_fallback",
            "reusable_for_release": False,
            "cache_optimization_enabled": False,
            "dependency_count": len(paths)}


def main() -> int:
    cli = argparse.ArgumentParser(description="Abhängigkeits-Fingerabdruck; nur Hinweis")
    cli.add_argument("test_id")
    args = cli.parse_args()
    try:
        print(json.dumps(scoped_report(args.test_id), ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, KeyError) as exc:
        print(json.dumps({"status": "blocked", "problem": str(exc),
                          "cache_optimization_enabled": False}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
