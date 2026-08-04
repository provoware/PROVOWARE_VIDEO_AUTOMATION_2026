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


def error_definition(code: str) -> ErrorDefinition:
    try:
        registry = load_json("registries/ERROR_REGISTRY.json").get("errors", {})
    except RegistryError:
        registry = {}
    raw = registry.get(code) if isinstance(registry, dict) else None
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
