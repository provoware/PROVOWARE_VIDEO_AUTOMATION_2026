from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Any, Mapping

from .registry import load_json

LAYOUT_STORE_SCHEMA_VERSION = 1
_REGISTRY_PATH = "registries/WORKSPACE_LAYOUT_REGISTRY.json"
_SPLITTER_KEYS = ("root_vertical", "grid_vertical", "top_horizontal", "bottom_horizontal")


@dataclass(frozen=True, slots=True)
class LayoutResolution:
    profile_key: str
    ratios: dict[str, float]
    status: str
    reason: str
    store: dict[str, Any]


def _registry() -> dict[str, Any]:
    return load_json(_REGISTRY_PATH)


def contract_version() -> str:
    return str(_registry().get("contract_version", "workspace-grid-unknown"))


def display_profile_key(screen_width: int, screen_height: int, ui_zoom: int) -> str:
    width = max(320, int(screen_width or 0))
    height = max(240, int(screen_height or 0))
    zoom = min(300, max(50, int(ui_zoom or 100)))
    return f"{width}x{height}@{zoom}"


def _resolution_class(width: int, height: int) -> str:
    defaults = _registry().get("defaults", {})
    compact = defaults.get("compact", {}) if isinstance(defaults, dict) else {}
    standard = defaults.get("standard", {}) if isinstance(defaults, dict) else {}
    if width <= int(compact.get("max_width", 1366)) or height <= int(compact.get("max_height", 768)):
        return "compact"
    if width <= int(standard.get("max_width", 1920)) or height <= int(standard.get("max_height", 1080)):
        return "standard"
    return "large"


def tested_default_ratios(screen_width: int, screen_height: int, ui_zoom: int) -> dict[str, float]:
    registry = _registry()
    defaults = registry.get("defaults", {})
    class_name = _resolution_class(int(screen_width), int(screen_height))
    selected = defaults.get(class_name, {}) if isinstance(defaults, dict) else {}
    raw = selected.get("ratios", {}) if isinstance(selected, dict) else {}
    result = {key: float(raw.get(key, 0.5)) for key in _SPLITTER_KEYS}
    _ = min(300, max(50, int(ui_zoom or 100)))  # Zoom trennt Profile, verändert aber nicht die geprüften Standardverhältnisse.
    return result


def empty_layout_store() -> dict[str, Any]:
    return {
        "schema_version": LAYOUT_STORE_SCHEMA_VERSION,
        "contract_version": contract_version(),
        "profiles": {},
    }


def normalize_layout_store(raw: Any) -> dict[str, Any]:
    source = raw if isinstance(raw, dict) else {}
    profiles_raw = source.get("profiles", {}) if isinstance(source.get("profiles", {}), dict) else {}
    result = empty_layout_store()
    max_profiles = max(1, int(_registry().get("max_profiles_per_project", 16) or 16))
    normalized: list[tuple[str, dict[str, Any]]] = []
    for key, value in profiles_raw.items():
        if not isinstance(value, dict):
            continue
        try:
            width = max(320, int(value.get("screen_width", 0) or 0))
            height = max(240, int(value.get("screen_height", 0) or 0))
            zoom = min(300, max(50, int(value.get("ui_zoom", 100) or 100)))
        except (TypeError, ValueError):
            continue
        expected_key = display_profile_key(width, height, zoom)
        if str(key) != expected_key:
            continue
        ratios_raw = value.get("ratios", {}) if isinstance(value.get("ratios"), dict) else {}
        ratios: dict[str, float] = {}
        valid_numbers = True
        for splitter_key in _SPLITTER_KEYS:
            try:
                ratio = float(ratios_raw.get(splitter_key, float("nan")))
            except (TypeError, ValueError):
                valid_numbers = False
                break
            if not math.isfinite(ratio):
                valid_numbers = False
                break
            ratios[splitter_key] = ratio
        if not valid_numbers:
            continue
        normalized.append((expected_key, {
            "screen_width": width,
            "screen_height": height,
            "ui_zoom": zoom,
            "contract_version": str(value.get("contract_version", "")),
            "ratios": ratios,
            "updated_at": str(value.get("updated_at", "")),
            "source": str(value.get("source", "user") or "user"),
            "reset_reason": str(value.get("reset_reason", "")),
        }))
    normalized.sort(key=lambda item: item[1].get("updated_at", ""), reverse=True)
    result["profiles"] = dict(normalized[:max_profiles])
    return result


def _effective_bounds(splitter_key: str, total: int) -> tuple[float, float]:
    limits = _registry().get("limits", {}).get(splitter_key, {})
    hard_min = float(limits.get("hard_min_ratio", 0.2))
    hard_max = float(limits.get("hard_max_ratio", 0.8))
    if total <= 1:
        return hard_min, hard_max
    first_min = max(1.0, float(limits.get("first_min_px", 100)))
    second_min = max(1.0, float(limits.get("second_min_px", 100)))
    usable = max(1.0, float(total) * 0.92)
    if first_min + second_min > usable:
        scale = usable / (first_min + second_min)
        first_min *= scale
        second_min *= scale
    lower = max(hard_min, first_min / float(total))
    upper = min(hard_max, 1.0 - second_min / float(total))
    if lower >= upper:
        return hard_min, hard_max
    return lower, upper


