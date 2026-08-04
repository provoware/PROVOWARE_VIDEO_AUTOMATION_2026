from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

PROJECT_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_REGISTRIES = (
    "registries/ERROR_REGISTRY.json",
    "registries/FUNCTION_REGISTRY.json",
    "registries/PLUGIN_REGISTRY.json",
    "registries/UPDATE_REGISTRY.json",
    "registries/SCENARIO_REGISTRY.json",
    "resources/texts/de.json",
    "resources/themes/dark.json",
    "registries/UI_BLUEPRINT.json",
    "registries/PLUGIN_TRUST_REGISTRY.json",
    "registries/PLUGIN_APPROVAL_REGISTRY.json",
    "registries/VISUAL_REGRESSION_REGISTRY.json",
    "registries/VISUAL_INSPECTION_REGISTRY.json",
    "registries/VISUAL_APPROVAL_REGISTRY.json",
    "registries/UI_COMPONENT_REGISTRY.json",
    "registries/WORKSPACE_LAYOUT_REGISTRY.json",
    "registries/CODE_QUALITY_REGISTRY.json",
)


class RegistryError(RuntimeError):
    pass


def _strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise RegistryError(f"Doppelter JSON-Schlüssel: {key}")
        result[key] = value
    return result


@lru_cache(maxsize=64)
def load_json(relative_path: str) -> dict[str, Any]:
    path = (PROJECT_ROOT / relative_path).resolve()
    if PROJECT_ROOT not in path.parents:
        raise RegistryError("Registry-Pfad verlässt das Projekt.")
    try:
        raw = path.read_text(encoding="utf-8")
        value = json.loads(raw, object_pairs_hook=_strict_pairs)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RegistryError(f"Registry nicht lesbar: {relative_path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RegistryError(f"Registry-Wurzel muss ein Objekt sein: {relative_path}")
    if int(value.get("schema_version", 0) or 0) < 1:
        raise RegistryError(f"Registry-Schema fehlt: {relative_path}")
    return value


def clear_registry_cache() -> None:
    load_json.cache_clear()


def _validate_required_files(errors: list[str]) -> None:
    for path in REQUIRED_REGISTRIES:
        try:
            load_json(path)
        except RegistryError as exc:
            errors.append(str(exc))


def _validate_error_registry(errors: list[str]) -> None:
    registry = load_json("registries/ERROR_REGISTRY.json").get("errors", {})
    if not isinstance(registry, dict) or not registry:
        errors.append("Fehlerregister ist leer.")
        return
    fields = ("title", "cause", "effect", "automatic_action", "solution", "alternative", "severity", "actions")
    for code, item in registry.items():
        if not isinstance(item, dict):
            errors.append(f"{code}: Fehlerdefinition ist kein Objekt.")
            continue
        for field in fields:
            if not item.get(field):
                errors.append(f"{code}: Pflichtfeld fehlt: {field}")


def _validate_plugin_registries(errors: list[str]) -> None:
    trust = load_json("registries/PLUGIN_TRUST_REGISTRY.json")
    policy = trust.get("policy", {})
    if policy.get("algorithm") != "ed25519":
        errors.append("Plugin-Vertrauensregister: Algorithmus muss ed25519 sein.")
    keys = trust.get("trusted_keys", {})
    if not isinstance(keys, dict) or not keys:
        errors.append("Plugin-Vertrauensregister enthält keine aktiven Schlüssel.")
    elif any(not isinstance(item, dict) or not item.get("public_key_base64") for item in keys.values()):
        errors.append("Plugin-Vertrauensregister enthält einen unvollständigen Schlüssel.")

    plugin = load_json("registries/PLUGIN_REGISTRY.json")
    allowed = plugin.get("allowed_capabilities", [])
    implemented = plugin.get("implemented_capabilities", [])
    if allowed != implemented:
        errors.append("Plugin-Registry: nur vollständig implementierte Capabilities dürfen erlaubt sein.")
    profiles = plugin.get("permission_profiles", {})
    if not isinstance(profiles, dict):
        errors.append("Plugin-Berechtigungsprofile fehlen.")
        return
    fields = ("title", "purpose", "file_access", "actions", "prohibited", "risk_level")
    for capability in allowed:
        profile = profiles.get(capability)
        if not isinstance(profile, dict):
            errors.append(f"Plugin-Berechtigungsprofil fehlt: {capability}")
            continue
        for field in fields:
            if not profile.get(field):
                errors.append(f"{capability}: Plugin-Berechtigungsfeld fehlt: {field}")


def _validate_visual_registries(errors: list[str]) -> None:
    visual = load_json("registries/VISUAL_REGRESSION_REGISTRY.json")
    scenarios = visual.get("scenarios", [])
    ids = [str(item.get("id", "")) for item in scenarios if isinstance(item, dict)]
    if len(ids) < 4 or len(ids) != len(set(ids)):
        errors.append("Visuelle Regression benötigt mindestens vier eindeutige Szenarien.")
    if not visual.get("policy", {}).get("baseline_changes_require_explicit_acceptance"):
        errors.append("Visuelle Referenzen dürfen nicht automatisch ersetzt werden.")
    workspace_states = {
        str(item.get("state"))
        for item in scenarios
        if isinstance(item, dict) and item.get("page") == "workspace"
    }
    missing_states = {"files", "preview", "playlist", "monitor"} - workspace_states
    if missing_states:
        errors.append(f"Visuelle Arbeitsbereich-Szenarien fehlen: {', '.join(sorted(missing_states))}")
    required_visuals = {
        "workspace_grid_1280x720_100",
        "workspace_debug_machine_1920x1080_100",
        "dialog_plugin_approval_manager_1180x700_100",
        "dialog_visual_approval_760x540_100",
    }
    missing_visuals = required_visuals - set(ids)
    if missing_visuals:
        errors.append(f"Visuelle 2.8-Szenarien fehlen: {', '.join(sorted(missing_visuals))}")

    approval = load_json("registries/VISUAL_APPROVAL_REGISTRY.json")
    rules = approval.get("rules", {})
    required_rules = (
        "signature_invalidates_on_visual_contract_change",
        "signature_invalidates_on_baseline_change",
        "signature_invalidates_on_normalized_report_change",
        "volatile_measurements_do_not_invalidate",
        "private_key_not_packaged",
        "private_key_backup_must_be_encrypted",
        "stable_update_must_bind_approval_hash",
    )
    for field in required_rules:
        if not rules.get(field):
            errors.append(f"Visueller Freigabevertrag fehlt: {field}")


def _validate_ui_and_layout(errors: list[str]) -> None:
    components = load_json("registries/UI_COMPONENT_REGISTRY.json").get("components", {})
    if not isinstance(components, dict) or len(components) < 6:
        errors.append("UI-Komponentenregister ist unvollständig.")
        return
    required = {
        "workspace.grid2x2",
        "debug.professional_footer",
        "plugins.approval_manager",
        "quality.visual_manual_approval",
        "diagnostics.report",
    }
    missing_components = required - set(components)
    if missing_components:
        errors.append(f"UI-Komponentenregister 2.8 unvollständig: {', '.join(sorted(missing_components))}")

    layout = load_json("registries/WORKSPACE_LAYOUT_REGISTRY.json")
    if not layout.get("contract_version"):
        errors.append("Rasterprofil-Registry: contract_version fehlt.")
    limits = layout.get("limits", {})
    required_splitters = {"root_vertical", "grid_vertical", "top_horizontal", "bottom_horizontal"}
    missing_splitters = required_splitters - set(limits) if isinstance(limits, dict) else required_splitters
    if missing_splitters:
        errors.append(f"Rasterprofil-Registry unvollständig: {', '.join(sorted(missing_splitters))}")
    rules = layout.get("rules", {})
    required_layout_rules = (
        "store_ratios_not_absolute_pixels",
        "separate_by_resolution_and_ui_zoom",
        "contract_change_expires_profile",
        "invalid_values_reset_to_tested_defaults",
        "project_scoped_storage",
    )
    for field in required_layout_rules:
        if not rules.get(field):
            errors.append(f"Rasterprofil-Regel fehlt: {field}")


def _validate_text_registry(errors: list[str]) -> None:
    from .text_resources import validate_text_resources

    errors.extend(validate_text_resources(PROJECT_ROOT))


def _validate_quality_registry(errors: list[str]) -> None:
    quality = load_json("registries/CODE_QUALITY_REGISTRY.json")
    required = {"ruff", "mypy", "pytest_cov", "bandit", "pip_audit"}
    gates = set(quality.get("required_gates", []))
    missing = required - gates
    if missing:
        errors.append(f"Codequalitäts-Gates fehlen: {', '.join(sorted(missing))}")
    dependency = quality.get("dependency_policy", {})
    if not dependency.get("exact_versions_required"):
        errors.append("Codequalität: exakte Abhängigkeitsversionen sind nicht verpflichtend.")


_VALIDATORS: tuple[Callable[[list[str]], None], ...] = (
    _validate_error_registry,
    _validate_plugin_registries,
    _validate_visual_registries,
    _validate_ui_and_layout,
    _validate_text_registry,
    _validate_quality_registry,
)


def validate_registries() -> list[str]:
    errors: list[str] = []
    _validate_required_files(errors)
    for validator in _VALIDATORS:
        try:
            validator(errors)
        except RegistryError as exc:
            errors.append(str(exc))
    return errors
