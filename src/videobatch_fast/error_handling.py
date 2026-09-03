from __future__ import annotations

from dataclasses import dataclass

from .registry import RegistryError, load_json


_FALLBACK_TEXT = {
    "title": "Unbekanntes Problem",
    "cause": "Die genaue Ursache konnte nicht eindeutig bestimmt werden.",
    "effect": "Der betroffene Vorgang wurde sicher gestoppt.",
    "automatic_action": "Originaldateien und vorhandene Ausgaben wurden geschützt.",
    "solution": "Technische Details prüfen und den Vorgang kontrolliert erneut starten.",
    "alternative": "Supportbericht öffnen.",
    "severity": "blocking",
}
_FALLBACK_ACTIONS = ("open_logs",)
_SEVERITIES = frozenset({"information", "warning", "blocking"})
_ERROR_REGISTRIES = (
    "registries/ERROR_REGISTRY.json",
    "registries/RUNTIME_ERROR_REGISTRY.json",
)


@dataclass(frozen=True, slots=True)
class ErrorDefinition:
    code: str
    title: str
    cause: str
    effect: str
    automatic_action: str
    solution: str
    alternative: str
    severity: str
    actions: tuple[str, ...]


def _merged_error_registry() -> dict[str, dict]:
    merged: dict[str, dict] = {}
    for path in _ERROR_REGISTRIES:
        try:
            payload = load_json(path)
        except RegistryError:
            continue
        errors = payload.get("errors", {}) if isinstance(payload, dict) else {}
        if not isinstance(errors, dict):
            continue
        for code, raw in errors.items():
            if isinstance(code, str) and isinstance(raw, dict):
                merged[code] = raw
    return merged


def error_definition(code: str) -> ErrorDefinition:
    raw = _merged_error_registry().get(code)
    if not isinstance(raw, dict):
        raw = {}
    values = {key: _text_value(raw, key) for key in _FALLBACK_TEXT}
    severity = values["severity"]
    if severity not in _SEVERITIES:
        severity = _FALLBACK_TEXT["severity"]
    raw_actions = raw.get("actions")
    actions = raw_actions if isinstance(raw_actions, list) else _FALLBACK_ACTIONS
    return ErrorDefinition(
        code=code,
        title=values["title"],
        cause=values["cause"],
        effect=values["effect"],
        automatic_action=values["automatic_action"],
        solution=values["solution"],
        alternative=values["alternative"],
        severity=severity,
        actions=tuple(str(item).strip() for item in actions if str(item).strip()),
    )


def _text_value(raw: dict, key: str) -> str:
    value = raw.get(key)
    return value.strip() if isinstance(value, str) and value.strip() else _FALLBACK_TEXT[key]
