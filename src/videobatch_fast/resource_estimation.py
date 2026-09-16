from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from .models import BatchOptions, PairJob
from .quick_modes import processing_options_for_job

_MIB = 1024**2
_MIN_VIDEO_BYTES_PER_SECOND = 1_200_000
_MIN_JOB_HEADROOM = 64 * _MIB
_MIN_DIRECTORY_HEADROOM = 512 * _MIB
_BATCH_HEADROOM_RATIO = 0.20
_RESOLUTION_RE = re.compile(r"^\s*(\d+)\s*[×xX]\s*(\d+)\s*$")

_CODEC_FACTORS = {
    "libx264": 1.00,
    "h264": 1.00,
    "libx265": 0.82,
    "hevc": 0.82,
    "libaom-av1": 0.76,
    "av1": 0.76,
    "mpeg4": 1.35,
}
_PROFILE_FACTORS = {
    "turbo": 1.00,
    "fast": 1.08,
    "balanced": 1.16,
    "quality": 1.32,
}


def _audio_bytes_per_second(value: str) -> int:
    text = str(value or "").strip().lower()
    try:
        if text.endswith("k"):
            return max(0, int(float(text[:-1]) * 1000 / 8))
        if text.endswith("m"):
            return max(0, int(float(text[:-1]) * 1_000_000 / 8))
        return max(0, int(float(text) / 8))
    except (TypeError, ValueError, OverflowError):
        return 24_000  # 192 kbit/s fallback


def _target_pixels(job: PairJob, resolution: str) -> int:
    if resolution and resolution != "Original":
        match = _RESOLUTION_RE.match(resolution)
        if match:
            return max(1, int(match.group(1)) * int(match.group(2)))
    width = int(job.media_info.width or 0)
    height = int(job.media_info.height or 0)
    if width > 0 and height > 0:
        return width * height
    # Unknown image dimensions must not make the safety estimate artificially tiny.
    return 1280 * 720


def estimate_job_output_bytes(job: PairJob, options: BatchOptions) -> int:
    """Return a deliberately conservative output-space estimate for one job.

    The estimate is not meant to predict the final file size exactly. Its job is
    to avoid starting renders that are likely to exhaust the destination while
    CRF encoding is still in progress.
    """
    selected = processing_options_for_job(job, options)
    duration = max(1.0, float(job.audio_info.duration or 60.0))
    pixels = _target_pixels(job, selected.resolution)
    pixel_factor = max(0.55, pixels / float(1280 * 720))
    fps_factor = max(0.75, float(max(1, selected.fps)) / 25.0)
    codec_factor = _CODEC_FACTORS.get(str(selected.codec).lower(), 1.15)
    profile_factor = _PROFILE_FACTORS.get(str(selected.profile).lower(), 1.20)

    video_rate = int(
        _MIN_VIDEO_BYTES_PER_SECOND
        * pixel_factor
        * fps_factor
        * codec_factor
        * profile_factor
    )
    video_rate = max(_MIN_VIDEO_BYTES_PER_SECOND, video_rate)
    audio_rate = _audio_bytes_per_second(selected.audio_bitrate)
    encoded_estimate = int(duration * (video_rate + audio_rate))

    # Fast-copy output can be driven more by the existing video stream than by
    # the model above. Never estimate below the known source size in that case.
    if job.fast_path and job.media_info.size_bytes > 0:
        encoded_estimate = max(
            encoded_estimate,
            int(job.media_info.size_bytes + duration * audio_rate),
        )

    return encoded_estimate + _MIN_JOB_HEADROOM


def estimate_required_by_directory(
    jobs: list[PairJob], options: BatchOptions
) -> dict[Path, int]:
    """Group conservative storage requirements by actual output directory."""
    grouped: dict[Path, int] = defaultdict(int)
    for job in jobs:
        grouped[Path(job.output).expanduser().parent] += estimate_job_output_bytes(job, options)

    required: dict[Path, int] = {}
    for directory, estimated in grouped.items():
        batch_headroom = max(_MIN_DIRECTORY_HEADROOM, int(estimated * _BATCH_HEADROOM_RATIO))
        required[directory] = estimated + batch_headroom
    return required
