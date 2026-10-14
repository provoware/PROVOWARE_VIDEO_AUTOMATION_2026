"""Pure-Python state contract for the always-visible VideoBatch controls.

This module intentionally does not touch the renderer or existing saved settings.
Integration into Qt and BatchOptions is a separate gated change.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Mapping

SCHEMA_VERSION = 1
RESOLUTIONS = ("Original", "HD", "Full HD", "QHD", "UHD")
QUALITIES = ("Schnell", "Ausgewogen", "Hoch", "Maximum")
FIELDS = frozenset({"resolution", "quality", "effect", "output_dir"})


@dataclass(frozen=True)
class DashboardSettings:
    resolution: str = "Original"
    quality: str = "Ausgewogen"
    effect: str = "none"
    output_dir: Path = Path.home() / "Videos" / "VideoBatch"
    explicit_fields: frozenset[str] = frozenset()
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("Unbekannte Einstellungs-Version")
        if self.resolution not in RESOLUTIONS:
            raise ValueError("Unbekannte Auflösung")
        if self.quality not in QUALITIES:
            raise ValueError("Unbekannte Qualitätsstufe")
        if not isinstance(self.effect, str) or not self.effect.strip():
            raise ValueError("Effekt darf nicht leer sein")
        if not str(self.output_dir).strip():
            raise ValueError("Ausgabeordner darf nicht leer sein")
        if not self.explicit_fields <= FIELDS:
            raise ValueError("Unbekannte Einstellungsfelder")

    def set_user_value(self, field: str, value: object) -> "DashboardSettings":
        if field not in FIELDS:
            raise ValueError(f"Nicht unterstütztes Feld: {field}")
        if field == "output_dir":
            if not str(value).strip():
                raise ValueError("Ausgabeordner darf nicht leer sein")
            value = Path(str(value)).expanduser()
        return replace(self, **{field: value}, explicit_fields=self.explicit_fields | {field})

    def apply_preset(self, values: Mapping[str, object]) -> "DashboardSettings":
        """A preset fills non-explicit fields; it never silently overwrites user choices."""
        unknown = set(values) - FIELDS
        if unknown:
            raise ValueError(f"Unbekannte Vorlagenfelder: {sorted(unknown)}")
        updated = self
        for field, value in values.items():
            if field not in updated.explicit_fields:
                updated = replace(updated, **{field: Path(str(value)).expanduser() if field == "output_dir" else value})
        return updated

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "resolution": self.resolution,
            "quality": self.quality,
            "effect": self.effect,
            "output_dir": str(self.output_dir),
            "explicit_fields": sorted(self.explicit_fields),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "DashboardSettings":
        if int(payload.get("schema_version", 1)) != SCHEMA_VERSION:
            raise ValueError("Unbekannte Einstellungs-Version")
        fields = payload.get("explicit_fields", ())
        if not isinstance(fields, (list, tuple, set, frozenset)) or not all(isinstance(x, str) for x in fields):
            raise ValueError("Ungültige Liste expliziter Einstellungen")
        return cls(
            resolution=str(payload.get("resolution", "Original")),
            quality=str(payload.get("quality", "Ausgewogen")),
            effect=str(payload.get("effect", "none")),
            output_dir=Path(str(payload.get("output_dir", Path.home() / "Videos" / "VideoBatch"))).expanduser(),
            explicit_fields=frozenset(fields),
        )
