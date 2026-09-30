from __future__ import annotations


QUALITY_TARGETS = {
    "smart_auto": "Ausgewogene Empfehlung für Qualität und Tempo",
    "maximum_speed": "Kürzeste Verarbeitungszeit und möglichst direktes Kopieren",
    "techno_clean": "Klarer, farbiger Look bei sehr kurzer Renderzeit",
    "hardtechno_impact": "Druckvoller Kontrast für harte Tracks",
    "industrial_dark": "Dunkler, metallischer Warehouse-Look",
    "acid_neon": "Maximale Farbwirkung mit leichtem Renderprofil",
    "bass_pulse": "Mehr Bewegung ohne aufwendige Beat-Analyse",
    "strobe_safe": "Milde Helligkeitsimpulse statt aggressivem Blitzen",
    "glitch_light": "Digitaler Glitch-Look mit moderatem Aufwand",
    "monochrome_rave": "Kontrastreiches Schwarzweiß und kleine Renderlast",
    "cold_warehouse": "Kühler, zurückhaltender Club-Look",
    "red_alert": "Warmer, aggressiver Rotakzent",
    "sharp_stage": "Klare Details für Cover und Bühnenfotos",
    "custom": "Eigene Parameter für erfahrene Nutzer",
}


def quality_target(key: str) -> str:
    return QUALITY_TARGETS.get(key, "Zielprofil nicht verfügbar")


def format_clock(seconds: float) -> str:
    total = max(0, int(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def format_size(size: int) -> str:
    value = max(0.0, float(size))
    for unit in ("B", "KiB", "MiB", "GiB"):
        if value < 1024 or unit == "GiB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return "0.0 B"


def format_eta(eta: object, elapsed: float, job_percent: int) -> str:
    if eta is None:
        return "wird berechnet" if elapsed < 15 else "nicht verfügbar"
    label = "erste Schätzung" if elapsed < 20 or job_percent < 10 else "aktuelle Schätzung"
    return f"{label} · ca. {format_clock(float(eta))}"
