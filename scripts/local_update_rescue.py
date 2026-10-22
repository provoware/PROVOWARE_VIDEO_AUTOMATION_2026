#!/usr/bin/env python3
"""Unabhängiger Linux-Erststart: nur Python-Standardbibliothek.

Wird vor dem lokalen Ordnerwechsel neben der Installation kopiert.
Läuft nach einem defekten Update weiter, selbst wenn neue Modulimporte
oder scripts/debug_launcher.py in der Installation nicht mehr funktionieren.
"""
from __future__ import annotations

import ctypes
import errno
import json
import os
import subprocess
import sys
from pathlib import Path


def _sync(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _exchange(a: Path, b: Path) -> None:
    renameat2 = getattr(ctypes.CDLL(None, use_errno=True), "renameat2", None)
    if renameat2 is None:
        raise OSError(errno.ENOSYS, "Atomarer Linux-Verzeichnistausch fehlt")
    renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    renameat2.restype = ctypes.c_int
    if renameat2(-100, os.fsencode(a), -100, os.fsencode(b), 2) != 0:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code), str(a))
    _sync(a.parent)


def _journal(root: Path) -> Path:
    return root.parent / f".{root.name}.update_pending.json"


def _read(root: Path) -> tuple[dict[str, object], Path] | None:
    journal = _journal(root)
    if not journal.exists() and not journal.is_symlink():
        return None
    if journal.is_symlink() or not journal.is_file():
        raise ValueError("Update-Journal ist keine sichere reguläre Datei")
    record = json.loads(journal.read_text(encoding="utf-8"))
    if not isinstance(record, dict) or record.get("schema_version") != 1:
        raise ValueError("Update-Journal ist ungültig")
    if record.get("install_root") != str(root):
        raise ValueError("Update-Journal gehört nicht zu dieser Installation")
    candidate, backup = Path(str(record.get("candidate", ""))), Path(str(record.get("backup", "")))
    if (candidate.name != "candidate" or candidate.parent.parent != root.parent
        or not candidate.parent.name.startswith(".videobatch_update_")
        or backup.parent != root.parent
        or not backup.name.startswith(root.name + ".backup_")):
        raise ValueError("Unzulässige Wiederherstellungspfade")
    if record.get("phase", "exchanging") not in ("exchanging", "awaiting_first_start"):
        raise ValueError("Unbekannte Update-Phase")
    if not root.is_dir() or root.is_symlink():
        raise ValueError("Programmordner ist kein echtes Verzeichnis")
    int(record["old_device"])
    int(record["old_inode"])
    return record, journal


def _restore(root: Path, *, failed_boot: bool = False) -> bool:
    pending = _read(root)
    if pending is None:
        return False
    record, journal = pending
    old_id = (int(record["old_device"]), int(record["old_inode"]))
    now = root.stat()
    if (now.st_dev, now.st_ino) == old_id:
        journal.unlink()
        _sync(journal.parent)
        return False
    if record.get("phase") == "awaiting_first_start" and not failed_boot:
        return False
    for candidate in (Path(str(record["candidate"])), Path(str(record["backup"]))):
        if not candidate.is_dir() or candidate.is_symlink():
            continue
        info = candidate.stat()
        if (info.st_dev, info.st_ino) == old_id:
            _exchange(root, candidate)
            journal.unlink()
            _sync(journal.parent)
            return True
    raise RuntimeError("Vorversion nicht zweifelsfrei auffindbar: kein riskanter Rückfall")


def _start(root: Path, args: list[str], *, retry: bool = False) -> int:
    debug = root / "scripts" / "debug_launcher.py"
    if not debug.is_file() or debug.is_symlink():
        return 127
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join(
            [str(root / "src"), os.environ.get("PYTHONPATH", "")]
        ),
    }
    if retry:
        env["VIDEOBATCH_UPDATE_ROLLBACK_RETRY"] = "1"
    try:
        return int(subprocess.run(
            [sys.executable, str(debug), *args], cwd=root, env=env, check=False
        ).returncode)
    except OSError:
        return 127


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not args:
        print("Benutzung: unabhängiger_starter.py INSTALLATIONSORDNER [Optionen]", file=sys.stderr)
        return 64
    root = Path(args[0]).absolute()
    try:
        _restore(root)
        awaiting = _read(root) is not None
        code = _start(root, args[1:])
        if code == 0:
            # Der echte Debug-Starter bestätigt UI_READY und entfernt das Journal.
            # Ein defektes Programm, das nur 0 zurückgibt, bestätigt KEIN Update.
            return 0 if not awaiting or _read(root) is None else 78
        if awaiting and _read(root) is not None and _restore(root, failed_boot=True):
            print("VideoBatch: Defekter neuer Starter; bestätigte Vorversion wiederhergestellt.", flush=True)
            return _start(root, args[1:], retry=True)
        return code
    except (OSError, RuntimeError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"VideoBatch: Unabhängiger Start blockiert: {exc}", file=sys.stderr)
        return 78


if __name__ == "__main__":
    raise SystemExit(main())
