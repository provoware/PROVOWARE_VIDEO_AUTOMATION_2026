from __future__ import annotations

from dataclasses import dataclass

from .registry import load_json


@dataclass(frozen=True, slots=True)
class PluginPermissionSummary:
    capability: str
    title: str
    purpose: str
    file_access: tuple[str, ...]
    actions: tuple[str, ...]
    prohibited: tuple[str, ...]
    risk_level: str
    publisher: str

    def plain_text(self, plugin_id: str, key_id: str) -> str:
        lines = [
            f"Plugin: {plugin_id}",
            f"Herausgeber: {self.publisher}",
            f"Signaturschlüssel: {key_id or 'unbekannt'}",
            f"Fähigkeit: {self.title}",
            f"Risiko: {self.risk_level}",
            "",
            "Zweck:",
            self.purpose,
            "",
            "Darf auf folgende Daten zugreifen:",
            *[f"• {item}" for item in self.file_access],
            "",
            "Darf folgende Aktionen ausführen:",
            *[f"• {item}" for item in self.actions],
            "",
            "Bleibt ausdrücklich verboten:",
            *[f"• {item}" for item in self.prohibited],
            "",
            "Das Plugin läuft nur im begrenzten Sandbox-Test und wird nicht automatisch dauerhaft aktiviert.",
        ]
        return "\n".join(lines)


def permission_summary(capability: str, key_id: str = "") -> PluginPermissionSummary:
    registry = load_json("registries/PLUGIN_REGISTRY.json")
    profiles = registry.get("permission_profiles", {})
    raw = profiles.get(capability, {}) if isinstance(profiles, dict) else {}
    trust = load_json("registries/PLUGIN_TRUST_REGISTRY.json")
    key_info = trust.get("trusted_keys", {}).get(key_id, {}) if key_id else {}
    publisher = str(key_info.get("publisher", "Nicht registrierter Herausgeber"))
    return PluginPermissionSummary(
        capability=capability,
        title=str(raw.get("title", capability or "Unbekannte Fähigkeit")),
        purpose=str(raw.get("purpose", "Keine Beschreibung registriert.")),
        file_access=tuple(str(item) for item in raw.get("file_access", ["Keine direkten Dateizugriffe registriert"])),
        actions=tuple(str(item) for item in raw.get("actions", ["Keine Aktionen registriert"])),
        prohibited=tuple(str(item) for item in raw.get("prohibited", ["Netzwerkzugriff", "Shell-Aufrufe", "unbegrenzter Dateizugriff"])),
        risk_level=str(raw.get("risk_level", "unbekannt")),
        publisher=publisher,
    )
