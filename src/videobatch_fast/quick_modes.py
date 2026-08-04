from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

from .models import BatchOptions, PairJob


@dataclass(frozen=True, slots=True)
class QuickModeSpec:
    key: str
    label: str
    short_label: str
    description: str
    visual_effect: str
    transition: str
    profile: str
    codec: str = "libx264"
    resolution: str = "Original"
    verification: str = "Vollständig"
    speed_class: str = "schnell"
    fallback_mode: str = "maximum_speed"
    adaptive: bool = False
    recommended: bool = False


QUICK_MODES: dict[str, QuickModeSpec] = {
    "smart_auto": QuickModeSpec(
        "smart_auto",
        "Automatisch schnell",
        "AUTO",
        "Empfohlener Standard. Videos werden wenn möglich direkt kopiert; Bilder erhalten automatisch einen klaren, schnellen Techno-Look.",
        "none",
        "none",
        "fast",
        speed_class="maximal bis schnell",
        adaptive=True,
        recommended=True,
    ),
    "maximum_speed": QuickModeSpec(
        "maximum_speed",
        "Maximale Geschwindigkeit",
        "MAX SPEED",
        "Keine visuellen Filter. Kompatible Videos werden ohne Qualitätsverlust direkt kopiert.",
        "none",
        "none",
        "turbo",
        verification="Schnell",
        speed_class="maximal",
    ),
    "techno_clean": QuickModeSpec(
        "techno_clean",
        "Techno Clean",
        "TECHNO",
        "Klarer Kontrast, etwas mehr Farbe und eine kurze weiche Einblendung. Ruhig, modern und sehr schnell.",
        "vivid",
        "soft",
        "fast",
        speed_class="sehr schnell",
    ),
    "hardtechno_impact": QuickModeSpec(
        "hardtechno_impact",
        "HardTechno Impact",
        "HARD",
        "Harter Kontrast, leicht entsättigte Industrieoptik und kurzer weißer Auftakt für druckvolle Tracks.",
        "hardtechno",
        "white_flash",
        "fast",
        speed_class="sehr schnell",
        recommended=True,
    ),
    "industrial_dark": QuickModeSpec(
        "industrial_dark",
        "Industrial Dark",
        "DARK",
        "Dunkler, metallischer Look mit kurzer Schwarzblende. Geeignet für Warehouse- und Industrial-Sets.",
        "industrial",
        "impact_black",
        "fast",
        speed_class="sehr schnell",
    ),
    "acid_neon": QuickModeSpec(
        "acid_neon",
        "Acid Neon",
        "ACID",
        "Giftige Farbverschiebung, kräftige Sättigung und kurzer weißer Impuls. Auffällig, aber weiterhin leicht zu berechnen.",
        "acid",
        "white_flash",
        "fast",
        speed_class="sehr schnell",
    ),
    "bass_pulse": QuickModeSpec(
        "bass_pulse",
        "Bass Pulse",
        "PULSE",
        "Sanft pulsierender Kontrast für mehr Bewegung, ohne aufwendige Beat-Analyse oder zusätzliche Renderstufen.",
        "pulse",
        "impact_black",
        "fast",
        speed_class="schnell",
    ),
    "strobe_safe": QuickModeSpec(
        "strobe_safe",
        "Strobe Safe",
        "STROBE",
        "Sehr milde Helligkeitsimpulse mit begrenzter Stärke. Kein aggressives Vollbildblitzen.",
        "strobe_safe",
        "none",
        "turbo",
        speed_class="sehr schnell",
    ),
    "glitch_light": QuickModeSpec(
        "glitch_light",
        "Glitch Light",
        "GLITCH",
        "Leichte digitale Farbverschiebung und Schärfung. Erzeugt einen Glitch-Eindruck ohne schwere Filtergraphen.",
        "glitch_light",
        "white_flash",
        "fast",
        speed_class="schnell",
    ),
    "monochrome_rave": QuickModeSpec(
        "monochrome_rave",
        "Monochrome Rave",
        "MONO",
        "Kontrastreiches Schwarzweiß mit kurzem dunklem Auftakt. Schnell, rau und clubtauglich.",
        "mono",
        "impact_black",
        "turbo",
        speed_class="sehr schnell",
    ),
    "cold_warehouse": QuickModeSpec(
        "cold_warehouse",
        "Cold Warehouse",
        "COLD",
        "Kühler Blau-Stahl-Look mit dezenter Einblendung. Gut für hypnotischen und reduzierten Techno.",
        "cold",
        "soft",
        "fast",
        speed_class="sehr schnell",
    ),
    "red_alert": QuickModeSpec(
        "red_alert",
        "Red Alert",
        "RED",
        "Warmer Rotakzent, kräftiger Kontrast und kurzer weißer Impuls für aggressive Drop-Momente.",
        "red_alert",
        "white_flash",
        "fast",
        speed_class="sehr schnell",
    ),
    "sharp_stage": QuickModeSpec(
        "sharp_stage",
        "Sharp Stage",
        "SHARP",
        "Dezente Schärfung und kurze Einblendung für Coverbilder, Bühnenfotos und klare Typografie.",
        "sharpen",
        "soft",
        "fast",
        speed_class="schnell",
    ),
    "custom": QuickModeSpec(
        "custom",
        "Eigene Feineinstellung",
        "EIGEN",
        "Nur für erfahrene Nutzer. Effekt, Übergang, Codec und Profil werden manuell gewählt.",
        "none",
        "none",
        "fast",
        speed_class="abhängig von Auswahl",
        fallback_mode="maximum_speed",
    ),
}


