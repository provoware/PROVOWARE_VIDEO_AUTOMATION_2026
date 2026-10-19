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

def explain_runtime_problem(message: str) -> tuple[str, str]:
    """Turn common local I/O / FFmpeg failures into safe German next steps.

    The original diagnostic detail must still be kept in the local log.
    Unknown errors are explicitly classified as unknown, never as fixed.
    """
    value = message.casefold()
    rules: tuple[tuple[tuple[str, ...], str, str], ...] = (
        (("no space left", "kein speicherplatz", "errno 28"),
         "Das Ziellaufwerk hat nicht genügend freien Speicher.",
         "Speicherplatz freigeben oder einen anderen Ausgabeordner wählen."),
        (("permission denied", "zugriff verweigert", "errno 13"),
         "VideoBatch darf auf die Datei oder den Zielordner nicht zugreifen.",
         "Die Dateiberechtigung prüfen oder einen Benutzerordner auswählen."),
        (("invalid data found", "moov atom not found", "invalid argument"),
         "Eine Quelldatei oder Medienkombination konnte nicht gelesen werden.",
         "Die betroffene Datei einzeln prüfen und gegebenenfalls neu exportieren."),
        (("unknown encoder", "encoder not found", "encoder does not exist"),
         "Der gewünschte Video- oder Audiocodierer fehlt in FFmpeg.",
         "Einen verfügbaren Codec wählen oder FFmpeg kontrollieren."),
        (("error while opening encoder", "incorrect parameters"),
         "Die ausgewählte Codierung ist mit diesen Parametern nicht möglich.",
         "Auflösung, Bildformat und Qualitätsvorgaben überprüfen."),
        (("input/output error", "i/o error", "errno 5"),
         "Das Laufwerk hat einen Ein- oder Ausgabefehler gemeldet.",
         "Laufwerkverbindung prüfen; Quelldateien nicht verändern."),
    )
    for needles, title, solution in rules:
        if any(word in value for word in needles):
            return title, solution
    return (
        "Die Verarbeitung konnte nicht abgeschlossen werden.",
        "Technische Meldungen öffnen, die betroffene Datei prüfen und erneut versuchen.",
    )
