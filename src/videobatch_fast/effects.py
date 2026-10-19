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


def effect_filter(effect_key: str, intensity: int = 100) -> str | None:
    """Render the existing look at 0..100 percent without changing legacy 100% filters."""
    spec = VISUAL_EFFECTS.get(effect_key, VISUAL_EFFECTS["none"])
    if not spec.filter_expression:
        return None
    strength = max(0.0, min(1.0, float(intensity) / 100.0))
    if strength <= 0.0:
        return None
    if strength >= 1.0:
        return spec.filter_expression

    def n(value: float) -> str:
        return f"{value:.4f}"

    if effect_key == "vivid":
        return f"eq=contrast={n(1 + .06*strength)}:saturation={n(1 + .08*strength)}"
    if effect_key == "mono":
        return f"hue=s={n(1-strength)},eq=contrast={n(1+.10*strength)}"
    if effect_key == "sharpen":
        return f"unsharp=5:5:{n(.45*strength)}:5:5:0.0"
    if effect_key == "vignette":
        return f"vignette=PI/{n(5.0/strength)}"
    if effect_key == "hardtechno":
        return (f"eq=contrast={n(1+.18*strength)}:saturation={n(1-.18*strength)}:"
                f"brightness={n(-.025*strength)},unsharp=3:3:{n(.25*strength)}:3:3:0.0")
    if effect_key == "industrial":
        return (f"eq=contrast={n(1+.16*strength)}:saturation={n(1-.35*strength)}:"
                f"brightness={n(-.045*strength)}")
    if effect_key == "acid":
        return f"hue=h={n(18*strength)}:s={n(1+.35*strength)},eq=contrast={n(1+.08*strength)}"
    if effect_key == "pulse":
        return (f"eq=contrast='1+{n(.10*strength)}+{n(.05*strength)}*sin(2*PI*t*2)':"
                f"saturation={n(1+.12*strength)}:eval=frame")
    if effect_key == "strobe_safe":
        return f"eq=brightness='{n(.025*strength)}*sin(2*PI*t*4)':contrast={n(1+.10*strength)}:eval=frame"
    if effect_key == "glitch_light":
        return (f"hue=h={n(6*strength)}:s={n(1+.20*strength)},"
                f"eq=contrast={n(1+.10*strength)},unsharp=3:3:{n(.20*strength)}:3:3:0.0")
    if effect_key == "cold":
        return f"colorbalance=bs={n(.10*strength)}:rs={n(-.04*strength)},eq=contrast={n(1+.08*strength)}"
    if effect_key == "red_alert":
        return f"colorbalance=rs={n(.10*strength)}:bs={n(-.05*strength)},eq=contrast={n(1+.12*strength)}"
    return spec.filter_expression


def transition_filters(
    transition_key: str, duration: float | None, requested_seconds: float | None = None
) -> list[str]:
    spec = TRANSITIONS.get(transition_key, TRANSITIONS["none"])
    if spec.duration <= 0:
        return []
    fade_duration = spec.duration if requested_seconds is None else max(0.0, min(5.0, float(requested_seconds)))
    if duration is not None and duration > 0 and requested_seconds is not None:
        fade_duration = min(fade_duration, duration / 2.0)
    if fade_duration <= 0:
        return []
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
