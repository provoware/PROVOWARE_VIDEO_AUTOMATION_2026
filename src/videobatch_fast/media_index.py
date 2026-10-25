"""Offline-first, media-only SQLite index for the three XDG user folders.

A cached listing is *last known state*, not proof that the source still exists.
Only a completed, error-free scan can remove stale entries. All filesystem
access happens in the caller's thread; GUI code must call refresh in a worker.
"""
from __future__ import annotations

import os
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


from .media_index_preferences import media_roots


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
        except sqlite3.DatabaseError as exc:
            # A busy, read-only or full database is NOT corrupted. In those
            # cases, fail without renaming any valid database files.
            if getattr(exc, "sqlite_errorcode", None) not in (
                sqlite3.SQLITE_NOTADB, sqlite3.SQLITE_CORRUPT
            ):
                raise
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
        if not self.database.is_file():
            return []
        # File dialogs run in the GUI thread. Never wait for a writer or
        # initialize/migrate the schema while showing cached entries.
        try:
            uri = self.database.absolute().as_uri() + "?mode=ro"
            with closing(sqlite3.connect(uri, uri=True, timeout=0.05)) as db:
                db.execute("PRAGMA busy_timeout=50")
                rows = db.execute(
                    "SELECT path,size,mtime_ns,kind FROM media WHERE parent=? "
                    "ORDER BY path COLLATE NOCASE LIMIT ?", (str(directory), max(1, limit))
                ).fetchall()
        except (OSError, sqlite3.Error):
            return []
        # Filter cached paths immediately when exclusions are changed. A
        # cached row is unverified data, never authorization to show a project.
        def allowed(path_text: str) -> bool:
            path = Path(path_text)
            if path.parent != directory:
                return False
            if any(path == excluded or excluded in path.parents
                   for excluded in self.excluded_paths):
                return False
            for root in self.roots.values():
                if root == directory or root in directory.parents:
                    relative = directory.relative_to(root)
                    return not any(
                        part.casefold() in EXCLUDED_DIRECTORY_NAMES
                        for part in relative.parts
                    )
            return False
        return [IndexedMedium(Path(p), size, mtime, kind)
                for p, size, mtime, kind in rows if allowed(p)]

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
                # Stage modifications in one transaction; partial scans roll back.
                db.execute("BEGIN IMMEDIATE")
                seen: set[str] = set()
                added = changed = unchanged = 0
                folders = [root]
                errors = []
                while folders:
                    if cancel is not None and cancel.is_set():
                        db.rollback()
                        return ScanResult(name, 0, 0, 0, unchanged,
                                          error="Prüfung abgebrochen")
                    folder = folders.pop()
                    try:
                        with os.scandir(folder) as listing:
                            for entry in listing:
                                if cancel is not None and cancel.is_set():
                                    db.rollback()
                                    return ScanResult(name, 0, 0, 0, unchanged,
                                                      error="Prüfung abgebrochen")
                                try:
                                    if entry.is_symlink():
                                        continue
                                    path = Path(entry.path)
                                    if entry.is_dir(follow_symlinks=False):
                                        if entry.name.casefold() not in EXCLUDED_DIRECTORY_NAMES and path not in self.excluded_paths:
                                            folders.append(path)
                                        continue
                                    if (path.suffix.lower() not in MEDIA_SUFFIXES or
                                            not entry.is_file(follow_symlinks=False)):
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
                if errors:
                    # Never publish only a fraction of a directory tree.
                    db.rollback()
                    return ScanResult(name, 0, 0, 0, unchanged,
                                      error="; ".join(sorted(set(errors))))
                stale = set(old) - seen
                if stale:
                    db.executemany("DELETE FROM media WHERE path=? AND root=?",
                                   ((path, name) for path in stale))
                db.commit()
                return ScanResult(name, added, changed, len(stale), unchanged,
                                  complete=True)
