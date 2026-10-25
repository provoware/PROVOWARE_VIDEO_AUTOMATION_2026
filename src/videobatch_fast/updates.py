from __future__ import annotations

import hashlib
import ctypes
import errno
import json
import os
import sys
import shutil
import subprocess
import tempfile
import time
import zipfile
import uuid
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable

from .update_validation import UpdateCheck, read_manifest, safe_member, validate_update_package
from .safe_io import atomic_write_bytes



@dataclass(frozen=True, slots=True)
class UpdateInstallResult:
    success: bool
    version: str
    message: str
    backup: str = ""
    report: str = ""


def _safe_candidate_target(candidate: Path, relative: PurePosixPath) -> Path:
    target = candidate.joinpath(*relative.parts)
    parent = target.parent
    while parent != candidate.parent:
        if parent.is_symlink():
            raise OSError(f"Update-Ziel liegt unter einem symbolischen Link: {relative}")
        if parent == candidate:
            break
        parent = parent.parent
    if target.is_symlink():
        raise OSError(f"Update-Ziel ist ein symbolischer Link: {relative}")
    resolved_parent = target.parent.resolve()
    if resolved_parent != candidate and candidate not in resolved_parent.parents:
        raise OSError(f"Update-Ziel verlässt den Kandidaten: {relative}")
    return target


def _atomic_write(path: Path, data: bytes, mode: int) -> None:
    atomic_write_bytes(path, data, mode=mode)


