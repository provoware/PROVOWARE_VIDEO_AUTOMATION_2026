from __future__ import annotations

import json
import math
import os
import re
from fractions import Fraction
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

from .models import MediaInfo

AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg", ".opus", ".wma", ".aif", ".aiff", ".ape", ".wv"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".avif", ".gif", ".heic", ".heif"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".webm", ".avi", ".m4v", ".ts", ".mpeg", ".mpg", ".wmv", ".3gp", ".mts", ".m2ts", ".ogv"}


def _configured_binary(environment_name: str, fallback_name: str) -> str:
    configured = os.environ.get(environment_name, "").strip()
    if configured:
        path = Path(configured).expanduser()
        if path.is_file() and os.access(path, os.X_OK):
            return str(path)
    return shutil.which(fallback_name) or ""


def ffmpeg_path() -> str:
    return _configured_binary("VIDEOBATCH_FFMPEG", "ffmpeg")


def ffprobe_path() -> str:
    return _configured_binary("VIDEOBATCH_FFPROBE", "ffprobe")


def classify_extension(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in AUDIO_EXTENSIONS:
        return "audio"
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    return "unknown"


@lru_cache(maxsize=1024)
def probe_media_cached(path_text: str, mtime_ns: int, size: int) -> MediaInfo:
    path = Path(path_text)
    binary = ffprobe_path()
    if not binary:
        # An extension is only a hint.  Without ffprobe no content validation
        # happened, so callers must not treat a damaged file as valid media.
        return MediaInfo(path, "unknown", size_bytes=size)
    command = [
        binary, "-v", "error", "-show_entries",
        "format=duration:stream=index,codec_type,codec_name,width,height,duration,avg_frame_rate,r_frame_rate",
        "-of", "json", str(path),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=20, check=True, errors="replace")
        payload = json.loads(result.stdout or "{}")
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError, ValueError):
        # Sobald ffprobe vorhanden ist, darf eine fehlgeschlagene Inhaltsprüfung
        # nicht durch die bloße Dateiendung als gültiges Medium erscheinen.
        return MediaInfo(path, "unknown", size_bytes=size)
    streams = payload.get("streams") if isinstance(payload, dict) else []
    streams = [stream for stream in streams if isinstance(stream, dict)] if isinstance(streams, list) else []
    video = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    audio = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
    extension_kind = classify_extension(path)
    # An extension alone is not proof of readable media. FFprobe returned no
    # usable track, so the input must fail the ordinary media validation.
    kind = "video" if video else "audio" if audio else "unknown"
    if extension_kind == "image" and video:
        kind = "image"
    format_info = payload.get("format") if isinstance(payload, dict) else {}
    format_info = format_info if isinstance(format_info, dict) else {}
    duration_value = format_info.get("duration")
    if duration_value in {None, "N/A", ""}:
        stream = audio or video or {}
        duration_value = stream.get("duration")
    try:
        duration = float(duration_value)
        if duration <= 0:
            duration = None
    except (TypeError, ValueError):
        duration = None
    stream = video or audio or {}
    rate_differs = _variable_frame_rate(video, kind)
    return MediaInfo(
        path=path,
        kind=kind,
        duration=duration,
        codec=str(stream.get("codec_name") or ""),
        width=int(stream["width"]) if stream.get("width") else None,
        height=int(stream["height"]) if stream.get("height") else None,
        size_bytes=size,
        variable_frame_rate=rate_differs,
    )


def probe_media(path: Path) -> MediaInfo:
    path = Path(path)
    try:
        stat = path.stat()
    except OSError:
        return MediaInfo(path, "unknown")
    return probe_media_cached(str(path.resolve()), stat.st_mtime_ns, stat.st_size)


def ffmpeg_version() -> str:
    binary = ffmpeg_path()
    if not binary:
        return "nicht gefunden"
    try:
        result = subprocess.run([binary, "-version"], capture_output=True, text=True, timeout=5, errors="replace")
        first = (result.stdout or "").splitlines()[0]
        return first.replace("ffmpeg version ", "").split(" Copyright", 1)[0]
    except (OSError, subprocess.SubprocessError):
        return "unbekannt"

@lru_cache(maxsize=256)
def sample_audio_peak(path_text: str, modified_ns: int, size: int) -> float | None:
    """Measure at most the opening six seconds; never claim a whole-song scan.

    The function is cached by file identity and has a strict subprocess timeout.
    It only reads the source and writes decoded samples to FFmpeg's null sink.
    """
    del modified_ns, size  # Cache key is intentional; nothing is written to the source.
    binary = ffmpeg_path()
    if not binary:
        return None
    command = [
        binary, "-hide_banner", "-nostdin", "-v", "info", "-t", "6",
        "-i", path_text, "-map", "0:a:0", "-vn",
        "-af", "volumedetect", "-f", "null", "-",
    ]
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, timeout=12,
            check=False, errors="replace",
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    match = re.search(r"max_volume:\s*(-?[\d.]+)\s*dB", completed.stderr or "")
    if not match:
        return None
    try:
        peak = float(match.group(1))
    except ValueError:
        return None
    return peak if math.isfinite(peak) and -200 <= peak <= 20 else None


def sampled_audio_peak(path: Path) -> float | None:
    """Read a bounded audio sample without modifying the file."""
    try:
        stat = Path(path).stat()
    except OSError:
        return None
    return sample_audio_peak(str(Path(path).resolve()), stat.st_mtime_ns, stat.st_size)


def _variable_frame_rate(video: dict | None, kind: str) -> bool:
    rate_differs = False
    if video and kind == "video":
        try:
            nominal = float(Fraction(str(video.get("r_frame_rate", "0/1"))))
            average = float(Fraction(str(video.get("avg_frame_rate", "0/1"))))
            rate_differs = (
                math.isfinite(nominal) and math.isfinite(average)
                and nominal > 0 and average > 0
                and abs(nominal - average) / nominal > 0.08
            )
        except (ValueError, ZeroDivisionError, OverflowError):
            rate_differs = False
    return rate_differs
