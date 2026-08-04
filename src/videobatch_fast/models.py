from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

MediaKind = Literal["audio", "image", "video", "unknown"]


@dataclass(frozen=True, slots=True)
class MediaInfo:
    path: Path
    kind: MediaKind
    duration: float | None = None
    codec: str = ""
    width: int | None = None
    height: int | None = None
    size_bytes: int = 0


@dataclass(frozen=True, slots=True)
class PairJob:
    index: int
    audio: Path
    media: Path
    output: Path
    audio_info: MediaInfo
    media_info: MediaInfo
    fast_path: bool
    reason: str
    media_sequence: tuple[Path, ...] = ()
    slide_duration: float | None = None
    slide_transition: float = 0.0
    slide_durations: tuple[float, ...] = ()
    slide_change_points: tuple[float, ...] = ()
    scene_markers: tuple[tuple[str, float, str, float], ...] = ()

    @property
    def is_slideshow(self) -> bool:
        return bool(self.media_sequence)

    @property
    def source_media(self) -> tuple[Path, ...]:
        return self.media_sequence or (self.media,)


@dataclass(frozen=True, slots=True)
class EncodeProfile:
    key: str
    label: str
    preset: str
    crf: int
    description: str


@dataclass(frozen=True, slots=True)
class BatchOptions:
    output_dir: Path
    output_mode: str = "Gemeinsamer Ordner"
    resolution: str = "Original"
    codec: str = "libx264"
    profile: str = "fast"
    verification: str = "Schnell"
    overwrite: bool = False
    keep_lists: bool = True
    audio_bitrate: str = "192k"
    fps: int = 25
    max_threads: int = 0
    visual_effect: str = "none"
    transition: str = "none"
    quick_mode: str = "custom"
    assignment_mode: str = "pairwise"
    slideshow_transition: str = "auto"
    slideshow_scene_sync: bool = False


@dataclass(slots=True)
class ProgressSnapshot:
    job_index: int = 0
    job_total: int = 0
    job_percent: float = 0.0
    total_percent: float = 0.0
    phase: str = "Wartet"
    elapsed_seconds: float = 0.0
    eta_seconds: float | None = None
    speed: str = ""
    frame: int | None = None
    fps: float | None = None
    output_size: int = 0
    last_activity_seconds: float = 0.0
    detail: str = ""


@dataclass(slots=True)
class JobResult:
    job: PairJob
    success: bool
    returncode: int
    elapsed_seconds: float
    message: str
    retried: bool = False
    command: list[str] = field(default_factory=list)
    fallback_mode: str = ""
