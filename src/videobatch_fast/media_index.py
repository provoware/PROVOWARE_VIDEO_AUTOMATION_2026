"""Offline-first, media-only SQLite index for the three XDG user folders.

A cached listing is *last known state*, not proof that the source still exists.
Only a completed, error-free scan can remove stale entries. All filesystem
access happens in the caller's thread; GUI code must call refresh in a worker.
"""
from __future__ import annotations

import os
import re
import sqlite3
from contextlib import closing
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .paths import cache_dir
from .probe import AUDIO_EXTENSIONS, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS

MEDIA_SUFFIXES = frozenset(AUDIO_EXTENSIONS | IMAGE_EXTENSIONS | VIDEO_EXTENSIONS)
EXCLUDED_DIRECTORY_NAMES = frozenset({
    ".git", ".venv", "venv", "__pycache__", "node_modules",
    "build", "dist", ".tox", ".mypy_cache", ".pytest_cache",
})
XDG_KEYS = {"videos": "XDG_VIDEOS_DIR", "downloads": "XDG_DOWNLOAD_DIR",
            "pictures": "XDG_PICTURES_DIR"}
SCHEMA_VERSION = 1


def _xdg_user_dirs() -> dict[str, Path]:
    config = os.environ.get("XDG_CONFIG_HOME")
    root = Path(config) if config and Path(config).is_absolute() else Path.home() / ".config"
    file = root / "user-dirs.dirs"
    try:
        lines = file.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}
    found: dict[str, Path] = {}
    for line in lines:
        match = re.fullmatch(r'\s*(XDG_(?:VIDEOS|DOWNLOAD|PICTURES)_DIR)="([^"]+)"\s*', line)
        if match is None:
            continue
        key, raw = match.groups()
        # Do not interpret arbitrary shell fragments from configuration files.
        if raw.startswith("$HOME/"):
            path = Path.home() / raw[6:]
        elif raw == "$HOME":
            path = Path.home()
        elif Path(raw).is_absolute():
            path = Path(raw)
        else:
            continue
        found[key] = path
    return found


def media_roots() -> dict[str, Path]:
    """Exactly three configured user roots; never crawl the whole home tree."""
    configured = _xdg_user_dirs()
    home = Path.home()
    pictures = home / "Bilder" if (home / "Bilder").is_dir() else home / "Pictures"
    defaults = {"videos": home / "Videos", "downloads": home / "Downloads",
                "pictures": pictures}
    return {
        name: configured.get(XDG_KEYS[name], default).expanduser().absolute()
        for name, default in defaults.items()
    }


@dataclass(frozen=True)
class IndexedMedium:
    path: Path
    size: int
    mtime_ns: int
    kind: str
    # True until a completed refresh has confirmed the current state.
    last_known: bool = True


@dataclass(frozen=True)
class ScanResult:
    root: str
    added: int = 0
    changed: int = 0
    removed: int = 0
    unchanged: int = 0
    complete: bool = False
    error: str = ""


