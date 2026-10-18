#!/usr/bin/env python3
"""Conservative dependency scope report. Never authorizes test skipping."""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

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


def python_import_audit(test_id: str) -> dict:
    """Find repository-local direct/transitive imports; retain unresolved risks."""
    data = json.loads(POLICY.read_text(encoding="utf-8"))
    spec = data["tests"][test_id]
    pending = list(spec.get("dependency_candidates", []))
    visited: set[str] = set()
    unresolved: set[str] = set()
    dynamic: set[str] = set()
    while pending:
        name = pending.pop()
        if name in visited:
            continue
        visited.add(name)
        path = ROOT / name
        if not path.is_file():
            unresolved.add(name)
            continue
        if path.suffix != ".py":
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeError):
            unresolved.add(name)
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"__import__", "eval", "exec"}:
                dynamic.add(name)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in {"import_module", "spec_from_file_location", "open", "read_text", "read_bytes", "glob", "rglob"}:
                dynamic.add(name)
            if isinstance(node, ast.Import):
                modules = [item.name for item in node.names]
            elif isinstance(node, ast.ImportFrom):
                modules = [("." * node.level) + (node.module or "")]
            else:
                continue
            for module in modules:
                if module.startswith("."):
                    # Relative imports without package resolution remain unknown.
                    dynamic.add(name)
                    continue
                for base in ("scripts", "src"):
                    candidate = ROOT / base / (module.replace(".", "/") + ".py")
                    if candidate.is_file():
                        pending.append(candidate.relative_to(ROOT).as_posix())
    return {"test_id": test_id, "discovered_paths": sorted(visited),
            "unresolved": sorted(unresolved), "dynamic_loaders": sorted(dynamic),
            "complete": False, "scope_reuse_approved": False}


def main() -> int:
    cli = argparse.ArgumentParser(description="Abhängigkeits-Fingerabdruck; nur Hinweis")
    cli.add_argument("test_id")
    cli.add_argument("--imports", action="store_true", help="Import-Abhängigkeiten untersuchen")
    args = cli.parse_args()
    try:
        report = python_import_audit(args.test_id) if args.imports else scoped_report(args.test_id)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, KeyError) as exc:
        print(json.dumps({"status": "blocked", "problem": str(exc),
                          "cache_optimization_enabled": False}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