def automatic_mode_keys() -> tuple[str, ...]:
    return tuple(key for key in QUICK_MODES if key != "custom")


def mode_spec(key: str) -> QuickModeSpec:
    return QUICK_MODES.get(key, QUICK_MODES["smart_auto"])


def apply_quick_mode(options: BatchOptions, key: str) -> BatchOptions:
    spec = mode_spec(key)
    if spec.key == "custom":
        return replace(options, quick_mode="custom")
    return replace(
        options,
        quick_mode=spec.key,
        visual_effect=spec.visual_effect,
        transition=spec.transition,
        profile=spec.profile,
        codec=spec.codec,
        resolution=spec.resolution,
        verification=spec.verification,
    )


def processing_options_for_job(job: PairJob, options: BatchOptions) -> BatchOptions:
    spec = mode_spec(options.quick_mode)
    if spec.key == "custom":
        return options
    if spec.adaptive:
        if job.media_info.kind == "video":
            return replace(
                options,
                quick_mode=spec.key,
                visual_effect="none",
                transition="none",
                profile="turbo",
                codec="libx264",
                resolution="Original",
                verification="Vollständig",
            )
        return replace(
            options,
            quick_mode=spec.key,
            visual_effect="vivid",
            transition="impact_black",
            profile="fast",
            codec="libx264",
            resolution="Original",
            verification="Vollständig",
        )
    return apply_quick_mode(options, spec.key)


def fallback_options(options: BatchOptions) -> BatchOptions | None:
    spec = mode_spec(options.quick_mode)
    if spec.key in {"maximum_speed", "custom"}:
        return None
    fallback = mode_spec(spec.fallback_mode)
    return apply_quick_mode(options, fallback.key)


def quick_mode_summary(key: str) -> str:
    spec = mode_spec(key)
    recommendation = " · empfohlen" if spec.recommended else ""
    return f"{spec.label}{recommendation} · {spec.speed_class} · automatische sichere Einstellungen"


def validate_quick_modes(
    effect_keys: Iterable[str], transition_keys: Iterable[str], profile_keys: Iterable[str]
) -> list[str]:
    effects = set(effect_keys)
    transitions = set(transition_keys)
    profiles = set(profile_keys)
    errors: list[str] = []
    if len(QUICK_MODES) < 11:
        errors.append("Es müssen mindestens zehn Automatikmodi plus Expertenmodus vorhanden sein.")
    for key, spec in QUICK_MODES.items():
        if key != spec.key:
            errors.append(f"Modusschlüssel stimmt nicht: {key} != {spec.key}")
        if spec.visual_effect not in effects:
            errors.append(f"{key}: unbekannter Effekt {spec.visual_effect}")
        if spec.transition not in transitions:
            errors.append(f"{key}: unbekannter Übergang {spec.transition}")
        if spec.profile not in profiles:
            errors.append(f"{key}: unbekanntes Profil {spec.profile}")
        if spec.fallback_mode not in QUICK_MODES:
            errors.append(f"{key}: unbekannter Fallback {spec.fallback_mode}")
        if not spec.label.strip() or not spec.description.strip():
            errors.append(f"{key}: Beschriftung oder Beschreibung fehlt")
    return errors
