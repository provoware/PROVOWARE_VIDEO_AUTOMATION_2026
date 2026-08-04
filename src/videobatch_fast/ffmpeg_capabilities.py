from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from functools import lru_cache

from .effects import effect_filter, transition_filters
from .probe import ffmpeg_path


@dataclass(frozen=True, slots=True)
class FfmpegCapabilities:
    binary: str
    encoders: frozenset[str]
    filters: frozenset[str]
    error: str = ""

    def supports_encoder(self, name: str) -> bool:
        return name in self.encoders

    def supports_filters(self, names: set[str]) -> bool:
        return names.issubset(self.filters)


def _run_listing(binary: str, argument: str) -> str:
    result = subprocess.run(
        [binary, "-hide_banner", argument],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
        errors="replace",
    )
    output = "\n".join(part for part in (result.stdout, result.stderr) if part)
    if result.returncode != 0 or not output.strip():
        raise RuntimeError(f"FFmpeg-Fähigkeitsliste {argument} konnte nicht gelesen werden.")
    return output


def _parse_encoders(output: str) -> frozenset[str]:
    values: set[str] = set()
    for line in output.splitlines():
        match = re.match(r"^\s*[VAS][A-Z\.]{5}\s+([^\s]+)", line)
        if match:
            values.add(match.group(1))
    return frozenset(values)


def _parse_filters(output: str) -> frozenset[str]:
    values: set[str] = set()
    for line in output.splitlines():
        match = re.match(r"^\s*[A-Z\.]{3}\s+([^\s]+)", line)
        if match:
            values.add(match.group(1))
    return frozenset(values)


@lru_cache(maxsize=4)
def read_ffmpeg_capabilities(binary: str | None = None) -> FfmpegCapabilities:
    resolved = binary or ffmpeg_path()
    if not resolved:
        return FfmpegCapabilities("", frozenset(), frozenset(), "FFmpeg fehlt.")
    try:
        encoders = _parse_encoders(_run_listing(resolved, "-encoders"))
        filters = _parse_filters(_run_listing(resolved, "-filters"))
    except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
        return FfmpegCapabilities(resolved, frozenset(), frozenset(), str(exc))
    return FfmpegCapabilities(resolved, encoders, filters)



@lru_cache(maxsize=16)
def encoder_smoke_test(binary: str, encoder: str, media_type: str = "audio") -> tuple[bool, str]:
    """Verify an encoder by running a tiny real encode.

    FFmpeg's listing flags differ between builds and versions.  Startup must not
    be blocked by a parser assumption, so the actual executable is authoritative.
    """
    if media_type == "audio":
        source = ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-frames:a", "2", "-c:a", encoder]
    elif media_type == "video":
        source = ["-f", "lavfi", "-i", "color=c=black:s=64x64:r=5", "-frames:v", "2", "-c:v", encoder]
    else:
        return False, f"Unbekannter Medientyp: {media_type}"
    try:
        result = subprocess.run(
            [binary, "-nostdin", "-hide_banner", "-loglevel", "error", *source, "-f", "null", "-"],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
            errors="replace",
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    output = "\n".join(part for part in (result.stdout, result.stderr) if part).strip()
    return result.returncode == 0, output[-2000:]

def required_filter_names(effect_key: str, transition_key: str, duration: float | None = 10.0) -> set[str]:
    expressions: list[str] = []
    effect = effect_filter(effect_key)
    if effect:
        expressions.append(effect)
    expressions.extend(transition_filters(transition_key, duration))
    names: set[str] = set()
    for expression in expressions:
        for component in expression.split(","):
            name = component.split("=", 1)[0].strip()
            if name:
                names.add(name)
    return names
