#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

EXCLUDE_PARTS = frozenset(
    {
        "__pycache__",
        ".git",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".venv",
        ".quality-venv",
        ".videobatch-venv",
        ".quality-toolchain-backups",
        "Backup",
        "build",
        "dist",
        "htmlcov",
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
        "coverage.json",
        "coverage.xml",
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
