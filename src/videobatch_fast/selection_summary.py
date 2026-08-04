from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .probe import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS
from .slideshow import SLIDESHOW_MODE_ALL_IMAGES


def build_selection_summary(
    audios: Iterable[Path],
    media: Iterable[Path],
    *,
    job_count: int,
    assignment_mode: str,
    transition: str,
    scene_sync: bool,
    quick_mode_label: str,
) -> str:
    """Return a compact, always-readable summary for the global header."""
    audio_count = sum(1 for _ in audios)
    media_paths = tuple(media)
    image_count = sum(1 for path in media_paths if path.suffix.lower() in IMAGE_EXTENSIONS)
    video_count = sum(1 for path in media_paths if path.suffix.lower() in VIDEO_EXTENSIONS)
    mode = "Diashow" if assignment_mode == SLIDESHOW_MODE_ALL_IMAGES else "1:1"
    transition_label = {
        "auto": "automatisch",
        "none": "ohne",
        "soft": "sanft",
        "clear": "deutlich",
    }.get(transition, transition or "automatisch")
    scene_label = "Szenen an" if scene_sync else "Szenen aus"
    audio_label = "Audio" if audio_count == 1 else "Audios"
    image_label = "Bild" if image_count == 1 else "Bilder"
    video_label = "Video" if video_count == 1 else "Videos"
    job_label = "Auftrag" if job_count == 1 else "Aufträge"
    return (
        f"{audio_count} {audio_label} · {image_count} {image_label} · {video_count} {video_label} · "
        f"{job_count} {job_label}  |  {mode} · Wechsel {transition_label} · "
        f"{scene_label} · {quick_mode_label}"
    )
