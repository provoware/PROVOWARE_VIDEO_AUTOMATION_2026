from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from .effects import TRANSITIONS, VISUAL_EFFECTS
from .paths import config_dir, default_output_dir, ensure_app_dirs
from .project_state import default_project_file
from .safe_io import atomic_write_json, quarantine_file
from .quick_modes import QUICK_MODES
from .workflow_grid import DEFAULT_WORKFLOW_LAYOUT_MODE, WORKFLOW_LAYOUT_MODES
from .slideshow import SLIDESHOW_MODES, TRANSITION_PRESETS
from .slideshow_sequence import ORDER_MODES

CONFIG_SCHEMA_VERSION = 3

DEFAULT_CONFIG: dict[str, Any] = {
    "schema_version": CONFIG_SCHEMA_VERSION,
    "output_dir": str(default_output_dir()),
    "output_mode": "Gemeinsamer Ordner",
    "resolution": "Original",
    "codec": "libx264",
    "profile": "fast",
    "verification": "Vollständig",
    "theme": "neon_gravity",
    "font_scale": 105,
    "window_geometry": "1380x860",
    "keep_lists": True,
    "visual_effect": "none",
    "transition": "none",
    "quick_mode": "smart_auto",
    "assignment_mode": "pairwise",
    "slideshow_transition": "auto",
    "slideshow_scene_sync": False,
    "slideshow_order_mode": "manual",
    "slideshow_random_seed": 0,
    "slideshow_start_image": "",
    "slideshow_end_image": "",
    "audio_sort": "import",
    "media_sort": "import",
    "last_audio_dir": str(Path.home() / "Downloads"),
    "last_media_dir": str(Path.home() / "Downloads"),
    "area_zoom": {"start": 100, "media": 100, "preview": 100, "modes": 100, "production": 100, "help": 100},
    "archive_used": False,
    "archive_project_dir": "",
    "archive_suffix": "__verwendet",
    "playlist_repeat": "off",
    "playlist_shuffle": False,
    "preview_zoom": 100,
    "active_tab": 0,
    "auto_open_output": True,
    "workflow_layout_mode": DEFAULT_WORKFLOW_LAYOUT_MODE,
    "current_project_file": str(default_project_file()),
    "debug_mode": True,
}


def config_file() -> Path:
    return config_dir() / "config.json"


def _normalize_area_zoom(raw: Any) -> dict[str, int]:
    source = raw if isinstance(raw, dict) else {}
    result: dict[str, int] = {}
    for area in ("start", "media", "preview", "modes", "production", "help"):
        try:
            result[area] = min(180, max(70, int(source.get(area, 100))))
        except (TypeError, ValueError):
            result[area] = 100
    return result


def _bounded_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        selected = int(value)
    except (TypeError, ValueError):
        return default
    return min(maximum, max(minimum, selected))


def _enum_value(value: Any, allowed: set[str], default: str) -> str:
    selected = str(value)
    return selected if selected in allowed else default


def _normalize_choice_fields(result: dict[str, Any]) -> None:
    choices = {
        "output_mode": {"Gemeinsamer Ordner", "Neben Mediendatei"},
        "resolution": {"Original", "1280×720", "1920×1080"},
        "codec": {"libx264", "libx265"},
        "profile": {"turbo", "fast", "balanced", "quality"},
        "verification": {"Schnell", "Vollständig"},
        "visual_effect": set(VISUAL_EFFECTS),
        "transition": set(TRANSITIONS),
        "quick_mode": set(QUICK_MODES),
        "assignment_mode": set(SLIDESHOW_MODES),
        "slideshow_transition": set(TRANSITION_PRESETS),
        "slideshow_order_mode": set(ORDER_MODES),
        "playlist_repeat": {"off", "one", "all"},
        "theme": {"neon_gravity", "acid_paper", "toxic_candy", "ultraviolet"},
        "workflow_layout_mode": WORKFLOW_LAYOUT_MODES,
    }
    for key, allowed in choices.items():
        result[key] = _enum_value(result.get(key), allowed, str(DEFAULT_CONFIG[key]))


def _normalize_slideshow_fields(result: dict[str, Any]) -> None:
    result["slideshow_scene_sync"] = bool(result.get("slideshow_scene_sync", False))
    result["slideshow_random_seed"] = _bounded_int(
        result.get("slideshow_random_seed", 0), 0, 0, 2_147_483_647
    )
    for anchor_key in ("slideshow_start_image", "slideshow_end_image"):
        result[anchor_key] = str(result.get(anchor_key, "") or "")


def _normalize_ui_fields(result: dict[str, Any]) -> None:
    result["font_scale"] = _bounded_int(result.get("font_scale", 105), 105, 80, 160)
    result["preview_zoom"] = _bounded_int(result.get("preview_zoom", 100), 100, 25, 800)
    result["active_tab"] = _bounded_int(result.get("active_tab", 0), 0, 0, 5)
    result["area_zoom"] = _normalize_area_zoom(result.get("area_zoom", {}))
    result["keep_lists"] = bool(result.get("keep_lists", True))
    result["archive_used"] = bool(result.get("archive_used", False))
    result["playlist_shuffle"] = bool(result.get("playlist_shuffle", False))
    result["auto_open_output"] = bool(result.get("auto_open_output", True))
    result["debug_mode"] = bool(result.get("debug_mode", True))


def _normalize_file_fields(result: dict[str, Any]) -> None:
    allowed_sort = {
        "import", "name_asc", "name_desc", "size_asc", "size_desc",
        "modified_new", "modified_old", "created_new", "created_old",
        "duration_short", "duration_long", "type",
    }
    result["audio_sort"] = _enum_value(result.get("audio_sort"), allowed_sort, "import")
    result["media_sort"] = _enum_value(result.get("media_sort"), allowed_sort, "import")
    suffix = str(result.get("archive_suffix", "__verwendet")).strip()
    result["archive_suffix"] = suffix if suffix.startswith("__") and len(suffix) <= 40 else "__verwendet"
    downloads = str(Path.home() / "Downloads")
    for directory_key in ("last_audio_dir", "last_media_dir"):
        result[directory_key] = str(result.get(directory_key, downloads) or downloads).strip() or downloads
    current_project = str(result.get("current_project_file", default_project_file()) or default_project_file()).strip()
    result["current_project_file"] = current_project or str(default_project_file())


def normalize_config(raw: Any) -> dict[str, Any]:
    source = raw if isinstance(raw, dict) else {}
    result = dict(DEFAULT_CONFIG)
    source_schema = _bounded_int(source.get("schema_version", 1), 1, 1, 1_000_000)
    if source_schema > CONFIG_SCHEMA_VERSION:
        return result
    result.update({key: source[key] for key in result if key in source})
    result["schema_version"] = CONFIG_SCHEMA_VERSION
    _normalize_choice_fields(result)
    _normalize_slideshow_fields(result)
    _normalize_ui_fields(result)
    _normalize_file_fields(result)
    return result


def load_config() -> dict[str, Any]:
    ensure_app_dirs()
    path = config_file()
    if not path.exists():
        return dict(DEFAULT_CONFIG)
    try:
        return normalize_config(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        try:
            quarantine_file(path, label="corrupt")
        except OSError:
            pass
        defaults = dict(DEFAULT_CONFIG)
        try:
            save_config(defaults)
        except OSError:
            pass
        return defaults


def save_config(data: dict[str, Any]) -> None:
    ensure_app_dirs()
    path = config_file()
    normalized = normalize_config(data)
    atomic_write_json(path, normalized)
