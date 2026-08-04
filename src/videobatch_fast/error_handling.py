from __future__ import annotations

from dataclasses import dataclass

from .registry import load_json


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
    registry = load_json("registries/ERROR_REGISTRY.json").get("errors", {})
    raw = registry.get(code) if isinstance(registry, dict) else None
    if not isinstance(raw, dict):
        raw = {
            "title": "Unbekanntes Problem",
            "cause": "Die genaue Ursache konnte nicht eindeutig bestimmt werden.",
            "effect": "Der betroffene Vorgang wurde sicher gestoppt.",
            "automatic_action": "Originaldateien und vorhandene Ausgaben wurden geschützt.",
            "solution": "Technische Details prüfen und den Vorgang kontrolliert erneut starten.",
            "alternative": "Supportbericht öffnen.",
            "severity": "blocking",
            "actions": ["open_logs"],
        }
    return ErrorDefinition(
        code=code,
        title=str(raw.get("title", code)),
        cause=str(raw.get("cause", "")),
        effect=str(raw.get("effect", "")),
        automatic_action=str(raw.get("automatic_action", "")),
        solution=str(raw.get("solution", "")),
        alternative=str(raw.get("alternative", "")),
        severity=str(raw.get("severity", "blocking")),
        actions=tuple(str(item) for item in raw.get("actions", []) if str(item)),
    )
