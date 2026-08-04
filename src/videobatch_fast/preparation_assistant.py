from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Iterable

from .quick_modes import QUICK_MODES
from .slideshow import SLIDESHOW_MODE_ALL_IMAGES


@dataclass(frozen=True)
class PreparationCheck:
    key: str
    status: str
    title: str
    detail: str
    action: str = ""


_STATUS_ORDER = {"error": 0, "warning": 1, "ok": 2}


def build_preparation_checks(
    *,
    audios: Iterable[Path],
    media: Iterable[Path],
    output_dir: Path,
    quick_mode: str,
    assignment_mode: str,
    archive_enabled: bool,
    archive_dir: str,
    analysis_pending: bool,
    job_count: int,
) -> list[PreparationCheck]:
    audio_list = list(audios)
    media_list = list(media)
    checks: list[PreparationCheck] = []
    checks.append(PreparationCheck("audio", "ok" if audio_list else "error", "Audiodateien", f"{len(audio_list)} ausgewählt" if audio_list else "Noch keine Audiodatei ausgewählt", "add_audio"))
    checks.append(PreparationCheck("media", "ok" if media_list else "error", "Bilder/Videos", f"{len(media_list)} ausgewählt" if media_list else "Noch kein Bild oder Video ausgewählt", "add_media"))
    target = Path(output_dir).expanduser()
    writable = False
    try:
        writable = target.is_dir() and os.access(target, os.W_OK | os.X_OK)
    except OSError:
        writable = False
    checks.append(PreparationCheck("output", "ok" if writable else "error", "Ausgabeordner", str(target) if writable else "Ziel fehlt oder ist nicht beschreibbar", "choose_output"))
    mode_ok = quick_mode in QUICK_MODES
    checks.append(PreparationCheck("settings", "ok" if mode_ok else "warning", "Einstellungen", "Geprüfter Schnellmodus aktiv" if mode_ok else "Ungültige Werte können automatisch repariert werden", "repair_settings"))
    pairing_ok = job_count > 0
    pairing_detail = f"{job_count} Auftrag/Aufträge vorbereitet" if pairing_ok else "Noch keine gültige Zuordnung"
    pairing_action = "switch_to_slideshow" if audio_list and media_list and assignment_mode != SLIDESHOW_MODE_ALL_IMAGES else "show_pairing"
    checks.append(PreparationCheck("pairing", "ok" if pairing_ok else "error", "Zuordnung", pairing_detail, pairing_action))
    if archive_enabled:
        archive_ok = bool(str(archive_dir or "").strip())
        checks.append(PreparationCheck("archive", "ok" if archive_ok else "warning", "Dateiablage", "Projektordner festgelegt" if archive_ok else "Aufräumen ist aktiv, Zielordner fehlt", "create_project_folder"))
    else:
        checks.append(PreparationCheck("archive", "ok", "Dateiablage", "Für diesen Lauf deaktiviert", ""))
    checks.append(PreparationCheck("analysis", "warning" if analysis_pending else "ok", "Audioanalyse", "Wellenformanalyse läuft noch" if analysis_pending else "Bereit", "focus_waveform" if analysis_pending else ""))
    return sorted(checks, key=lambda item: (_STATUS_ORDER.get(item.status, 9), item.title.casefold()))


def preparation_ready(checks: Iterable[PreparationCheck]) -> bool:
    return all(item.status != "error" for item in checks)
