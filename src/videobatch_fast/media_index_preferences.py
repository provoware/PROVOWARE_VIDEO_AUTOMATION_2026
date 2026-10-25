"""Validated, atomic local configuration for media-index folder exclusions."""
from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Iterable, Mapping


def exclusions_path() -> Path:
    supplied = os.environ.get("XDG_CONFIG_HOME", "")
    base = Path(supplied) if supplied and Path(supplied).is_absolute() else Path.home() / ".config"
    return base / "provoware" / "videobatch" / "media-exclusions.json"


def validate_exclusions(paths: Iterable[str | Path], roots: Mapping[str, Path]) -> tuple[Path, ...]:
    """Accept only strict descendants of monitored roots, never arbitrary disks."""
    roots_abs = [Path(root).expanduser().absolute() for root in roots.values()]
    selected: set[Path] = set()
    for source in paths:
        value = str(source).strip()
        if not value:
            continue
        directory = Path(value).expanduser()
        if not directory.is_absolute():
            raise ValueError(f"Bitte einen vollständigen Ordnerpfad verwenden: {value}")
        directory = directory.absolute()
        if not any(directory != root and root in directory.parents for root in roots_abs):
            raise ValueError(f"Dieser Ordner liegt nicht innerhalb von Videos, Downloads oder Bilder: {directory}")
        selected.add(directory)
    return tuple(sorted(selected, key=str))


def load_exclusions(path: Path | None = None) -> tuple[Path, ...]:
    target = Path(path) if path is not None else exclusions_path()
    if not target.exists():
        return ()
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("schema_version") != 1:
            raise ValueError("Unbekannte Ausschlusslisten-Version")
        paths = data.get("excluded", [])
        if not isinstance(paths, list) or not all(isinstance(v, str) for v in paths):
            raise ValueError("Ungültige Liste ausgeschlossener Ordner")
        return tuple(Path(p) for p in paths)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Ausschlussliste ist beschädigt oder unlesbar") from exc


def save_exclusions(paths: Iterable[str | Path], roots: Mapping[str, Path],
                    path: Path | None = None) -> tuple[Path, ...]:
    valid = validate_exclusions(paths, roots)
    target = Path(path) if path is not None else exclusions_path()
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=target.parent,
            prefix=".exclusions-", suffix=".tmp", delete=False
        ) as stream:
            temporary = stream.name
            os.chmod(temporary, 0o600)
            json.dump({"schema_version": 1, "excluded": list(map(str, valid))},
                      stream, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)
    return valid


XDG_KEYS = {"videos": "XDG_VIDEOS_DIR", "downloads": "XDG_DOWNLOAD_DIR", "pictures": "XDG_PICTURES_DIR"}


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
    roots: dict[str, Path] = {}
    for name, default in defaults.items():
        candidate = configured.get(XDG_KEYS[name], default).expanduser().absolute()
        # XDG can intentionally map an unset user folder to $HOME.
        # Never interpret that as permission to scan the entire home or /.
        if candidate in (home.absolute(), Path("/")):
            candidate = default
        roots[name] = candidate
    return roots
