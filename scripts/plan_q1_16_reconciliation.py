from __future__ import annotations

import argparse
import hashlib
import json
import stat
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable

EXPECTED_SHA256 = "ae33da8a0130ea0b3d22799c3d7977a16bac98c36f4bcedfdafc4b82d19a217b"


@dataclass(frozen=True)
class PlanEntry:
    path: str
    archive_sha256: str
    repository_sha256: str | None
    action: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_member_path(name: str) -> PurePosixPath:
    if "\\" in name or "\x00" in name:
        raise ValueError(f"unsafe archive path: {name!r}")
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"unsafe archive path: {name!r}")
    return path


def is_symlink(info: zipfile.ZipInfo) -> bool:
    return stat.S_ISLNK(info.external_attr >> 16)


def normalized_members(archive: zipfile.ZipFile) -> dict[str, zipfile.ZipInfo]:
    files: list[tuple[PurePosixPath, zipfile.ZipInfo]] = []
    for info in archive.infolist():
        path = safe_member_path(info.filename)
        if not path.parts or info.is_dir():
            continue
        if is_symlink(info):
            raise ValueError(f"symlink entries are forbidden: {info.filename}")
        files.append((path, info))
    if not files:
        raise ValueError("archive contains no files")

    first_parts = {path.parts[0] for path, _ in files if len(path.parts) > 1}
    strip_root = len(first_parts) == 1 and all(len(path.parts) > 1 for path, _ in files)
    result: dict[str, zipfile.ZipInfo] = {}
    for path, info in files:
        normalized = PurePosixPath(*path.parts[1:]) if strip_root else path
        key = normalized.as_posix()
        if key in result:
            raise ValueError(f"duplicate normalized archive path: {key}")
        result[key] = info
    return result


def load_scope(path: Path) -> tuple[set[str], set[str]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    added = set(map(str, value.get("added", [])))
    modified = set(map(str, value.get("modified", [])))
    if not added or not modified or added & modified:
        raise ValueError("invalid Q1.16 import scope")
    return added, modified


def build_plan(archive_path: Path, repo_root: Path, scope_path: Path) -> dict[str, object]:
    actual_hash = sha256_file(archive_path)
    if actual_hash != EXPECTED_SHA256:
        raise ValueError(f"archive SHA-256 mismatch: {actual_hash}")

    added, modified = load_scope(scope_path)
    expected = added | modified
    entries: list[PlanEntry] = []
    with zipfile.ZipFile(archive_path) as archive:
        members = normalized_members(archive)
        missing = sorted(expected - set(members))
        if missing:
            raise ValueError("archive misses scoped files: " + ", ".join(missing))

        for relative in sorted(expected):
            archive_hash = sha256_bytes(archive.read(members[relative]))
            target = repo_root / relative
            repository_hash = sha256_file(target) if target.is_file() else None
            declared = "added" if relative in added else "modified"
            if repository_hash == archive_hash:
                action = "identical"
            elif declared == "added" and repository_hash is None:
                action = "add"
            elif declared == "added":
                action = "conflict-existing-added"
            elif repository_hash is None:
                action = "conflict-missing-modified"
            else:
                action = "review-modified"
            entries.append(PlanEntry(relative, archive_hash, repository_hash, action))

    counts: dict[str, int] = {}
    for entry in entries:
        counts[entry.action] = counts.get(entry.action, 0) + 1
    return {
        "status": "PLAN_READY",
        "archive_sha256": actual_hash,
        "scope_files": len(entries),
        "counts": counts,
        "entries": [asdict(entry) for entry in entries],
        "apply_allowed": False,
        "reason": "Plan-only by design; modified files require explicit three-way review to preserve PR #74 changes.",
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--scope", type=Path, default=Path("Q1_16_IMPORT_SCOPE.json"))
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        plan = build_plan(args.archive, args.repo_root, args.scope)
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f"Q1_16_IMPORT_PLAN=BLOCKED · {exc}")
        return 1

    text = json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.write_text(text, encoding="utf-8")
    print("Q1_16_IMPORT_PLAN=READY")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
