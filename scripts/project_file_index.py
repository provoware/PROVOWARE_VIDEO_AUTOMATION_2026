#!/usr/bin/env python3
"""Deterministic project inventory: read-only checks, atomic writes and Linux watch."""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import select
import stat
import subprocess
import time
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "registries" / "PROJECT_FILE_INDEX.json"
IGNORED_DIRS = frozenset({
    ".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".venv", ".quality-venv", ".videobatch-venv", "build", "dist",
    ".tox", ".idea", ".vscode",
})
IGNORED_FILES = frozenset({".coverage", ".DS_Store"})
IGNORED_PATHS = frozenset({"registries/PROJECT_FILE_INDEX.json"})
EVENT_MASK = (0x00000100 | 0x00000200 | 0x00000040 | 0x00000080
              | 0x00000008 | 0x00000004 | 0x00000400 | 0x00000800
              | 0x00004000)
CREATE_DIR = 0x40000000


def included(relative: str) -> bool:
    parts = Path(relative).parts
    return bool(parts and not any(part in IGNORED_DIRS for part in parts)
                and relative not in IGNORED_PATHS
                and parts[-1] not in IGNORED_FILES
                and not parts[-1].endswith((".pyc", ".pyo")))


def category(path: str) -> str:
    if path.startswith(("docs/archive/", ".release/")):
        return "historical"
    for prefix, name in (
        ("tests/", "tests"), (".github/", "automation"), (".githooks/", "automation"),
        ("scripts/", "development"), ("src/", "application"),
        ("registries/", "registry"), ("resources/", "resources"),
        ("docs/", "documentation"), ("diagnostics/", "diagnostics"),
        ("debugging/", "diagnostics"),
    ):
        if path.startswith(prefix):
            return name
    if path.endswith((".sh", ".desktop")):
        return "entrypoint" if path in {"STARTEN.sh", "resources/desktop/VideoBatch-Fast.desktop"} else "tooling"
    return "project_contract" if path.endswith((".json", ".lock", ".toml")) else "documentation"


def lifecycle(path: str) -> str:
    if path.startswith(("docs/archive/", ".release/")):
        return "historical"
    if path.startswith(("tests/", "scripts/", ".github/")):
        return "development"
    return "active"


def _blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _record(path: str, mode: str, sha: str, size: int | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": path, "mode": mode, "blob_sha1": sha,
        "category": category(path), "lifecycle": lifecycle(path),
    }
    if size is not None:
        result["size"] = size
    return result


def inventory_files(root: Path) -> list[dict[str, Any]]:
    """Working-directory snapshot, also detects as-yet-untracked local files."""
    records: list[dict[str, Any]] = []
    for current, dirs, filenames in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in IGNORED_DIRS
                         and not (Path(current) / d).is_symlink())
        for filename in sorted(filenames):
            target = Path(current) / filename
            relative = target.relative_to(root).as_posix()
            if not included(relative) or target.is_symlink() or not target.is_file():
                continue
            data = target.read_bytes()
            bits = target.stat().st_mode
            mode = "100755" if bits & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH) else "100644"
            records.append(_record(relative, mode, _blob_sha(data)))
    return sorted(records, key=lambda x: x["path"])


def inventory_git_index(root: Path) -> list[dict[str, Any]]:
    """Exactly the staged Git state; avoids mixed staged/unstaged fingerprints."""
    completed = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--stage", "-z"],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15,
    )
    records = []
    for raw in completed.stdout.split(b"\0"):
        if not raw:
            continue
        metadata, path = raw.split(b"\t", 1)
        mode, sha, stage = metadata.decode("ascii").split()
        relative = os.fsdecode(path)
        if stage != "0":
            raise RuntimeError(f"Nicht aufgelöster Git-Konflikt: {relative}")
        if included(relative) and mode in {"100644", "100755"}:
            records.append(_record(relative, mode, sha))
    return sorted(records, key=lambda x: x["path"])


