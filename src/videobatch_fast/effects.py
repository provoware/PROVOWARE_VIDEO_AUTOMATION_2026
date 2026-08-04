from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EffectSpec:
    key: str
    label: str
    description: str
    filter_expression: str | None
    speed_class: str


@dataclass(frozen=True, slots=True)
class TransitionSpec:
    key: str
    label: str
    description: str
    duration: float
    speed_class: str
    color: str = "black"


VISUAL_EFFECTS: dict[str, EffectSpec] = {
    "none": EffectSpec("none", "Keine", "Schnellste Variante. Kompatible Videos können direkt kopiert werden.", None, "maximal"),
    "vivid": EffectSpec("vivid", "Klar & kräftig", "Leicht mehr Kontrast und Farbsättigung.", "eq=contrast=1.06:saturation=1.08", "sehr schnell"),
    "mono": EffectSpec("mono", "Schwarzweiß", "Kontraststarker monochromer Rave-Look.", "hue=s=0,eq=contrast=1.10", "sehr schnell"),
    "sharpen": EffectSpec("sharpen", "Sanft schärfen", "Dezente Schärfung für Cover, Fotos und Typografie.", "unsharp=5:5:0.45:5:5:0.0", "schnell"),
    "vignette": EffectSpec("vignette", "Sanfte Vignette", "Dunkelt die Bildränder leicht ab.", "vignette=PI/5", "schnell"),
    "hardtechno": EffectSpec("hardtechno", "HardTechno-Kontrast", "Harter, leicht entsättigter Industrie-Look.", "eq=contrast=1.18:saturation=0.82:brightness=-0.025,unsharp=3:3:0.25:3:3:0.0", "sehr schnell"),
    "industrial": EffectSpec("industrial", "Industrial Dark", "Dunkler metallischer Look ohne schwere Filter.", "eq=contrast=1.16:saturation=0.65:brightness=-0.045", "sehr schnell"),
    "acid": EffectSpec("acid", "Acid Neon", "Statische Neon-Farbverschiebung mit kräftiger Sättigung.", "hue=h=18:s=1.35,eq=contrast=1.08", "sehr schnell"),
    "pulse": EffectSpec("pulse", "Bass Pulse", "Sanft pulsierender Kontrast ohne Beat-Analyse.", "eq=contrast='1.10+0.05*sin(2*PI*t*2)':saturation=1.12:eval=frame", "schnell"),
    "strobe_safe": EffectSpec("strobe_safe", "Strobe Safe", "Sehr milde, begrenzte Helligkeitsimpulse.", "eq=brightness='0.025*sin(2*PI*t*4)':contrast=1.10:eval=frame", "sehr schnell"),
    "glitch_light": EffectSpec("glitch_light", "Glitch Light", "Leichte digitale Farbverschiebung und Schärfung.", "hue=h=6:s=1.20,eq=contrast=1.10,unsharp=3:3:0.20:3:3:0.0", "schnell"),
    "cold": EffectSpec("cold", "Cold Warehouse", "Kühler Blau-Stahl-Look.", "colorbalance=bs=0.10:rs=-0.04,eq=contrast=1.08", "sehr schnell"),
    "red_alert": EffectSpec("red_alert", "Red Alert", "Warmer Rotakzent mit kräftigem Kontrast.", "colorbalance=rs=0.10:bs=-0.05,eq=contrast=1.12", "sehr schnell"),
}


TRANSITIONS: dict[str, TransitionSpec] = {
    "none": TransitionSpec("none", "Keine", "Keine Ein- oder Ausblendung.", 0.0, "maximal"),
    "soft": TransitionSpec("soft", "Kurze weiche Blende", "Unaufdringliche Ein- und Ausblendung.", 0.25, "sehr schnell"),
    "cinema": TransitionSpec("cinema", "Ruhige Kinoblende", "Längere dunkle Ein- und Ausblendung.", 0.8, "sehr schnell"),
    "white_flash": TransitionSpec("white_flash", "Kurzer White Flash", "Sehr kurzer weißer Auftakt und Abschluss.", 0.10, "sehr schnell", "white"),
    "impact_black": TransitionSpec("impact_black", "Kurzer Black Impact", "Kurzer dunkler Auftakt und Abschluss.", 0.12, "sehr schnell", "black"),
}


def effect_filter(effect_key: str) -> str | None:
    return VISUAL_EFFECTS.get(effect_key, VISUAL_EFFECTS["none"]).filter_expression


def transition_filters(transition_key: str, duration: float | None) -> list[str]:
    spec = TRANSITIONS.get(transition_key, TRANSITIONS["none"])
    if spec.duration <= 0:
        return []
    fade_duration = spec.duration
    filters = [f"fade=t=in:st=0:d={fade_duration:.3f}:color={spec.color}"]
    if duration and duration > fade_duration:
        start = max(0.0, duration - fade_duration)
        filters.append(f"fade=t=out:st={start:.3f}:d={fade_duration:.3f}:color={spec.color}")
    return filters


def speed_summary(effect_key: str, transition_key: str) -> str:
    effect = VISUAL_EFFECTS.get(effect_key, VISUAL_EFFECTS["none"])
    transition = TRANSITIONS.get(transition_key, TRANSITIONS["none"])
    if effect.key == "none" and transition.key == "none":
        return "Direktkopie bleibt möglich · maximale Geschwindigkeit"
    labels = []
    if effect.key != "none":
        labels.append(effect.label)
    if transition.key != "none":
        labels.append(transition.label)
    return f"{' + '.join(labels)} · schneller 1-Pass-Render · keine Zwischenrenderings"
