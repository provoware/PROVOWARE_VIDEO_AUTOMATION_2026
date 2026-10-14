"""Optional Linux inotify change detection, limited strictly to three media trees.

No third-party dependency and no crawling of other user directories. Events
are merely hints: index.refresh_root() remains the authoritative verifier.
"""
from __future__ import annotations

import ctypes
import ctypes.util
import os
import select
import struct
import sys
from pathlib import Path
from typing import Mapping

from .media_index import EXCLUDED_DIRECTORY_NAMES, MEDIA_SUFFIXES

_IN_MODIFY = 0x00000002
_IN_CLOSE_WRITE = 0x00000008
_IN_MOVED_FROM = 0x00000040
_IN_MOVED_TO = 0x00000080
_IN_CREATE = 0x00000100
_IN_DELETE = 0x00000200
_IN_DELETE_SELF = 0x00000400
_IN_MOVE_SELF = 0x00000800
_IN_Q_OVERFLOW = 0x00004000
_IN_IGNORED = 0x00008000
_IN_ISDIR = 0x40000000
_IN_ONLYDIR = 0x01000000
_IN_DONT_FOLLOW = 0x02000000
_MASK = (_IN_MODIFY | _IN_CLOSE_WRITE | _IN_MOVED_FROM |
         _IN_MOVED_TO | _IN_CREATE | _IN_DELETE | _IN_DELETE_SELF |
         _IN_MOVE_SELF | _IN_ONLYDIR | _IN_DONT_FOLLOW)
_HEADER = struct.Struct("iIII")


class MediaWatcher:
    """Use in a worker thread. Close on every shutdown or configuration change."""

    def __init__(self, roots: Mapping[str, Path],
                 excluded_paths: frozenset[Path] = frozenset(),
                 max_watches: int = 2048) -> None:
        self.roots = {k: Path(v).absolute() for k, v in roots.items()}
        self.excluded_paths = frozenset(Path(p).absolute() for p in excluded_paths)
        self.max_watches = max(1, int(max_watches))
        self.coverage_limited = False
        self.topology_changed = False
        self._wd_to_root: dict[int, str] = {}
        self._libc = None
        self._fd = -1
        if not sys.platform.startswith("linux"):
            self.coverage_limited = True
            return
        library = ctypes.util.find_library("c")
        if library is None:
            self.coverage_limited = True
            return
        self._libc = ctypes.CDLL(library, use_errno=True)
        self._libc.inotify_init1.argtypes = [ctypes.c_int]
        self._libc.inotify_init1.restype = ctypes.c_int
        self._libc.inotify_add_watch.argtypes = [
            ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32
        ]
        self._libc.inotify_add_watch.restype = ctypes.c_int
        self.reset()

    def reset(self) -> None:
        self.close()
        self._wd_to_root.clear()
        self.coverage_limited = False
        self.topology_changed = False
        if self._libc is None:
            self.coverage_limited = True
            return
        fd = self._libc.inotify_init1(os.O_NONBLOCK | os.O_CLOEXEC)
        if fd < 0:
            self.coverage_limited = True
            return
        self._fd = fd
        for name, root in self.roots.items():
            if root.is_symlink() or not root.is_dir():
                self.coverage_limited = True
                continue
            pending = [root]
            while pending:
                directory = pending.pop()
                if len(self._wd_to_root) >= self.max_watches:
                    self.coverage_limited = True
                    return
                try:
                    if directory.is_symlink() or directory in self.excluded_paths:
                        continue
                    wd = self._libc.inotify_add_watch(
                        self._fd, os.fsencode(directory), _MASK
                    )
                    if wd < 0:
                        self.coverage_limited = True
                        continue
                    self._wd_to_root[wd] = name
                    with os.scandir(directory) as entries:
                        for entry in entries:
                            if (entry.is_symlink() or
                                    entry.name.casefold() in EXCLUDED_DIRECTORY_NAMES):
                                continue
                            if entry.is_dir(follow_symlinks=False):
                                child = Path(entry.path)
                                if child not in self.excluded_paths:
                                    pending.append(child)
                except OSError:
                    self.coverage_limited = True

    def changed(self, timeout: float = 1.0) -> set[str]:
        """Return possibly affected root names; never claim certainty from events."""
        if self._fd < 0:
            return set()
        try:
            readable, _, _ = select.select([self._fd], [], [], max(0.0, timeout))
            if not readable:
                return set()
            data = os.read(self._fd, 262144)
        except (OSError, ValueError):
            self.coverage_limited = True
            return set(self.roots)
        changed: set[str] = set()
        offset = 0
        while offset + _HEADER.size <= len(data):
            wd, mask, _cookie, size = _HEADER.unpack_from(data, offset)
            raw_name = data[offset + _HEADER.size:offset + _HEADER.size + size]
            filename = os.fsdecode(raw_name.split(b"\x00", 1)[0])
            offset += _HEADER.size + size
            if mask & _IN_Q_OVERFLOW:
                self.coverage_limited = True
                return set(self.roots)
            name = self._wd_to_root.get(wd)
            if name and mask & (_MASK | _IN_IGNORED):
                directory_event = bool(mask & _IN_ISDIR)
                if directory_event or not filename or Path(filename).suffix.lower() in MEDIA_SUFFIXES:
                    changed.add(name)
                    if directory_event or mask & _IN_IGNORED:
                        self.topology_changed = True
        return changed

    def close(self) -> None:
        if self._fd >= 0:
            os.close(self._fd)
            self._fd = -1

    def __enter__(self) -> "MediaWatcher":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()
