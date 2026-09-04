#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
from pathlib import Path, PurePosixPath

EXCLUDE_PARTS = frozenset(
    {
        "__pycache__",
        ".git",
        ".pytest_cache",
        ".venv",
        ".quality-venv",
        ".videobatch-venv",
        ".quality-toolchain-backups",
        "build",
        "dist",
        "visual_actual",
        "quarantine",
        "keys",
        "diagnostics",
        "actual",
        "diff",
        "archive",
        "matrix-logs",
        "matrix-status",
        "warmup-metrics",
        "release-audit",
    }
)
EXCLUDE_SUFFIXES = frozenset({".pyc", ".pyo", ".pvak", ".coverage"})
EXCLUDE_FILES = frozenset(
    {
        "RELEASE_MANIFEST.json",
        "STABLE_UPDATE_MANIFEST.json",
        "modern_visual_contact_sheet.png",
        ".coverage",
        "CI_PACKAGE_METRICS.json",
        "FFMPEG_TOOLCHAIN.json",
        "RELEASE_LITERAL_HYGIENE.json",
        "KUBUNTU_CACHE_STATUS.json",
        "KUBUNTU_CACHE_STATUS.md",
        "KUBUNTU_MATRIX_SUMMARY.json",
        "KUBUNTU_MATRIX_SUMMARY.md",
        "KUBUNTU_PR_MATRIX_SUMMARY.json",
        "KUBUNTU_PR_MATRIX_SUMMARY.md",
        "cache-inventory.json",
    }
)


class ReleaseFileSelectionError(RuntimeError):
    """Raised when a Git-backed release source set cannot be determined safely."""


def included_release_file(root: Path, path: Path) -> bool:
    """Return whether *path* belongs to the reproducible release source set."""
    if not path.is_file() or path.is_symlink():
        return False
    rel = path.relative_to(root)
    if path.name in EXCLUDE_FILES or path.name.startswith(".coverage."):
        return False
    if path.suffix in EXCLUDE_SUFFIXES:
        return False
    if any(part in EXCLUDE_PARTS for part in rel.parts):
        return False
    if any(part.startswith("dist-matrix-") for part in rel.parts):
        return False
    if path.name.startswith("matrix-status-") and path.suffix == ".json":
        return False
    return True


def _git_tracked_paths(root: Path) -> list[Path]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z", "--cached"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as exc:
        raise ReleaseFileSelectionError(
            f"Git-Dateiliste kann nicht gestartet werden: {exc}"
        ) from exc
    except subprocess.CalledProcessError as exc:
        detail = os.fsdecode(exc.stderr).strip() or f"Exit-Code {exc.returncode}"
        raise ReleaseFileSelectionError(
            f"Git-Dateiliste kann nicht gelesen werden: {detail}"
        ) from exc

    paths: list[Path] = []
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        relative = os.fsdecode(raw)
        pure = PurePosixPath(relative)
        if pure.is_absolute() or ".." in pure.parts:
            raise ReleaseFileSelectionError(
                f"Unsicherer Git-Pfad in Dateiliste: {relative!r}"
            )
        paths.append(root.joinpath(*pure.parts))
    return paths


def selected_release_files(root: Path) -> list[Path]:
    """Return the deterministic release source set for *root*.

    In a Git worktree, the index is authoritative so CI-injected or otherwise
    untracked workspace files cannot alter the release manifest. A real
    Fresh-Extract without ``.git`` falls back to the filesystem contract.
    Git failures inside an existing worktree are fail-closed.
    """
    candidates = (
        _git_tracked_paths(root)
        if (root / ".git").exists()
        else list(root.rglob("*"))
    )
    return sorted(
        (path for path in candidates if included_release_file(root, path)),
        key=lambda path: path.relative_to(root).as_posix(),
    )
