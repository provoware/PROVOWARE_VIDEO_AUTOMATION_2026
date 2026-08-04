from __future__ import annotations

import json
import os
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

from .models import MediaInfo

AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg", ".opus"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".webm", ".avi", ".m4v", ".ts"}


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
        return MediaInfo(path, classify_extension(path), size_bytes=size)
    command = [
        binary, "-v", "error", "-show_entries",
        "format=duration:stream=index,codec_type,codec_name,width,height,duration",
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
    streams = streams if isinstance(streams, list) else []
    video = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    audio = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
    extension_kind = classify_extension(path)
    kind = "video" if video else "audio" if audio else extension_kind
    if extension_kind == "image" and video:
        kind = "image"
    duration_value = (payload.get("format") or {}).get("duration")
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
    return MediaInfo(
        path=path,
        kind=kind,
        duration=duration,
        codec=str(stream.get("codec_name") or ""),
        width=int(stream["width"]) if stream.get("width") else None,
        height=int(stream["height"]) if stream.get("height") else None,
        size_bytes=size,
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