def _release_manifest_snapshot(root: Path) -> dict[str, str]:
    manifest_path = root / "RELEASE_MANIFEST.json"
    if not manifest_path.is_file():
        raise OSError("Kandidat enthält kein RELEASE_MANIFEST.json.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    items = manifest.get("files", [])
    if not isinstance(items, list):
        raise OSError("Release-Manifest enthält keine gültige Dateiliste.")
    snapshot: dict[str, str] = {}
    for item in items:
        relative = PurePosixPath(str(item.get("path", "")))
        if not safe_member(str(relative)):
            raise OSError(f"Release-Manifest enthält unsicheren Pfad: {relative}")
        path = root.joinpath(*relative.parts)
        if not path.is_file() or path.is_symlink():
            raise OSError(f"Release-Datei fehlt oder ist ein Link: {relative}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != str(item.get("sha256", "")):
            raise OSError(f"Release-Datei stimmt nicht mit Manifest überein: {relative}")
        snapshot[str(relative)] = digest
    if int(manifest.get("file_count", -1)) != len(snapshot):
        raise OSError("Release-Manifest-Dateizahl stimmt nicht.")
    return snapshot



_TREE_EXCLUDED_PARTS = {"__pycache__", ".git", ".pytest_cache", ".venv", "visual_actual", "quarantine", "keys", "diagnostics", "actual", "diff"}
_TREE_EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".pvak", ".coverage"}


def _candidate_tree_snapshot(root: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(root)
        if any(part in _TREE_EXCLUDED_PARTS for part in relative.parts) or path.suffix in _TREE_EXCLUDED_SUFFIXES:
            continue
        snapshot[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return snapshot

def _write_report(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(path, (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"), 0o600)


def _fsync_directory(path: Path) -> None:
    try:
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:
        pass


def _atomic_exchange_dirs(first: Path, second: Path) -> None:
    """Atomisch zwei vorhandene Verzeichnisse auf demselben Linux-Dateisystem tauschen.

    Anders als zwei aufeinanderfolgende os.replace-Aufrufe lässt RENAME_EXCHANGE
    den Installationsnamen auch bei abruptem Prozessende niemals unbesetzt.
    Auf nicht unterstützten Dateisystemen wird die Aktualisierung blockiert.
    """
    renameat2 = getattr(ctypes.CDLL(None, use_errno=True), "renameat2", None)
    if renameat2 is None:
        raise OSError(errno.ENOSYS, "Atomarer Linux-Verzeichnistausch nicht verfügbar")
    renameat2.argtypes = [
        ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint,
    ]
    renameat2.restype = ctypes.c_int
    at_fdcwd = -100
    rename_exchange = 2
    if renameat2(
        at_fdcwd, os.fsencode(first), at_fdcwd, os.fsencode(second), rename_exchange
    ) != 0:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code), str(first))


def _ensure_independent_starter(install_root: Path) -> Path:
    from .update_installer import _ensure_independent_starter as ensure

    return ensure(install_root)


def _pending_update_path(install_root: Path) -> Path:
    return install_root.parent / f".{install_root.name}.update_pending.json"


def _remove_pending_update(journal: Path) -> None:
    journal.unlink(missing_ok=True)
    _fsync_directory(journal.parent)


def recover_interrupted_update(install_root: Path, *, failed_start: bool = False) -> bool:
    """Vor dem normalen GUI-Start eine unfertige lokale Installation zurückholen.

    Liefert True, wenn der bisherige bestätigte Programmordner wieder
    aktiviert wurde. Fehlen eindeutige Belege, wird nicht blind umbenannt.
    """
    install_root = Path(install_root).resolve()
    journal = _pending_update_path(install_root)
    if not journal.exists():
        return False
    if journal.is_symlink() or not journal.is_file():
        raise OSError("Update-Wiederanlaufdatei ist kein regulärer Eintrag.")
    record = json.loads(journal.read_text(encoding="utf-8"))
    if not isinstance(record, dict) or record.get("schema_version") != 1:
        raise ValueError("Update-Wiederanlaufdatei hat ein ungültiges Format.")
    if record.get("install_root") != str(install_root):
        raise ValueError("Update-Wiederanlaufdatei gehört zu einer anderen Installation.")
    candidate = Path(str(record.get("candidate", "")))
    backup = Path(str(record.get("backup", "")))
    parent = install_root.parent
    if (
        candidate.name != "candidate"
        or candidate.parent.parent != parent
        or not candidate.parent.name.startswith(".videobatch_update_")
        or backup.parent != parent
        or not backup.name.startswith(install_root.name + ".backup_")
    ):
        raise ValueError("Update-Wiederanlaufdatei enthält unzulässige Pfade.")
    phase = record.get("phase", "exchanging")
    if phase not in {"exchanging", "awaiting_first_start"}:
        raise ValueError("Update-Wiederanlaufdatei meldet eine unbekannte Phase.")
    old_id = (int(record["old_device"]), int(record["old_inode"]))
    if not install_root.is_dir() or install_root.is_symlink():
        raise OSError("Programmstartordner fehlt; keine automatische riskante Reparatur.")
    current = install_root.stat()
    if (current.st_dev, current.st_ino) == old_id:
        _remove_pending_update(journal)
        return False
    old_locations = []
    for location in (candidate, backup):
        if location.is_dir() and not location.is_symlink():
            info = location.stat()
            if (info.st_dev, info.st_ino) == old_id:
                old_locations.append(location)
    if phase == "awaiting_first_start" and not failed_start:
        # Ein aktivierter Kandidat darf zuerst EINMAL real starten.
        # Das Journal bleibt bis zur bestätigten Qt-Bereitschaft erhalten.
        if len(old_locations) != 1:
            raise OSError("Letzte bestätigte Installation ist nicht eindeutig gesichert.")
        return False
    for location in old_locations:
        if location.is_dir() and not location.is_symlink():
            info = location.stat()
            if (info.st_dev, info.st_ino) == old_id:
                _atomic_exchange_dirs(install_root, location)
                _fsync_directory(parent)
                _remove_pending_update(journal)
                return True
    raise OSError("Bisherige Installation nicht zweifelsfrei auffindbar; manuelle Diagnose nötig.")


def finish_local_update_first_start(install_root: Path, *, normal_ui_ready: bool) -> str:
    """Lokalen Update-Rückfall erst nach echtem Erststart endgültig freigeben.

    'confirmed': neuer Stand gestartet; Sicherung bleibt für Nutzer erhalten.
    'restored': Start gescheitert; alte Version ist wieder aktiv.
    'none': kein entsprechendes neues Update wartet auf die Bestätigung.
    """
    install_root = Path(install_root).resolve()
    journal = _pending_update_path(install_root)
    if not journal.exists():
        return "none"
    if journal.is_symlink() or not journal.is_file():
        raise OSError("Update-Journal ist kein regulärer Eintrag.")
    record = json.loads(journal.read_text(encoding="utf-8"))
    if not isinstance(record, dict) or record.get("phase") != "awaiting_first_start":
        raise ValueError("Update-Journal enthält keine ausstehende Erststart-Bestätigung.")
    if normal_ui_ready:
        # Wiederanlauf prüft erst Pfade, Gerätekennung und Sicherungs-Inode.
        recover_interrupted_update(install_root)
        if not journal.exists():
            # Der alte Stand war schon wieder aktiviert.
            return "none"
        _remove_pending_update(journal)
        return "confirmed"
    if recover_interrupted_update(install_root, failed_start=True):
        return "restored"
    return "none"


def apply_update_package(package: Path, install_root: Path, current_version: str,
                         progress: Callable[[str, str], None] | None = None,
                         timeout: int = 240) -> UpdateInstallResult:
    from .update_installer import apply_update_package as install

    return install(package, install_root, current_version, progress, timeout, _backend=sys.modules[__name__])
