#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]

RELEASE_LITERAL = re.compile(
    r"(?<![A-Za-z0-9])v?\d+\.\d+\.\d+(?:-?rc\d+)(?![A-Za-z0-9])",
    re.IGNORECASE,
)
ARTIFACT_LITERAL = re.compile(
    r"\bVideoBatch_Fast_[A-Za-z0-9.+-]+"
    r"(?:\.AppDir|-portable\.(?:run|tar\.gz))\b",
    re.IGNORECASE,
)
ALLOW_MARKER = "release-literal: allow["

SCANNED_PREFIXES = (
    ".github/workflows/",
    "scripts/",
    "src/",
)
SCANNED_ROOT_SUFFIXES = (
    ".py",
    ".sh",
    ".yml",
    ".yaml",
    ".toml",
    ".ini",
    ".cfg",
    ".desktop",
)
AUTHORITATIVE_FILES = {
    "VERSION.json",
    "pyproject.toml",
}
POLICY_IMPLEMENTATION_FILES = {
    "scripts/check_release_literal_hygiene.py",
    "tests/test_release_literal_hygiene.py",
}
SKIPPED_PREFIXES = (
    ".git/",
    ".mypy_cache/",
    ".pytest_cache/",
    ".ruff_cache/",
    "__pycache__/",
    "diagnostics/",
    "dist/",
    "tests/baselines/",
    "toolchain_wheelhouse/",
    "visual_inspection/captures/",
    "work/",
)


@dataclass(frozen=True)
class Violation:
    path: str
    line: int
    kind: str
    literal: str
    excerpt: str


def tracked_files(root: Path) -> list[Path]:
    completed = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if completed.returncode == 0:
        return [
            root / raw.decode("utf-8", errors="surrogateescape")
            for raw in completed.stdout.split(b"\0")
            if raw
        ]
    return [path for path in root.rglob("*") if path.is_file()]


def relative_path(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def is_skipped(relative: str) -> bool:
    if relative in POLICY_IMPLEMENTATION_FILES:
        return True
    return any(
        relative == prefix.rstrip("/") or relative.startswith(prefix)
        for prefix in SKIPPED_PREFIXES
    )


def is_release_sensitive(relative: str) -> bool:
    if relative in AUTHORITATIVE_FILES:
        return False
    if any(relative.startswith(prefix) for prefix in SCANNED_PREFIXES):
        return Path(relative).suffix.lower() in SCANNED_ROOT_SUFFIXES
    if "/" not in relative:
        return Path(relative).suffix.lower() in SCANNED_ROOT_SUFFIXES
    return False


def iter_text_lines(path: Path) -> Iterable[tuple[int, str]]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ()
    return enumerate(text.splitlines(), start=1)


def line_is_non_operational(line: str) -> bool:
    stripped = line.lstrip()
    return not stripped or stripped.startswith(("#", "//"))


def has_valid_allow_marker(line: str) -> bool:
    marker = line.find(ALLOW_MARKER)
    if marker < 0:
        return False
    end = line.find("]", marker + len(ALLOW_MARKER))
    return end > marker + len(ALLOW_MARKER)


def scan_repository(root: Path) -> tuple[list[Violation], dict[str, int]]:
    root = root.resolve()
    violations: list[Violation] = []
    counters = {
        "tracked_files": 0,
        "text_files": 0,
        "release_sensitive_files": 0,
        "skipped_files": 0,
    }

    for path in tracked_files(root):
        counters["tracked_files"] += 1
        try:
            relative = relative_path(root, path)
        except ValueError:
            continue
        if is_skipped(relative):
            counters["skipped_files"] += 1
            continue

        lines = tuple(iter_text_lines(path))
        if not lines:
            continue
        counters["text_files"] += 1
        if not is_release_sensitive(relative):
            continue
        counters["release_sensitive_files"] += 1

        for line_number, line in lines:
            if line_is_non_operational(line) or has_valid_allow_marker(line):
                continue
            for kind, pattern in (
                ("release_identifier", RELEASE_LITERAL),
                ("artifact_filename", ARTIFACT_LITERAL),
            ):
                for match in pattern.finditer(line):
                    violations.append(
                        Violation(
                            path=relative,
                            line=line_number,
                            kind=kind,
                            literal=match.group(0),
                            excerpt=line.strip()[:240],
                        )
                    )
    return violations, counters


def write_report(
    path: Path,
    *,
    root: Path,
    violations: list[Violation],
    counters: dict[str, int],
) -> None:
    report = {
        "schema_version": 1,
        "status": "passed" if not violations else "failed",
        "root": str(root.resolve()),
        "policy": {
            "scanned_prefixes": list(SCANNED_PREFIXES),
            "authoritative_files": sorted(AUTHORITATIVE_FILES),
            "policy_implementation_files": sorted(POLICY_IMPLEMENTATION_FILES),
            "allow_marker": f"{ALLOW_MARKER}reason]",
        },
        "counters": counters,
        "violations": [asdict(item) for item in violations],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Blockiert fest verdrahtete RC-Kennungen und konkrete Portable-"
            "Artefaktnamen in ausführbaren Repository-Bereichen."
        )
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "RELEASE_LITERAL_HYGIENE.json",
    )
    args = parser.parse_args()

    violations, counters = scan_repository(args.root)
    write_report(
        args.report,
        root=args.root,
        violations=violations,
        counters=counters,
    )

    if violations:
        print("Release-Literal-Prüfung fehlgeschlagen:")
        for item in violations:
            print(
                f"- {item.path}:{item.line}: {item.kind} "
                f"{item.literal!r} · {item.excerpt}"
            )
        print(
            "Lösung: Version aus VERSION.json/Build-Bericht ableiten. "
            "Nur zwingende Ausnahmen mit "
            "'release-literal: allow[konkrete Begründung]' markieren."
        )
        return 1

    print(
        "Release-Literal-Prüfung bestanden: "
        f"{counters['release_sensitive_files']} sensible Dateien geprüft."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
