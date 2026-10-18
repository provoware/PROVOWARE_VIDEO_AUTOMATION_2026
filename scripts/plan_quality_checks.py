#!/usr/bin/env python3
"""Conservative test-plan adviser; NEVER bypasses a mandatory existing CI gate."""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "registries" / "CHECK_PLANNING_REGISTRY.json"


def load_registry(path: Path = REGISTRY) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError("Unbekannte Prüf-Registry-Version")
    suites = data.get("suites")
    if not isinstance(suites, list) or not suites:
        raise ValueError("Prüf-Registry enthält keine Tests")
    names = [str(row["id"]) for row in suites]
    if len(set(names)) != len(names):
        raise ValueError("Doppelte Prüfkennung")
    if not {"structure", "release_contract", "physical_desktop", "real_long_render"} <= set(names):
        raise ValueError("Pflichtprüfungen fehlen")
    return data


def match(path: str, glob: str) -> bool:
    if glob == "**":
        return True
    # fnmatch treats ** as wildcard over directory separators.
    if glob.startswith("**/") and fnmatch.fnmatch(path, glob[3:]):
        return True
    return fnmatch.fnmatch(path, glob)


def plan(changed: Iterable[str], *, final: bool = False,
         registry: dict[str, Any] | None = None) -> dict[str, Any]:
    data = registry or load_registry()
    paths = sorted(set(str(p) for p in changed))
    if any(p.startswith(("../", "/")) or "/../" in p for p in paths):
        raise ValueError("Unsicherer geänderter Pfad")
    # A completely unknown change cannot be classified safely.
    known_prefixes = (
        ".github/", ".githooks/", "01_START_HIER/", "src/", "scripts/", "tests/", "docs/",
        "resources/", "registries/", "diagnostics/", "debugging/",
        ".release/", "visual_inspection/", "toolchain_wheelhouse/",
    )
    unknown = [p for p in paths if "/" in p and not p.startswith(known_prefixes)]
    if unknown:
        final = True  # Fail closed, not arbitrary skip.
    result: list[dict[str, Any]] = []
    for suite in data["suites"]:
        tier = suite["tier"]
        hit = bool(paths and any(match(p, pattern) for p in paths
                                 for pattern in suite["patterns"]))
        required = tier == "always" or (tier == "final" and final) or final or hit
        result.append({
            "id": suite["id"],
            "decision": "required" if required else "not_affected",
            "reason": "Pflicht/Abnahme" if tier in {"always", "final"} and required
                      else "Betroffene Pfade" if hit
                      else "Finaler/unklarer Kandidat" if final
                      else "Keine betroffenen Pfade",
            "command": suite["command"] if required else None,
            "reusable": bool(suite.get("reusable", False)) if required else False,
        })
    return {
        "schema_version": 1,
        "mode": "final" if final else "iteration",
        "changed": paths, "forced_full_scope": bool(unknown),
        "suites": result,
        "note": "Empfehlung; die bestehenden CI-Required-Checks werden nicht abgeschaltet.",
    }


def git_changed(base: str, head: str, *, root: Path = ROOT) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(root), "diff", "--name-only", "--diff-filter=ACDMRT",
         "--no-renames", f"{base}...{head}"],
        check=True, capture_output=True, text=True, timeout=25,
    )
    return sorted(set(result.stdout.splitlines()))


def evidence_matches(evidence: dict[str, Any], *, commit: str, suite: str,
                     suite_digest: str, inputs_digest: str, environment: str) -> bool:
    """All hashes AND a verified success are required; only noncritical suites eligible.

    This predicate offers *candidate reuse*, never grants CI or release approval.
    """
    required = {
        "status": "success", "commit": commit, "suite": suite,
        "suite_digest": suite_digest,
        "inputs_digest": inputs_digest, "environment": environment,
        "verified": True,
    }
    return bool(commit and suite_digest and inputs_digest and environment
                and all(evidence.get(k) == v for k, v in required.items()))


def content_digest(values: Iterable[str]) -> str:
    payload = "\n".join(sorted(set(values))).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description="Änderungsabhängige Prüfplanung (keine Freigabe)")
    ap.add_argument("--changed", action="append", default=[], metavar="PATH")
    ap.add_argument("--base")
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--final", action="store_true")
    ap.add_argument("--registry", type=Path, default=REGISTRY)
    args = ap.parse_args()
    changes = list(args.changed)
    if args.base:
        changes.extend(git_changed(args.base, args.head))
    if not args.base and not changes:
        ap.error("--changed oder --base ist erforderlich")
    print(json.dumps(plan(changes, final=args.final, registry=load_registry(args.registry)),
                     indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
