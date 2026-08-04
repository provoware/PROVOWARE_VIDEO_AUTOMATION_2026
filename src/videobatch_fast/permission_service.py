from __future__ import annotations

import os
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DirectoryAccess:
    path: Path
    writable: bool
    repaired: bool = False
    fallback_used: bool = False
    message: str = ""


def downloads_dir() -> Path:
    """Return the user's downloads directory without requiring xdg-user-dir."""
    configured = os.environ.get("XDG_DOWNLOAD_DIR", "").strip()
    if configured:
        return Path(configured.replace("$HOME", str(Path.home()))).expanduser()
    return Path.home() / "Downloads"


def _write_probe(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".videobatch-write-test-", dir=directory)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(b"ok")
            handle.flush()
            os.fsync(handle.fileno())
        Path(name).unlink()
    finally:
        try:
            Path(name).unlink()
        except FileNotFoundError:
            pass


def is_writable_directory(path: Path) -> bool:
    candidate = Path(path).expanduser()
    if candidate.is_symlink():
        return False
    try:
        _write_probe(candidate)
    except OSError:
        return False
    return True


def ensure_writable_directory(path: Path, fallback: Path) -> DirectoryAccess:
    """Return a writable user directory, automatically falling back if needed."""
    requested = Path(path).expanduser()
    if is_writable_directory(requested):
        return DirectoryAccess(requested, True)
    fallback_path = Path(fallback).expanduser()
    try:
        _write_probe(fallback_path)
    except OSError as exc:
        return DirectoryAccess(
            requested,
            False,
            message=f"Weder {requested} noch {fallback_path} sind beschreibbar: {exc}",
        )
    return DirectoryAccess(
        fallback_path,
        True,
        repaired=True,
        fallback_used=True,
        message=f"{requested} war nicht beschreibbar. Sicherer Benutzerordner aktiviert: {fallback_path}",
    )



def _safe_folder_name(value: str, default: str = "VideoBatch_Ausgabe") -> str:
    cleaned = "".join(character for character in str(value).strip() if character.isalnum() or character in " -_()")
    cleaned = " ".join(cleaned.split()).strip(" .")
    return (cleaned[:80] or default)


def create_writable_subdirectory(
    base: Path,
    name: str = "VideoBatch_Ausgabe",
    *,
    fallback_base: Path | None = None,
) -> DirectoryAccess:
    """Create a writable user folder without sudo and without overwriting files.

    The requested base is tried first. If it cannot be prepared, a user-owned
    fallback below Videos or Downloads is used. Existing writable directories
    are reused; conflicting files receive a numbered sibling path.
    """
    folder_name = _safe_folder_name(name)
    fallback = Path(fallback_base).expanduser() if fallback_base else Path.home() / "Videos"
    candidates = [Path(base).expanduser(), fallback, downloads_dir()]
    seen: set[Path] = set()
    errors: list[str] = []
    for parent in candidates:
        if parent in seen:
            continue
        seen.add(parent)
        try:
            parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            errors.append(f"{parent}: {exc}")
            continue
        for index in range(0, 100):
            suffix = "" if index == 0 else f"_{index + 1}"
            target = parent / f"{folder_name}{suffix}"
            if target.exists() and not target.is_dir():
                continue
            try:
                _write_probe(target)
            except OSError as exc:
                errors.append(f"{target}: {exc}")
                continue
            fallback_used = parent != Path(base).expanduser()
            return DirectoryAccess(
                target,
                True,
                repaired=True,
                fallback_used=fallback_used,
                message=(
                    f"Neuer beschreibbarer Ordner erstellt: {target}"
                    if not fallback_used
                    else f"Ausweichordner im Benutzerbereich erstellt: {target}"
                ),
            )
    return DirectoryAccess(
        Path(base).expanduser(),
        False,
        message="Kein beschreibbarer Zielordner konnte erstellt werden. " + "; ".join(errors[-3:]),
    )

def prepare_install_root(requested: Path, fallback: Path) -> DirectoryAccess:
    """Prepare an install root without sudo and quarantine conflicting entries.

    A root-owned or otherwise non-writable child can still be renamed when its
    parent directory is writable. The active path is then recreated for the
    current user. If that is impossible, a separate per-user fallback is used.
    """
    root = Path(requested).expanduser()
    parent = root.parent
    try:
        parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        parent = Path(fallback).expanduser().parent
    if root.exists() or root.is_symlink():
        if root.is_symlink() or not is_writable_directory(root):
            if is_writable_directory(parent):
                quarantine = parent / f".{root.name}.permission-conflict-{time.strftime('%Y%m%dT%H%M%S')}"
                try:
                    os.replace(root, quarantine)
                    _write_probe(root)
                    return DirectoryAccess(
                        root,
                        True,
                        repaired=True,
                        message=f"Nicht beschreibbare Altinstallation wurde sicher nach {quarantine} verschoben.",
                    )
                except OSError:
                    pass
            return ensure_writable_directory(Path(fallback), Path(fallback))
    try:
        _write_probe(root)
        return DirectoryAccess(root, True)
    except OSError:
        return ensure_writable_directory(Path(fallback), Path(fallback))
