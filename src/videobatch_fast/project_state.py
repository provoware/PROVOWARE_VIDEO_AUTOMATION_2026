from __future__ import annotations

import fcntl
import json
import os
import stat
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from .layout_profiles import normalize_layout_store
from .paths import ensure_app_dirs, state_dir
from .safe_io import atomic_write_bytes, atomic_write_json, quarantine_file
from .slideshow_sequence import ORDER_MANUAL, ORDER_MODES

PROJECT_SCHEMA_VERSION = 3
PROJECT_NOTES_FILENAME = "VideoBatch_Notizen.txt"

DEFAULT_CALENDAR_COLORS = ["none", "success", "warning", "error", "info", "active"]
CALENDAR_ENTRY_TYPES = ["note", "task", "reminder", "deadline"]


def projects_dir() -> Path:
    path = state_dir() / "projects"
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_project_file() -> Path:
    return projects_dir() / "aktuelles_projekt.vbfast.json"


def project_notes_file(project_file: Path) -> Path:
    """Keep the append-only note file next to the active project document."""
    return Path(project_file).expanduser().parent / PROJECT_NOTES_FILENAME


def _read_existing_notes(target: Path) -> tuple[bytes, int]:
    """Refuse redirected targets before copying their content into an atomic update."""
    try:
        descriptor = os.open(target, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return b"", 0o600
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise OSError(f"Unsicheres Notizziel (kein einzelner regulärer Dateieintrag): {target}")
        return stream.read(), stat.S_IMODE(info.st_mode)


def append_project_note(project_file: Path, note: str, *, now: datetime | None = None) -> tuple[Path, str]:
    """Append one dated line without replacing existing notes or source media."""
    content = " ".join(str(note).split())
    if not content:
        raise ValueError("Bitte zuerst eine Notiz eingeben.")
    if len(content) > 500:
        raise ValueError("Die Notiz darf höchstens 500 Zeichen enthalten.")
    target = project_notes_file(project_file)
    if not target.parent.is_dir():
        raise FileNotFoundError(f"Projektordner nicht erreichbar: {target.parent}")
    timestamp = (now or datetime.now().astimezone()).astimezone().isoformat(timespec="seconds")
    entry = f"[{timestamp}] {content}\n".encode("utf-8")
    # Lock the stable directory inode: the notes inode changes at atomic replace.
    directory_fd = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        fcntl.flock(directory_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        previous, mode = _read_existing_notes(target)
        separator = b"\n" if previous and not previous.endswith(b"\n") else b""
        atomic_write_bytes(target, previous + separator + entry, mode=mode)
    finally:
        os.close(directory_fd)
    return target, timestamp


def _normalize_paths(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    result: list[str] = []
    for item in values:
        value = str(item).strip()
        if value and value not in result:
            result.append(value)
    return result


def _bounded_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError):
        return default
    return result if minimum <= result <= maximum else default


def _bounded_tenth(value: Any) -> float:
    try:
        selected = float(value)
    except (ValueError, TypeError):
        return 1.0
    if not 0 <= selected <= 5:
        return 1.0
    return round(selected, 1)


def _base_project_state(source: dict[str, Any], now: str) -> dict[str, Any]:
    local = time.localtime()
    return {
        "schema_version": PROJECT_SCHEMA_VERSION,
        "project_name": str(source.get("project_name", "Neues Projekt") or "Neues Projekt"),
        "created_at": str(source.get("created_at", now) or now),
        "updated_at": now,
        "quick_note": str(source.get("quick_note", "") or "")[:2000],
        "audio_paths": _normalize_paths(source.get("audio_paths")),
        "media_paths": _normalize_paths(source.get("media_paths")),
        "playlist_paths": _normalize_paths(source.get("playlist_paths")),
        "output_dir": str(source.get("output_dir", "") or ""),
        "quick_mode": str(source.get("quick_mode", "smart_auto") or "smart_auto"),
        "assignment_mode": str(source.get("assignment_mode", "pairwise") or "pairwise"),
        "slideshow_transition": str(source.get("slideshow_transition", "auto") or "auto"),
        "slideshow_transition_seconds": _bounded_tenth(source.get("slideshow_transition_seconds", 1.0)),
        "effect_intensity": _bounded_int(source.get("effect_intensity", 100), 100, 0, 100),
        "transition_duration": _bounded_tenth(source.get("transition_duration", 0.8)),
        "resolution": str(source.get("resolution", "Original") or "Original"),
        "profile": str(source.get("profile", "fast") or "fast"),
        "visual_effect": str(source.get("visual_effect", "none") or "none"),
        "transition": str(source.get("transition", "none") or "none"),
        "verification": str(source.get("verification", "Vollständig") or "Vollständig"),
        "slideshow_scene_sync": bool(source.get("slideshow_scene_sync", False)),
        "slideshow_order_mode": (
            str(source.get("slideshow_order_mode", ORDER_MANUAL) or ORDER_MANUAL)
            if str(source.get("slideshow_order_mode", ORDER_MANUAL) or ORDER_MANUAL) in ORDER_MODES
            else ORDER_MANUAL
        ),
        "slideshow_random_seed": _bounded_int(source.get("slideshow_random_seed"), 0, 0, 2_147_483_647),
        "slideshow_start_image": str(source.get("slideshow_start_image", "") or ""),
        "slideshow_end_image": str(source.get("slideshow_end_image", "") or ""),
        "audio_sort": str(source.get("audio_sort", "import") or "import"),
        "media_sort": str(source.get("media_sort", "import") or "import"),
        "archive_used": bool(source.get("archive_used", False)),
        "archive_project_dir": str(source.get("archive_project_dir", "") or ""),
        "archive_suffix": str(source.get("archive_suffix", "__verwendet") or "__verwendet"),
        "calendar_year": _bounded_int(source.get("calendar_year"), local.tm_year, 2000, 2100),
        "calendar_month": _bounded_int(source.get("calendar_month"), local.tm_mon, 1, 12),
        "calendar_marks": {},
        "calendar_notes": {},
        "workspace_layout_profiles": normalize_layout_store(
            source.get("workspace_layout_profiles", source.get("workspace_layout", {}))
        ),
        "meta": source.get("meta", {}) if isinstance(source.get("meta"), dict) else {},
    }


def _normalize_calendar_marks(source: dict[str, Any]) -> dict[str, str]:
    marks: dict[str, str] = {}
    raw = source.get("calendar_marks", {})
    if not isinstance(raw, dict):
        return marks
    for key, value in raw.items():
        date_key = str(key)
        color = str(value)
        if len(date_key) == 10 and color in DEFAULT_CALENDAR_COLORS:
            marks[date_key] = color
    return marks


def _normalize_calendar_notes(source: dict[str, Any], marks: dict[str, str]) -> dict[str, dict[str, str]]:
    notes: dict[str, dict[str, str]] = {}
    raw = source.get("calendar_notes", {})
    if isinstance(raw, dict):
        for key, value in raw.items():
            normalized = _normalize_calendar_note(str(key), value, marks)
            if normalized is not None:
                notes[str(key)] = normalized
                if normalized["color"] != "none":
                    marks[str(key)] = normalized["color"]
    for key, color in marks.items():
        notes.setdefault(key, {"note": "", "entry_type": "note", "color": color})
    return notes


def _normalize_calendar_note(
    key: str, value: Any, marks: dict[str, str]
) -> dict[str, str] | None:
    if len(key) != 10 or not isinstance(value, dict):
        return None
    note = str(value.get("note", "") or "")[:500]
    entry_type = str(value.get("entry_type", "note") or "note")
    color = str(value.get("color", marks.get(key, "none")) or "none")
    if entry_type not in CALENDAR_ENTRY_TYPES:
        entry_type = "note"
    if color not in DEFAULT_CALENDAR_COLORS:
        color = "none"
    if not note and color == "none":
        return None
    return {"note": note, "entry_type": entry_type, "color": color}


def normalize_project_state(raw: Any) -> dict[str, Any]:
    source = raw if isinstance(raw, dict) else {}
    state = _base_project_state(source, time.strftime("%Y-%m-%dT%H:%M:%S"))
    marks = _normalize_calendar_marks(source)
    state["calendar_marks"] = marks
    state["calendar_notes"] = _normalize_calendar_notes(source, marks)
    return state


def load_project_state(path: Path | str | None = None) -> tuple[Path, dict[str, Any], bool]:
    ensure_app_dirs()
    project_path = Path(path).expanduser() if path else default_project_file()
    if not project_path.exists():
        # Only the application's default project may be created implicitly.
        # A manually selected project disappearing before opening is an
        # error, not permission to silently replace it with a blank one.
        if project_path != default_project_file():
            raise FileNotFoundError(
                f"Ausgewähltes Projekt ist nicht mehr vorhanden: {project_path}"
            )
        state = normalize_project_state({})
        save_project_state(project_path, state)
        return project_path, state, False
    # Read-access errors are not corruption: keep the original project intact.
    # In particular, do not replace a temporarily unreadable project by blanks.
    try:
        text = project_path.read_text(encoding="utf-8")
    except UnicodeError:
        corrupted = True
    else:
        try:
            source = json.loads(text)
        except (json.JSONDecodeError, UnicodeError):
            corrupted = True
        else:
            if not isinstance(source, dict):
                corrupted = True
            else:
                return project_path, normalize_project_state(source), False

    if corrupted:
        # Quarantine must succeed before creating any replacement. If backup
        # fails (read-only/full disk), propagate the error without data loss.
        quarantine_file(project_path, label="corrupt")
        state = normalize_project_state({})
        save_project_state(project_path, state)
        return project_path, state, True
    raise AssertionError("Unreachable project loader state")


def save_project_state(path: Path | str, state: dict[str, Any]) -> Path:
    ensure_app_dirs()
    project_path = Path(path).expanduser()
    project_path.parent.mkdir(parents=True, exist_ok=True)
    normalized = normalize_project_state(state)
    atomic_write_json(project_path, normalized)
    return project_path