class MediaIndex:
    def __init__(self, database: Path | None = None,
                 roots: Mapping[str, Path] | None = None,
                 excluded_paths: frozenset[Path] = frozenset()) -> None:
        self.database = Path(database) if database is not None else cache_dir() / "media-index.sqlite3"
        self.roots = dict(media_roots() if roots is None else roots)
        if set(self.roots) != set(XDG_KEYS):
            raise ValueError("Genau Videos, Downloads und Bilder müssen konfiguriert sein")
        self.excluded_paths = frozenset(Path(p).expanduser().absolute() for p in excluded_paths)
        self._lock = threading.Lock()

    def _open_schema(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.database, timeout=10)
        try:
            conn.execute("PRAGMA busy_timeout=10000")
            conn.execute("PRAGMA journal_mode=WAL")
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, SCHEMA_VERSION):
                raise ValueError("Unbekannte Version des Medienindexes")
            conn.execute(
                "CREATE TABLE IF NOT EXISTS media("
                "root TEXT NOT NULL, path TEXT PRIMARY KEY, parent TEXT NOT NULL, "
                "size INTEGER NOT NULL, mtime_ns INTEGER NOT NULL, kind TEXT NOT NULL)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS media_parent ON media(parent)")
            conn.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
            conn.commit()
            return conn
        except (sqlite3.DatabaseError, ValueError, OSError):
            conn.close()
            raise

    def _connect(self) -> sqlite3.Connection:
        self.database.parent.mkdir(parents=True, exist_ok=True)
        try:
            return self._open_schema()
        except sqlite3.DatabaseError:
            # This is only regenerable metadata. Keep the broken database for
            # diagnostics; NEVER delete or modify source media or other files.
            import time
            backup = self.database.with_name(
                f"{self.database.name}.corrupt-{time.time_ns()}"
            )
            if not self.database.is_file():
                raise
            os.replace(self.database, backup)
            for suffix in ("-wal", "-shm"):
                aux = Path(str(self.database) + suffix)
                if aux.exists():
                    os.replace(aux, Path(str(backup) + suffix))
            return self._open_schema()

    def cached_directory(self, directory: Path, *, limit: int = 3000) -> list[IndexedMedium]:
        """Fast read-only display; all entries are treated as unverified."""
        directory = Path(directory).expanduser().absolute()
        if not any(directory == root or root in directory.parents
                   for root in self.roots.values()):
            return []
        with self._lock:
            with closing(self._connect()) as db, db:
                rows = db.execute(
                    "SELECT path,size,mtime_ns,kind FROM media WHERE parent=? "
                    "ORDER BY path COLLATE NOCASE LIMIT ?", (str(directory), max(1, limit))
                ).fetchall()
        return [IndexedMedium(Path(p), size, mtime, kind) for p, size, mtime, kind in rows]

    def refresh(self, *, cancel: threading.Event | None = None) -> list[ScanResult]:
        results = []
        for name in XDG_KEYS:
            if cancel is not None and cancel.is_set():
                break
            results.append(self.refresh_root(name, cancel=cancel))
        return results

    def refresh_root(self, name: str, *, cancel: threading.Event | None = None) -> ScanResult:
        """Do not delete stale entries if unavailable, interrupted or partially unreadable."""
        if name not in self.roots:
            raise ValueError("Unbekannter Medienordner")
        root = self.roots[name]
        if root.is_symlink() or not root.is_dir() or not os.access(root, os.R_OK | os.X_OK):
            return ScanResult(name, error="Medienordner nicht erreichbar")
        with self._lock:
            with closing(self._connect()) as db, db:
                old = {
                    path: (size, mtime)
                    for path, size, mtime in db.execute(
                        "SELECT path,size,mtime_ns FROM media WHERE root=?", (name,)
                    )
                }
                seen: set[str] = set()
                added = changed = unchanged = 0
                folders = [root]
                errors = []
                while folders:
                    if cancel is not None and cancel.is_set():
                        return ScanResult(name, added, changed, 0, unchanged,
                                          error="Prüfung abgebrochen")
                    folder = folders.pop()
                    try:
                        with os.scandir(folder) as listing:
                            for entry in listing:
                                if cancel is not None and cancel.is_set():
                                    return ScanResult(name, added, changed, 0, unchanged,
                                                      error="Prüfung abgebrochen")
                                try:
                                    if entry.is_symlink():
                                        continue
                                    path = Path(entry.path)
                                    if entry.is_dir(follow_symlinks=False):
                                        if entry.name.casefold() not in EXCLUDED_DIRECTORY_NAMES and path not in self.excluded_paths:
                                            folders.append(path)
                                        continue
                                    if (not entry.is_file(follow_symlinks=False) or
                                            path.suffix.lower() not in MEDIA_SUFFIXES):
                                        continue
                                    stat = entry.stat(follow_symlinks=False)
                                except OSError:
                                    errors.append("Ein Eintrag war nicht lesbar")
                                    continue
                                name_path = str(path)
                                seen.add(name_path)
                                identity = (int(stat.st_size), int(stat.st_mtime_ns))
                                if old.get(name_path) == identity:
                                    unchanged += 1
                                    continue
                                kind = ("audio" if path.suffix.lower() in AUDIO_EXTENSIONS
                                        else "image" if path.suffix.lower() in IMAGE_EXTENSIONS
                                        else "video")
                                db.execute(
                                    "INSERT INTO media(root,path,parent,size,mtime_ns,kind)"
                                    "VALUES(?,?,?,?,?,?) ON CONFLICT(path) DO UPDATE SET "
                                    "root=excluded.root,parent=excluded.parent,size=excluded.size,"
                                    "mtime_ns=excluded.mtime_ns,kind=excluded.kind",
                                    (name, name_path, str(folder), *identity, kind)
                                )
                                if name_path in old:
                                    changed += 1
                                else:
                                    added += 1
                    except OSError:
                        errors.append("Ein Unterordner war nicht lesbar")
                removed = 0
                if not errors:
                    stale = set(old) - seen
                    if stale:
                        db.executemany("DELETE FROM media WHERE path=? AND root=?",
                                       ((path, name) for path in stale))
                        removed = len(stale)
                # A failed/incomplete scan leaves all old entries untouched.
                return ScanResult(name, added, changed, removed, unchanged,
                                  complete=not errors,
                                  error="; ".join(sorted(set(errors))))
