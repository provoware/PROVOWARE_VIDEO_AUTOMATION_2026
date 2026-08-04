from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from .layout_profiles import normalize_layout_store
from .paths import ensure_app_dirs, state_dir
from .safe_io import atomic_write_json, quarantine_file
from .slideshow_sequence import ORDER_MANUAL, ORDER_MODES

PROJECT_SCHEMA_VERSION = 3

DEFAULT_CALENDAR_COLORS = ["none", "success", "warning", "error", "info", "active"]
CALENDAR_ENTRY_TYPES = ["note", "task", "reminder", "deadline"]


def projects_dir() -> Path:
    path = state_dir() / "projects"
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_project_file() -> Path:
    return projects_dir() / "aktuelles_projekt.vbfast.json"


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
        state = normalize_project_state({})
        save_project_state(project_path, state)
        return project_path, state, False
    try:
        state = normalize_project_state(json.loads(project_path.read_text(encoding="utf-8")))
        return project_path, state, False
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, TypeError):

        try:
            quarantine_file(project_path, label="corrupt")
        except OSError:
            pass
        state = normalize_project_state({})
        save_project_state(project_path, state)
        return project_path, state, True


def save_project_state(path: Path | str, state: dict[str, Any]) -> Path:
    ensure_app_dirs()
    project_path = Path(path).expanduser()
    project_path.parent.mkdir(parents=True, exist_ok=True)
    normalized = normalize_project_state(state)
    atomic_write_json(project_path, normalized)
    return project_path
