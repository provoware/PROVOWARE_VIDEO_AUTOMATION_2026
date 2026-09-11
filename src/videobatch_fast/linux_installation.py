from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

APP_ID = "videobatch-fast"
APP_NAME = "VideoBatch Fast"
CANONICAL_DESKTOP = "videobatch-fast.desktop"
_MARKER = f"X-Provoware-AppId={APP_ID}"
_MANAGED_MARKER = "X-Provoware-Managed=true"


def _xdg_data_home() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")).expanduser().absolute()


def _xdg_state_home() -> Path:
    return Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")).expanduser().absolute()


def _atomic_text(path: Path, content: str, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    _atomic_text(
        path,
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        0o600,
    )


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _managed_root(path: Path) -> bool:
    if path.is_symlink() or not path.is_dir():
        return False
    state = _load_json(path / "installation_state.json")
    product = str(state.get("product", "")).strip().lower()
    return (
        product == APP_NAME.lower()
        and (path / "slots").is_dir()
        and (path / "controller").is_dir()
    )


def _install_record(path: Path) -> dict[str, Any]:
    state = _load_json(path / "installation_state.json")
    try:
        sequence = int(state.get("release_sequence", 0) or 0)
    except (TypeError, ValueError):
        sequence = 0
    return {
        "path": str(path),
        "version": str(state.get("version", "unbekannt")),
        "release_sequence": sequence,
        "pending_transaction": (path / "pending_transaction.json").exists(),
    }


def _candidate_legacy_roots(canonical: Path) -> list[Path]:
    data_home = _xdg_data_home()
    candidates: set[Path] = {
        data_home / "videobatch-fast",
        data_home / "VideoBatch-Fast",
        data_home / "provoware" / "VideoBatchFast",
        data_home / "PROVOWARE" / "VideoBatchFast",
        Path.home() / ".local/opt/VideoBatchFast",
        Path.home() / ".local/opt/videobatch-fast",
    }
    name_pattern = re.compile(r"^videobatch(?:[-_ ]?fast)?(?:[-_ ]?v?[0-9].*)?$", re.IGNORECASE)
    for parent in (data_home, data_home / "provoware", data_home / "PROVOWARE"):
        try:
            entries = list(parent.iterdir()) if parent.is_dir() else []
        except OSError:
            entries = []
        for entry in entries:
            if name_pattern.match(entry.name):
                candidates.add(entry)
    canonical_abs = canonical.absolute()
    return sorted(
        (path.absolute() for path in candidates if path.absolute() != canonical_abs),
        key=lambda path: str(path).lower(),
    )


def _is_videobatch_desktop(path: Path) -> bool:
    if not path.is_file() or path.is_symlink():
        return False
    try:
        text = path.read_text(encoding="utf-8", errors="replace")[:64_000]
    except OSError:
        return False
    if _MARKER in text:
        return True
    lowered = text.lower()
    named = "name=videobatch fast" in lowered or "name=videobatch fast portable" in lowered
    exec_owned = any(token in lowered for token in ("exec=", "videobatch", "starten.sh", "apprun"))
    return named and exec_owned


def _desktop_exec(path: Path) -> str:
    escaped = str(path).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _managed_wrapper(root: Path) -> str:
    return (
        "#!/usr/bin/env bash\n"
        "set -u\n"
        f"ROOT={shlex.quote(str(root))}\n"
        "for CTRL in \"$ROOT/controller/current/ab_launcher.py\" \"$ROOT/controller/previous/ab_launcher.py\"; do\n"
        "  [[ -f \"$CTRL\" ]] || continue\n"
        "  python3 \"$CTRL\" --install-root \"$ROOT\" -- \"$@\"; RC=$?\n"
        "  [[ $RC -lt 70 || $RC -gt 79 ]] && exit $RC\n"
        "done\n"
        "exit 76\n"
    )


def _portable_wrapper(launcher: Path) -> str:
    return (
        "#!/usr/bin/env bash\n"
        "set -Eeuo pipefail\n"
        f"exec {shlex.quote(str(launcher))} \"$@\"\n"
    )


def _link_version_name(link: Path, versions: Path) -> str | None:
    if not link.is_symlink():
        return None
    try:
        raw = Path(os.readlink(link))
        resolved = raw if raw.is_absolute() else link.parent / raw
        resolved = resolved.resolve(strict=False)
        versions_resolved = versions.resolve(strict=False)
        if resolved.parent != versions_resolved:
            return None
        return resolved.name
    except OSError:
        return None


def _prune_controller_versions(root: Path) -> list[str]:
    versions = root / "controller" / "versions"
    if not versions.is_dir() or versions.is_symlink():
        return []
    keep = {
        value
        for value in (
            _link_version_name(root / "controller/current", versions),
            _link_version_name(root / "controller/previous", versions),
        )
        if value
    }
    removed: list[str] = []
    for candidate in sorted(versions.iterdir(), key=lambda path: path.name):
        if candidate.name in keep or candidate.is_symlink() or not candidate.is_dir():
            continue
        shutil.rmtree(candidate)
        removed.append(candidate.name)
    return removed


def _backup_desktop(path: Path, backup_dir: Path) -> None:
    backup_dir.mkdir(parents=True, exist_ok=True)
    target = backup_dir / path.name
    counter = 1
    while target.exists():
        target = backup_dir / f"{path.stem}-{counter}{path.suffix}"
        counter += 1
    shutil.copy2(path, target)


def _prune_small_backups(parent: Path, keep: int = 3) -> None:
    if not parent.is_dir():
        return
    items = sorted(
        (path for path in parent.iterdir() if path.is_dir() and not path.is_symlink()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for path in items[keep:]:
        shutil.rmtree(path)


def _normalize_desktop(launcher: Path, state_dir: Path) -> tuple[Path, list[str], list[str]]:
    data_home = _xdg_data_home()
    canonical_dir = data_home / "applications"
    canonical_dir.mkdir(parents=True, exist_ok=True)
    canonical = canonical_dir / CANONICAL_DESKTOP
    desktop_text = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={APP_NAME}\n"
        "Comment=Geführte Videoautomatisierung · Qt 6 · Wayland\n"
        f"Exec={_desktop_exec(launcher)}\n"
        "Terminal=false\n"
        "Icon=video-x-generic\n"
        "Categories=AudioVideo;Video;\n"
        "StartupNotify=true\n"
        f"{_MARKER}\n"
        f"{_MANAGED_MARKER}\n"
    )
    _atomic_text(canonical, desktop_text, 0o644)

    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + f"-{os.getpid()}"
    backup_dir = state_dir / "menu-backups" / stamp
    removed: list[str] = []
    user_dirs = [canonical_dir]
    default_dir = Path.home() / ".local/share/applications"
    if default_dir.absolute() != canonical_dir.absolute():
        user_dirs.append(default_dir)
    for app_dir in user_dirs:
        if not app_dir.is_dir():
            continue
        for candidate in sorted(app_dir.glob("*.desktop")):
            if candidate.absolute() == canonical.absolute() or not _is_videobatch_desktop(candidate):
                continue
            try:
                text = candidate.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if "Hidden=true" in text and _MARKER in text:
                continue
            _backup_desktop(candidate, backup_dir)
            candidate.unlink()
            removed.append(str(candidate))

    hidden_system: list[str] = []
    for app_dir in (Path("/usr/local/share/applications"), Path("/usr/share/applications")):
        if not app_dir.is_dir():
            continue
        for candidate in sorted(app_dir.glob("*.desktop")):
            if candidate.name == CANONICAL_DESKTOP or not _is_videobatch_desktop(candidate):
                continue
            override = canonical_dir / candidate.name
            if override.exists() and not (
                override.is_file()
                and not override.is_symlink()
                and _MARKER in override.read_text(encoding="utf-8", errors="replace")
                and "Hidden=true" in override.read_text(encoding="utf-8", errors="replace")
            ):
                continue
            _atomic_text(
                override,
                "[Desktop Entry]\nHidden=true\n" + _MARKER + "\n" + _MANAGED_MARKER + "\n",
                0o644,
            )
            hidden_system.append(str(candidate))

    _prune_small_backups(state_dir / "menu-backups", keep=3)
    updater = shutil.which("update-desktop-database")
    if updater:
        subprocess.run(
            [updater, str(canonical_dir)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=20,
        )
    return canonical, removed, hidden_system


def _retire_legacy_roots(canonical: Path, state_dir: Path, current_sequence: int) -> tuple[list[str], list[dict[str, Any]]]:
    retired: list[str] = []
    blocked: list[dict[str, Any]] = []
    retire_dir = state_dir / "retired-installations"
    for candidate in _candidate_legacy_roots(canonical):
        if not _managed_root(candidate):
            continue
        record = _install_record(candidate)
        sequence = int(record["release_sequence"])
        if sequence <= 0 or sequence > current_sequence:
            record["reason"] = "Version ist unbekannt oder neuer als die bestätigte Standardinstallation."
            blocked.append(record)
            continue
        retire_dir.mkdir(parents=True, exist_ok=True)
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", candidate.name).strip("-") or "legacy"
        target = retire_dir / f"{safe_name}-seq{sequence}-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"
        try:
            os.replace(candidate, target)
        except OSError as exc:
            record["reason"] = f"Sicheres Verschieben nicht möglich: {exc}"
            blocked.append(record)
            continue
        retired.append(str(candidate))

    if retire_dir.is_dir():
        items = sorted(
            (path for path in retire_dir.iterdir() if _managed_root(path)),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for old in items[1:]:
            shutil.rmtree(old)
    return retired, blocked


def normalize_linux_installation(*, project_root: Path, launcher: Path) -> dict[str, Any]:
    """Keep one standard Linux installation and one visible application entry.

    Destructive cleanup is restricted to controller versions and old A/B roots that
    are positively identified as VideoBatch-managed. User configuration, state,
    caches, projects and media are never migration targets.
    """
    data_home = _xdg_data_home()
    state_dir = _xdg_state_home() / "VideoBatchFast" / "installer"
    state_dir.mkdir(parents=True, exist_ok=True)
    canonical = data_home / "VideoBatchFast"

    current_raw = os.environ.get("VIDEOBATCH_INSTALL_ROOT", "").strip()
    current = Path(current_raw).expanduser().absolute() if current_raw else None
    current_managed = current if current is not None and _managed_root(current) else None
    canonical_managed = canonical if _managed_root(canonical) else None
    preferred = current_managed or canonical_managed

    wrapper = Path.home() / ".local/bin/videobatch-fast"
    if preferred is not None:
        _atomic_text(wrapper, _managed_wrapper(preferred), 0o755)
    else:
        _atomic_text(wrapper, _portable_wrapper(launcher), 0o755)

    desktop, removed_desktop, hidden_system = _normalize_desktop(wrapper, state_dir)
    legacy_records = [
        _install_record(path)
        for path in _candidate_legacy_roots(canonical)
        if _managed_root(path) and (current is None or path.absolute() != current.absolute())
    ]

    controller_removed: list[str] = []
    retired: list[str] = []
    blocked: list[dict[str, Any]] = []
    destructive_allowed = (
        current_managed is not None
        and current_managed.absolute() == canonical.absolute()
        and not (canonical / "pending_transaction.json").exists()
    )
    if destructive_allowed:
        state = _load_json(canonical / "installation_state.json")
        try:
            current_sequence = int(state.get("release_sequence", 0) or 0)
        except (TypeError, ValueError):
            current_sequence = 0
        controller_removed = _prune_controller_versions(canonical)
        if current_sequence > 0:
            retired, blocked = _retire_legacy_roots(canonical, state_dir, current_sequence)

    report: dict[str, Any] = {
        "schema_version": 1,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "normalized" if (removed_desktop or hidden_system or controller_removed or retired) else "clean",
        "canonical_install_root": str(canonical),
        "current_install_root": str(current) if current is not None else None,
        "current_is_standard": bool(current_managed and current_managed.absolute() == canonical.absolute()),
        "destructive_cleanup_allowed": destructive_allowed,
        "legacy_installations_detected": legacy_records,
        "legacy_installations_retired": retired,
        "legacy_installations_blocked": blocked,
        "controller_versions_removed": controller_removed,
        "desktop_entries_removed": removed_desktop,
        "system_desktop_entries_hidden": hidden_system,
        "canonical_desktop_entry": str(desktop),
        "canonical_launcher": str(wrapper),
        "project_root": str(project_root),
        "protected_user_data": [
            str(Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "VideoBatchFast"),
            str(_xdg_state_home() / "VideoBatchFast"),
            str(Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "VideoBatchFast"),
            str(Path.home() / "Videos"),
        ],
    }
    if current_managed is not None and current_managed.absolute() != canonical.absolute():
        report["status"] = "attention"
        report["nonstandard_installation_note"] = (
            "Aktive Installation liegt außerhalb des XDG-Standardpfads. Sie wird während eines laufenden Starts nicht verschoben; "
            "der nächste reguläre Installerlauf soll sie durch die Standardinstallation ersetzen."
        )
    _atomic_json(state_dir / "installation-hygiene-latest.json", report)
    return report
