from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from .models import PairJob
from .probe import ffmpeg_path, ffprobe_path


def _stream_duration(stream: dict[str, Any]) -> float | None:
    try:
        value = float(stream.get("duration") or 0)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _decode_output(path: Path, duration: float) -> tuple[bool, str]:
    binary = ffmpeg_path()
    if not binary:
        return False, "FFmpeg fehlt für die vollständige Dekodierprüfung."
    timeout = max(45.0, min(900.0, 60.0 + duration * 0.75))
    command = [
        binary,
        "-hide_banner",
        "-v",
        "error",
        "-xerror",
        "-i",
        str(path),
        "-map",
        "0:v:0",
        "-map",
        "0:a:0",
        "-f",
        "null",
        "-",
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            errors="replace",
        )
    except subprocess.TimeoutExpired:
        return False, f"Die vollständige Dekodierprüfung überschritt {timeout:.0f} Sekunden."
    except OSError as exc:
        return False, f"Die vollständige Dekodierprüfung konnte nicht gestartet werden: {exc}"
    if result.returncode != 0:
        details = (result.stderr or result.stdout or "unbekannter Dekodierfehler").strip().splitlines()
        return False, f"Dekodierfehler: {(details[-1] if details else 'unbekannt')[:400]}"
    return True, "vollständig dekodiert"


def verify_output(path: Path, job: PairJob, mode: str = "Schnell") -> tuple[bool, str]:
    if not path.is_file() or path.stat().st_size < 4096:
        return False, "Ausgabedatei fehlt oder ist zu klein."
    binary = ffprobe_path()
    if not binary:
        return False, "FFprobe fehlt."
    entries = "format=duration:stream=codec_type,codec_name,width,height,duration"
    try:
        result = subprocess.run(
            [binary, "-v", "error", "-show_entries", entries, "-of", "json", str(path)],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
            errors="replace",
        )
        payload = json.loads(result.stdout or "{}")
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        return False, "Die Ausgabedatei konnte nicht geprüft werden."
    streams = payload.get("streams") or []
    streams = [stream for stream in streams if isinstance(stream, dict)]
    kinds = {stream.get("codec_type") for stream in streams}
    if not {"audio", "video"}.issubset(kinds):
        return False, "Audio- oder Videostream fehlt."
    try:
        duration = float((payload.get("format") or {}).get("duration") or 0)
    except (TypeError, ValueError):
        duration = 0
    expected = job.audio_info.duration or 0
    if duration <= 0:
        return False, "Die Ausgabedauer ist ungültig."
    if expected and duration < max(0.2, expected * 0.94):
        return False, f"Die Ausgabe ist zu kurz ({duration:.1f} statt {expected:.1f} Sekunden)."
    if expected and duration > expected * 1.08 + 0.5:
        return False, f"Die Ausgabe ist unerwartet lang ({duration:.1f} statt {expected:.1f} Sekunden)."
    stream_durations = [_stream_duration(stream) for stream in streams]
    known_stream_durations = [value for value in stream_durations if value is not None]
    if len(known_stream_durations) >= 2 and max(known_stream_durations) - min(known_stream_durations) > max(1.0, duration * 0.03):
        return False, "Audio- und Videostream enden deutlich unterschiedlich."
    if mode == "Vollständig":
        if path.stat().st_size < 50_000:
            return False, "Die Datei ist für eine vollständige Ausgabe ungewöhnlich klein."
        decoded, decode_message = _decode_output(path, duration)
        if not decoded:
            return False, decode_message
        return True, f"Video und Audio vorhanden · Dauer {duration:.1f} Sekunden · {decode_message}."
    return True, f"Video und Audio vorhanden · Dauer {duration:.1f} Sekunden."
