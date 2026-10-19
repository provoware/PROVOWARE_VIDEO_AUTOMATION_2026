"""Single, versioned source of truth for the four everyday video settings.

No Qt imports. The stored identifiers are the actual renderer identifiers;
German labels are presentation-only. Original media are never modified here.
"""
from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Mapping

from .effects import TRANSITIONS, VISUAL_EFFECTS
from .quick_modes import QUICK_MODES
from .safe_io import atomic_write_json

SCHEMA_VERSION = 2
RESOLUTION_LABELS = {
    "Original": "Originalgröße",
    "1280×720": "HD · 720p",
    "1920×1080": "Full HD · 1080p",
    "2560×1440": "QHD · 1440p",
    "3840×2160": "UHD · 2160p",
}
QUALITY_LABELS = {
    "turbo": "Schnell",
    "balanced": "Ausgewogen",
    "quality": "Hoch",
    "maximum": "Maximum",
}
# The effect field represents one visual effect, not a combined quick mode.
EFFECT_LABELS: dict[str, str] = {"none": "Kein Effekt"}
for _preset in QUICK_MODES.values():
    if _preset.visual_effect not in EFFECT_LABELS:
        EFFECT_LABELS[_preset.visual_effect] = _preset.label
for _effect_key, _effect in VISUAL_EFFECTS.items():
    EFFECT_LABELS.setdefault(_effect_key, _effect.label)
FIELDS = frozenset({"resolution", "quality", "effect", "output_dir", "effect_intensity", "transition", "transition_duration"})
_LEGACY_RESOLUTIONS = {"HD": "1280×720", "Full HD": "1920×1080", "QHD": "2560×1440", "UHD": "3840×2160"}
_LEGACY_QUALITIES = {"Schnell": "turbo", "Ausgewogen": "balanced", "Hoch": "quality", "Maximum": "maximum"}


def settings_path() -> Path:
    home_config = Path.home() / ".config"
    supplied = os.environ.get("XDG_CONFIG_HOME")
    root = Path(supplied).expanduser() if supplied and Path(supplied).is_absolute() else home_config
    return root / "provoware" / "videobatch" / "dashboard_settings.json"


@dataclass(frozen=True)
class DashboardSettings:
    resolution: str = "Original"
    quality: str = "balanced"
    effect: str = "none"
    effect_intensity: int = 100  # 100 = prior unmodified effect, 0 = disabled
    transition: str = "none"
    transition_duration: float = 0.8
    output_dir: Path = field(default_factory=lambda: Path.home() / "Videos" / "VideoBatch")
    explicit_fields: frozenset[str] = frozenset()
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("Nicht unterstützte Einstellungs-Version")
        if self.resolution not in RESOLUTION_LABELS:
            raise ValueError("Unbekannte Auflösung")
        if self.quality not in QUALITY_LABELS:
            raise ValueError("Unbekannte Qualitätsstufe")
        if self.effect not in EFFECT_LABELS:
            raise ValueError("Unbekannter Bildeffekt")
        if type(self.effect_intensity) is not int or not 0 <= self.effect_intensity <= 100:
            raise ValueError("Effektstärke muss zwischen 0 und 100 liegen")
        if self.transition not in TRANSITIONS:
            raise ValueError("Unbekannte Videoblende")
        if not math.isfinite(float(self.transition_duration)) or not 0 <= self.transition_duration <= 5:
            raise ValueError("Blenddauer muss zwischen 0 und 5 Sekunden liegen")
        if not isinstance(self.output_dir, Path) or not str(self.output_dir).strip():
            raise ValueError("Ausgabeordner fehlt")
        if not self.explicit_fields <= FIELDS:
            raise ValueError("Unbekannte Einstellungsfelder")

    def set_user_value(self, field: str, value: object) -> "DashboardSettings":
        if field not in FIELDS:
            raise ValueError(f"Unbekanntes Feld: {field}")
        normalized = self._normalize(field, value)
        return replace(self, **{field: normalized}, explicit_fields=self.explicit_fields | {field})

    @staticmethod
    def _normalize(field: str, value: object) -> object:
        if field in {"effect_intensity", "transition_duration"}:
            if isinstance(value, bool):
                raise ValueError(f"Ungültiger Wert für {field}")
            try:
                number = float(value)
            except (TypeError, ValueError, OverflowError) as exc:
                raise ValueError(f"Ungültiger Zahlenwert für {field}") from exc
            if not math.isfinite(number):
                raise ValueError(f"Ungültige Zahl für {field}")
            if field == "effect_intensity":
                if number != int(number) or not 0 <= number <= 100:
                    raise ValueError("Effektstärke: nur ganze Prozent von 0 bis 100")
                return int(number)
            if not 0 <= number <= 5:
                raise ValueError("Blenddauer muss zwischen 0 und 5 Sekunden liegen")
            return round(number, 1)
        if not isinstance(value, (str, Path)):
            raise ValueError(f"Ungültiger Wert für {field}")
        text = str(value).strip()
        if not text:
            raise ValueError(f"Leerer Wert für {field}")
        if field == "resolution":
            return _LEGACY_RESOLUTIONS.get(text, text)
        if field == "quality":
            return _LEGACY_QUALITIES.get(text, text)
        if field == "output_dir":
            return Path(text).expanduser()
        return text

    def apply_preset(self, values: Mapping[str, object]) -> "DashboardSettings":
        if set(values) - FIELDS:
            raise ValueError("Vorlage enthält unbekannte Felder")
        selected = self
        for key, value in values.items():
            if key not in self.explicit_fields:
                selected = replace(selected, **{key: self._normalize(key, value)})
        return selected

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "resolution": self.resolution,
            "quality": self.quality,
            "effect": self.effect,
            "effect_intensity": self.effect_intensity,
            "transition": self.transition,
            "transition_duration": self.transition_duration,
            "output_dir": str(self.output_dir),
            "explicit_fields": sorted(self.explicit_fields),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "DashboardSettings":
        version = payload.get("schema_version", 1)
        if version not in (1, SCHEMA_VERSION):
            raise ValueError("Unbekannte Einstellungs-Version")
        markers = payload.get("explicit_fields", [])
        if not isinstance(markers, (list, tuple, set, frozenset)) or any(not isinstance(x, str) for x in markers):
            raise ValueError("Ungültige Liste der Nutzervorgaben")
        defaults = cls()
        values = {}
        for key in FIELDS:
            value = payload.get(key, getattr(defaults, key))
            values[key] = cls._normalize(key, value)
        return cls(**values, explicit_fields=frozenset(markers))


def load_settings(path: Path | None = None) -> DashboardSettings:
    target = path or settings_path()
    if not target.exists():
        return DashboardSettings()
    with target.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("Ungültige Einstellungsdatei")
    return DashboardSettings.from_dict(payload)


def save_settings(settings: DashboardSettings, path: Path | None = None) -> None:
    """Persist settings with the shared durable-write contract.

    Never truncate the previous file if serialization or writing fails.
    """
    target = path or settings_path()
    atomic_write_json(target, settings.to_dict())