def validate_ratios(ratios: Mapping[str, Any], dimensions: Mapping[str, int]) -> tuple[bool, str]:
    for splitter_key in _SPLITTER_KEYS:
        try:
            ratio = float(ratios[splitter_key])
        except (KeyError, TypeError, ValueError):
            return False, f"{splitter_key}: Verhältnis fehlt oder ist ungültig"
        if not math.isfinite(ratio):
            return False, f"{splitter_key}: Verhältnis ist nicht endlich"
        total = max(1, int(dimensions.get(splitter_key, 1) or 1))
        lower, upper = _effective_bounds(splitter_key, total)
        if ratio < lower or ratio > upper:
            return False, f"{splitter_key}: {ratio:.3f} außerhalb {lower:.3f} bis {upper:.3f}"
    return True, "Layoutverhältnisse sind plausibel."


def _profile_entry(
    screen_width: int,
    screen_height: int,
    ui_zoom: int,
    ratios: Mapping[str, float],
    *,
    source: str,
    reset_reason: str = "",
) -> dict[str, Any]:
    return {
        "screen_width": int(screen_width),
        "screen_height": int(screen_height),
        "ui_zoom": int(ui_zoom),
        "contract_version": contract_version(),
        "ratios": {key: round(float(ratios[key]), 6) for key in _SPLITTER_KEYS},
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "source": str(source),
        "reset_reason": str(reset_reason),
    }


def _trim_profiles(store: dict[str, Any]) -> dict[str, Any]:
    max_profiles = max(1, int(_registry().get("max_profiles_per_project", 16) or 16))
    profiles = store.get("profiles", {}) if isinstance(store.get("profiles"), dict) else {}
    items = sorted(profiles.items(), key=lambda item: str(item[1].get("updated_at", "")), reverse=True)
    store["profiles"] = dict(items[:max_profiles])
    return store


def resolve_layout_profile(
    raw_store: Any,
    *,
    screen_width: int,
    screen_height: int,
    ui_zoom: int,
    dimensions: Mapping[str, int],
) -> LayoutResolution:
    store = normalize_layout_store(raw_store)
    key = display_profile_key(screen_width, screen_height, ui_zoom)
    default_ratios = tested_default_ratios(screen_width, screen_height, ui_zoom)
    profile = store.get("profiles", {}).get(key)
    status = "default"
    reason = "Für dieses Anzeigeprofil existierte noch kein gespeichertes Raster."
    ratios = default_ratios
    if isinstance(profile, dict):
        if profile.get("contract_version") != contract_version():
            status = "healed"
            reason = "Gespeicherter Rastervertrag ist veraltet. Geprüfte Standardverhältnisse wurden wiederhergestellt."
        else:
            candidate = profile.get("ratios", {})
            valid, validation_reason = validate_ratios(candidate, dimensions)
            if valid:
                status = "restored"
                reason = "Gespeicherte Rasterverhältnisse wurden für dieses Anzeigeprofil wiederhergestellt."
                ratios = {key_name: float(candidate[key_name]) for key_name in _SPLITTER_KEYS}
            else:
                status = "healed"
                reason = f"Unbrauchbarer Rasterzustand erkannt: {validation_reason}. Standardverhältnisse wurden wiederhergestellt."
    store["schema_version"] = LAYOUT_STORE_SCHEMA_VERSION
    store["contract_version"] = contract_version()
    store.setdefault("profiles", {})[key] = _profile_entry(
        screen_width,
        screen_height,
        ui_zoom,
        ratios,
        source="user" if status == "restored" else status,
        reset_reason="" if status == "restored" else reason,
    )
    _trim_profiles(store)
    return LayoutResolution(key, ratios, status, reason, store)


def update_layout_profile(
    raw_store: Any,
    *,
    screen_width: int,
    screen_height: int,
    ui_zoom: int,
    ratios: Mapping[str, Any],
    dimensions: Mapping[str, int],
) -> LayoutResolution:
    store = normalize_layout_store(raw_store)
    key = display_profile_key(screen_width, screen_height, ui_zoom)
    valid, reason = validate_ratios(ratios, dimensions)
    if not valid:
        return resolve_layout_profile(
            store,
            screen_width=screen_width,
            screen_height=screen_height,
            ui_zoom=ui_zoom,
            dimensions=dimensions,
        )
    normalized_ratios = {splitter_key: float(ratios[splitter_key]) for splitter_key in _SPLITTER_KEYS}
    store.setdefault("profiles", {})[key] = _profile_entry(
        screen_width,
        screen_height,
        ui_zoom,
        normalized_ratios,
        source="user",
    )
    store["schema_version"] = LAYOUT_STORE_SCHEMA_VERSION
    store["contract_version"] = contract_version()
    _trim_profiles(store)
    return LayoutResolution(key, normalized_ratios, "saved", "Rasterzustand wurde für dieses Anzeigeprofil gespeichert.", store)


def reset_layout_profile(
    raw_store: Any,
    *,
    screen_width: int,
    screen_height: int,
    ui_zoom: int,
    dimensions: Mapping[str, int],
) -> LayoutResolution:
    store = normalize_layout_store(raw_store)
    key = display_profile_key(screen_width, screen_height, ui_zoom)
    store.setdefault("profiles", {}).pop(key, None)
    return resolve_layout_profile(
        store,
        screen_width=screen_width,
        screen_height=screen_height,
        ui_zoom=ui_zoom,
        dimensions=dimensions,
    )
