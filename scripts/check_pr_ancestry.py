#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]

PROTECTED_PREFIXES = (
    ".github/actions/",
    ".github/ci/",
    ".github/workflows/",
    "diagnostics/",
    "scripts/",
    "src/",
    "tests/",
)
PROTECTED_FILES = {
    "RELEASE_MANIFEST.json",
    "VERSION.json",
    "pyproject.toml",
    "requirements.lock",
    "requirements-toolchain.lock",
}


class GitContractError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class Violation:
    code: str
    message: str
    paths: tuple[str, ...] = ()
    commits: tuple[str, ...] = ()


def run_git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        errors="replace",
        check=False,
    )
    if check and completed.returncode != 0:
        command = "git " + " ".join(args)
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise GitContractError(f"{command} fehlgeschlagen: {detail}")
    return completed


def verify_commit(value: str, label: str) -> str:
    completed = run_git("rev-parse", "--verify", f"{value}^{{commit}}")
    commit = completed.stdout.strip()
    if not commit:
        raise GitContractError(f"{label} konnte nicht als Commit aufgelöst werden")
    return commit


def is_ancestor(base: str, head: str) -> bool:
    completed = run_git("merge-base", "--is-ancestor", base, head, check=False)
    if completed.returncode not in (0, 1):
        raise GitContractError(completed.stderr.strip() or "merge-base fehlgeschlagen")
    return completed.returncode == 0


def merge_base(base: str, head: str) -> str:
    return run_git("merge-base", base, head).stdout.strip()


def changed_paths(older: str, newer: str) -> set[str]:
    output = run_git("diff", "--name-only", "--diff-filter=ACDMRTUXB", older, newer)
    return {line.strip() for line in output.stdout.splitlines() if line.strip()}


def is_protected(path: str) -> bool:
    return path in PROTECTED_FILES or path.startswith(PROTECTED_PREFIXES)


def patch_id(commit: str) -> str | None:
    patch = run_git(
        "show",
        "--pretty=format:",
        "--binary",
        "--no-ext-diff",
        commit,
    ).stdout
    completed = subprocess.run(
        ["git", "patch-id", "--stable"],
        cwd=ROOT,
        input=patch,
        text=True,
        capture_output=True,
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        raise GitContractError(completed.stderr.strip() or "git patch-id fehlgeschlagen")
    value = completed.stdout.strip()
    return value.split()[0] if value else None


def patch_equivalent_commits(base: str, head: str) -> tuple[str, ...]:
    base_commits = run_git("rev-list", "--no-merges", base).stdout.splitlines()
    base_patch_ids = {
        value
        for commit in base_commits
        if (value := patch_id(commit)) is not None
    }
    duplicates = []
    unique_commits = run_git(
        "rev-list",
        "--reverse",
        "--no-merges",
        f"{base}..{head}",
    ).stdout.splitlines()
    for commit in unique_commits:
        value = patch_id(commit)
        if value is not None and value in base_patch_ids:
            duplicates.append(commit)
    return tuple(duplicates)


def blob_at(commit: str, path: str) -> str | None:
    completed = run_git("rev-parse", "--verify", f"{commit}:{path}", check=False)
    if completed.returncode == 0:
        return completed.stdout.strip()
    return None


def historical_blob_sources(base: str, path: str, blob: str) -> tuple[str, ...]:
    commits = run_git("rev-list", base, "--", path).stdout.splitlines()
    matches = []
    for commit in commits:
        if blob_at(commit, path) == blob:
            matches.append(commit)
    return tuple(matches)


def historical_rollbacks(base: str, head: str) -> dict[str, tuple[str, ...]]:
    rollbacks: dict[str, tuple[str, ...]] = {}
    for path in sorted(changed_paths(base, head)):
        if not is_protected(path):
            continue
        base_blob = blob_at(base, path)
        head_blob = blob_at(head, path)
        if base_blob is None or head_blob is None or base_blob == head_blob:
            continue
        sources = historical_blob_sources(base, path, head_blob)
        if sources:
            rollbacks[path] = sources
    return rollbacks


def evaluate(base: str, head: str) -> dict[str, object]:
    base = verify_commit(base, "Base")
    head = verify_commit(head, "Head")
    common = merge_base(base, head)
    violations: list[Violation] = []

    base_is_ancestor = is_ancestor(base, head)
    if not base_is_ancestor:
        base_changes = changed_paths(common, base)
        head_changes = changed_paths(common, head)
        overlap = tuple(sorted(path for path in base_changes & head_changes if is_protected(path)))
        violations.append(
            Violation(
                code="BASE_NOT_ANCESTOR",
                message=(
                    "Der PR-Head enthält den aktuellen Base-Commit nicht. "
                    "Branch zuerst auf den aktuellen main-Stand bringen."
                ),
                paths=overlap,
            )
        )

    duplicates = patch_equivalent_commits(base, head)
    if duplicates:
        violations.append(
            Violation(
                code="PATCH_ALREADY_IN_BASE",
                message=(
                    "Mindestens ein PR-Commit führt eine bereits patch-identisch "
                    "in main vorhandene Änderung erneut ein."
                ),
                commits=duplicates,
            )
        )

    rollbacks = historical_rollbacks(base, head)
    if rollbacks:
        violations.append(
            Violation(
                code="HISTORICAL_BLOB_ROLLBACK",
                message=(
                    "Geschützte Dateien wurden auf eine ältere, bereits in der "
                    "main-Historie vorhandene Blob-Version zurückgesetzt."
                ),
                paths=tuple(sorted(rollbacks)),
                commits=tuple(
                    sorted({commit for commits in rollbacks.values() for commit in commits})
                ),
            )
        )

    return {
        "schema_version": 1,
        "status": "passed" if not violations else "failed",
        "base": base,
        "head": head,
        "merge_base": common,
        "base_is_ancestor": base_is_ancestor,
        "protected_prefixes": list(PROTECTED_PREFIXES),
        "protected_files": sorted(PROTECTED_FILES),
        "violations": [asdict(item) for item in violations],
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description=(
            "Prüft PR-Abstammung, patch-identische Wiederholungen und historische "
            "Rücknahmen geschützter Produktdateien."
        )
    )
    result.add_argument("--base", required=True, help="Aktueller Base-Commit")
    result.add_argument("--head", required=True, help="Exakter PR-Head-Commit")
    result.add_argument(
        "--report",
        type=Path,
        default=Path("PR_ANCESTRY_REPORT.json"),
        help="Ziel für den maschinenlesbaren JSON-Bericht",
    )
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        report = evaluate(args.base, args.head)
    except GitContractError as exc:
        report = {
            "schema_version": 1,
            "status": "error",
            "error": str(exc),
            "base": args.base,
            "head": args.head,
            "violations": [],
        }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
