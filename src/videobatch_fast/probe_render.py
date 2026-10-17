"""Small first-pair preview through the existing verified batch runner.

Preview output is isolated from the user's configured output directory.
Only pairwise jobs with known audio duration are eligible.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import replace
from pathlib import Path

from .models import BatchOptions, PairJob
from .paths import cache_dir

MAX_PREVIEW_SECONDS = 10.0
PREVIEW_PREFIX = "vb-probe-"


def plan_probe(job: PairJob, options: BatchOptions, destination: Path) -> tuple[PairJob, BatchOptions]:
    if job.is_slideshow:
        raise ValueError("Für eine Diashow ist diese kurze Paarvorschau nicht geeignet.")
    if not job.audio_info.duration or job.audio_info.duration <= 0:
        raise ValueError("Die Audiodauer konnte nicht bestimmt werden.")
    if not destination.is_absolute() or destination.suffix.lower() != ".mp4":
        raise ValueError("Ungültiger Probevideo-Zielpfad.")
    target = min(float(job.audio_info.duration), MAX_PREVIEW_SECONDS)
    preview_job = replace(
        job,
        index=1,
        output=destination,
        audio_info=replace(job.audio_info, duration=target),
        fast_path=False,
        reason="Kurzprobe – separate Ausgabe, keine Originaländerung",
    )
    preview_options = replace(
        options, output_dir=destination.parent, quick_mode="custom",
        assignment_mode="pairwise", overwrite=False,
    )
    return preview_job, preview_options


def probe_output() -> Path:
    directory = cache_dir() / "probevideos"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / (PREVIEW_PREFIX + str(time.time_ns()) + "-" + uuid.uuid4().hex[:8] + ".mp4")


def prune_probes(directory: Path, *, keep: int = 10) -> int:
    """Remove only old, regular preview artifacts with our own filename prefix."""
    directory = Path(directory)
    if not directory.exists():
        return 0
    entries: list[tuple[int, Path]] = []
    for entry in directory.iterdir():
        if entry.is_symlink() or not entry.is_file():
            continue
        if not entry.name.startswith(PREVIEW_PREFIX) or entry.suffix.lower() != ".mp4":
            continue
        try:
            entries.append((entry.stat().st_mtime_ns, entry))
        except OSError:
            continue
    removed = 0
    for _, old in sorted(entries, reverse=True)[max(0, keep):]:
        try:
            old.unlink()
            removed += 1
        except OSError:
            continue
    return removed