def inventory(root: Path, *, staged: bool = False) -> dict[str, Any]:
    files = inventory_git_index(root) if staged else inventory_files(root)
    counts: Counter[str] = Counter()
    for entry in files:
        parts = Path(entry["path"]).parts
        for index in range(len(parts)):
            counts["/".join(parts[:index]) or "."] += 1
    return {
        "schema_version": 1,
        "scope": "project_structure_not_release_approval",
        "hash_algorithm": "git_blob_sha1",
        "files": files,
        "directories": [
            {"path": key, "file_count_recursive": counts[key]}
            for key in sorted(counts)
        ],
        "file_count": len(files),
    }


def comparison(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    earlier = {item["path"]: item for item in old.get("files", [])}
    latest = {item["path"]: item for item in new["files"]}
    removed = sorted(earlier.keys() - latest.keys())
    added = sorted(latest.keys() - earlier.keys())
    modified = sorted(p for p in earlier.keys() & latest.keys()
                      if earlier[p]["blob_sha1"] != latest[p]["blob_sha1"]
                      or earlier[p]["mode"] != latest[p]["mode"])
    return {"added": added, "removed": removed, "changed": modified}


def read_saved(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError(f"Ungültiger Dateiindex: {path}")
    return payload


def write_atomic(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        temporary.unlink(missing_ok=True)


def run_once(root: Path, path: Path, *, staged: bool, check: bool) -> int:
    current = inventory(root, staged=staged)
    previous = read_saved(path)
    differences = comparison(previous, current)
    same = previous == current
    if check:
        print(json.dumps({"status": "ok" if same else "drift",
                          "file_count": current["file_count"],
                          "changes": differences}, ensure_ascii=False))
        return 0 if same else 1
    if not same:
        write_atomic(path, current)
    print(json.dumps({"status": "updated" if not same else "unchanged",
                      "file_count": current["file_count"],
                      "changes": differences}, ensure_ascii=False))
    return 0


def watch(root: Path, path: Path) -> None:
    """Linux inotify watches directories; overflows always trigger a full rescan."""
    if os.name != "posix":
        raise RuntimeError("Die Live-Überwachung benötigt Linux.")
    libc = ctypes.CDLL(None, use_errno=True)
    fd = libc.inotify_init1(os.O_NONBLOCK | os.O_CLOEXEC)
    if fd < 0:
        raise OSError(ctypes.get_errno(), "inotify_init1 fehlgeschlagen")
    watched: set[str] = set()

    def add_directories() -> None:
        for directory, names, _files in os.walk(root, followlinks=False):
            names[:] = sorted(name for name in names if name not in IGNORED_DIRS
                              and not (Path(directory) / name).is_symlink())
            if libc.inotify_add_watch(fd, os.fsencode(directory), EVENT_MASK) < 0:
                raise OSError(ctypes.get_errno(), f"Ordnerüberwachung: {directory}")
            watched.add(directory)

    try:
        add_directories()
        run_once(root, path, staged=False, check=False)
        while True:
            ready, _, _ = select.select([fd], [], [], 60)
            if ready:
                while True:
                    try:
                        data = os.read(fd, 262144)
                    except BlockingIOError:
                        break
                    if not data:
                        break
                # Debounce file editors that save via temporary renaming.
                time.sleep(0.3)
                add_directories()
            run_once(root, path, staged=False, check=False)
    finally:
        os.close(fd)


def main() -> int:
    parser = argparse.ArgumentParser(description="Datei-/Ordnerindex des Projekts pflegen")
    choice = parser.add_mutually_exclusive_group()
    choice.add_argument("--check", action="store_true", help="Nur prüfen, nie schreiben")
    choice.add_argument("--write", action="store_true", help="Index atomar aktualisieren")
    choice.add_argument("--watch", action="store_true", help="Live bei Dateiänderungen")
    parser.add_argument("--git-index", action="store_true", help="Nur gestagte Git-Dateien")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--index", type=Path, default=None)
    args = parser.parse_args()
    root = args.root.resolve()
    path = args.index or root / "registries" / "PROJECT_FILE_INDEX.json"
    if args.watch:
        if args.git_index:
            parser.error("--watch darf nicht --git-index verwenden")
        try:
            watch(root, path)
        except KeyboardInterrupt:
            return 0
        return 0
    return run_once(root, path, staged=args.git_index,
                    check=not (args.write or args.watch))


if __name__ == "__main__":
    raise SystemExit(main())
