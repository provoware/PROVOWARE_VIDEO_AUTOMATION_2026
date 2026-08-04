from __future__ import annotations

from array import array
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import math
from pathlib import Path
import statistics
import subprocess
import sys
from typing import Iterable

_ALLOWED_MARKER_KINDS = {"intro", "beat", "quiet", "drop", "outro"}
_MAX_CACHE_BYTES = 2 * 1024 * 1024

from .paths import cache_dir
from .probe import ffmpeg_path, probe_media
from .safe_io import atomic_write_json, read_json


@dataclass(frozen=True, slots=True)
class SceneMarker:
    label: str
    time_seconds: float
    kind: str
    confidence: float = 1.0


@dataclass(frozen=True, slots=True)
class WaveformAnalysis:
    path: Path
    duration: float
    peaks: tuple[float, ...]
    markers: tuple[SceneMarker, ...]
    sample_rate: int

    def marker_tuples(self) -> tuple[tuple[str, float, str, float], ...]:
        return tuple((item.label, item.time_seconds, item.kind, item.confidence) for item in self.markers)


def _quantile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round((len(ordered) - 1) * fraction)))
    return ordered[index]


def _smooth(values: list[float], radius: int = 3) -> list[float]:
    if not values:
        return []
    prefix = [0.0]
    for value in values:
        prefix.append(prefix[-1] + value)
    result: list[float] = []
    for index in range(len(values)):
        left = max(0, index - radius)
        right = min(len(values), index + radius + 1)
        result.append((prefix[right] - prefix[left]) / max(1, right - left))
    return result


def _marker_time(index: int, count: int, duration: float) -> float:
    if count <= 1:
        return 0.0
    return max(0.0, min(duration, index * duration / (count - 1)))


def _detect_markers(peaks: tuple[float, ...], duration: float) -> tuple[SceneMarker, ...]:
    if duration <= 0:
        return ()
    if len(peaks) < 8:
        return (
            SceneMarker("Intro", 0.0, "intro", 1.0),
            SceneMarker("Drop", round(duration * 0.5, 3), "drop", 0.4),
            SceneMarker("Outro", round(max(0.0, duration * 0.9), 3), "outro", 0.7),
        )

    values = _smooth(list(peaks), max(2, len(peaks) // 240))
    median = statistics.median(values)
    p75 = _quantile(values, 0.75)
    deltas = [0.0] + [values[index] - values[index - 1] for index in range(1, len(values))]
    positive = [value for value in deltas if value > 0]
    delta75 = _quantile(positive, 0.75) if positive else 0.0
    count = len(values)

    start_index = max(1, round(count * 0.03))
    onset_end = max(start_index + 1, round(count * 0.48))
    onset_candidates = [
        index
        for index in range(start_index, onset_end)
        if values[index] >= max(median * 1.12, p75 * 0.78) and deltas[index] >= max(delta75, 0.005)
    ]
    if onset_candidates:
        onset_index = onset_candidates[0]
    else:
        onset_index = max(range(start_index, onset_end), key=lambda index: deltas[index])

    quiet_left = max(onset_index + 2, round(count * 0.20))
    quiet_right = max(quiet_left + 1, round(count * 0.78))
    window = max(3, count // 80)
    quiet_index = min(
        range(quiet_left, quiet_right),
        key=lambda index: sum(values[max(0, index - window):min(count, index + window + 1)]),
    )

    drop_left = max(onset_index + 2, round(count * 0.18))
    drop_right = max(drop_left + 1, round(count * 0.88))
    scale = max(0.01, p75, median)
    drop_index = max(
        range(drop_left, drop_right),
        key=lambda index: (max(0.0, deltas[index]) / scale) * 0.7 + (values[index] / scale) * 0.3,
    )

    outro_start = round(count * 0.80)
    outro_threshold = max(0.015, median * 0.72)
    outro_index = next(
        (index for index in range(outro_start, count) if values[index] <= outro_threshold),
        round(count * 0.90),
    )

    raw = [
        SceneMarker("Intro", 0.0, "intro", 1.0),
        SceneMarker("Beat-Einsatz", _marker_time(onset_index, count, duration), "beat", 0.75),
        SceneMarker("Ruhige Phase", _marker_time(quiet_index, count, duration), "quiet", 0.65),
        SceneMarker("Drop", _marker_time(drop_index, count, duration), "drop", 0.9),
        SceneMarker("Outro", _marker_time(outro_index, count, duration), "outro", 0.8),
    ]

    priority = {"intro": 5, "drop": 4, "beat": 3, "quiet": 2, "outro": 1}
    minimum_gap = max(0.75, duration * 0.015)
    accepted: list[SceneMarker] = []
    for marker in sorted(raw, key=lambda item: (item.time_seconds, -priority.get(item.kind, 0))):
        collision = next((item for item in accepted if abs(item.time_seconds - marker.time_seconds) < minimum_gap), None)
        if collision is None:
            accepted.append(marker)
            continue
        if priority.get(marker.kind, 0) > priority.get(collision.kind, 0):
            accepted.remove(collision)
            accepted.append(marker)
    return tuple(sorted(accepted, key=lambda item: item.time_seconds))


def _adaptive_sample_rate(duration: float) -> int:
    # Bound decoded PCM to roughly 16 MiB even for unusually long recordings.
    if duration <= 0:
        return 1000
    bounded = int((16 * 1024 * 1024) / max(1.0, duration * 2.0))
    return max(100, min(2000, bounded))


def _decode_peaks(path: Path, duration: float, points: int) -> tuple[tuple[float, ...], int]:
    binary = ffmpeg_path() or "ffmpeg"
    sample_rate = _adaptive_sample_rate(duration)
    command = [
        binary,
        "-v", "error",
        "-i", str(path),
        "-map", "0:a:0",
        "-vn", "-sn", "-dn",
        "-ac", "1",
        "-ar", str(sample_rate),
        "-f", "s16le",
        "pipe:1",
    ]
    timeout = min(240.0, max(30.0, duration * 0.08 + 20.0))
    completed = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    samples = array("h")
    samples.frombytes(completed.stdout)
    if sys.byteorder != "little":
        samples.byteswap()
    if not samples:
        raise RuntimeError("Die Audiospur enthält keine dekodierbaren Samples.")

    target_points = max(160, min(1800, int(points)))
    chunk = max(1, math.ceil(len(samples) / target_points))
    peaks: list[float] = []
    for start in range(0, len(samples), chunk):
        block = samples[start:start + chunk]
        if not block:
            continue
        rms = math.sqrt(sum(float(value) * float(value) for value in block) / len(block)) / 32768.0
        peaks.append(min(1.0, max(0.0, rms)))
    maximum = max(peaks, default=0.0)
    if maximum > 0:
        peaks = [min(1.0, value / maximum) for value in peaks]
    return tuple(peaks), sample_rate




def _cache_path(path: Path, size: int, modified_ns: int, points: int) -> Path:
    identity = f"{path.resolve()}\0{size}\0{modified_ns}\0{points}\0waveform-v1".encode("utf-8")
    digest = hashlib.sha256(identity).hexdigest()
    return cache_dir() / "waveforms" / f"{digest}.json"


def _load_persistent_cache(path: Path, source: Path, size: int, modified_ns: int) -> WaveformAnalysis | None:
    try:
        if path.stat().st_size > _MAX_CACHE_BYTES:
            return None
        payload = read_json(path)
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("source") != str(source) or payload.get("size") != size or payload.get("modified_ns") != modified_ns:
        return None
    try:
        markers = tuple(
            SceneMarker(str(item["label"]), float(item["time"]), str(item["kind"]), float(item.get("confidence", 1.0)))
            for item in payload.get("markers", [])
            if isinstance(item, dict)
        )
        peaks = tuple(float(value) for value in payload.get("peaks", []))
        duration = float(payload["duration"])
        sample_rate = int(payload["sample_rate"])
    except (KeyError, TypeError, ValueError):
        return None
    if duration <= 0 or not math.isfinite(duration) or sample_rate <= 0 or not peaks or len(peaks) > 1800:
        return None
    if any(not math.isfinite(value) or value < 0.0 or value > 1.0 for value in peaks):
        return None
    if any(
        item.kind not in _ALLOWED_MARKER_KINDS
        or not math.isfinite(item.time_seconds)
        or item.time_seconds < 0.0
        or item.time_seconds > duration
        or not math.isfinite(item.confidence)
        or item.confidence < 0.0
        or item.confidence > 1.0
        for item in markers
    ):
        return None
    return WaveformAnalysis(source, duration, peaks, markers, sample_rate)


def _save_persistent_cache(path: Path, analysis: WaveformAnalysis, size: int, modified_ns: int) -> None:
    payload = {
        "schema_version": 1,
        "source": str(analysis.path),
        "size": size,
        "modified_ns": modified_ns,
        "duration": analysis.duration,
        "sample_rate": analysis.sample_rate,
        "peaks": list(analysis.peaks),
        "markers": [
            {"label": item.label, "time": item.time_seconds, "kind": item.kind, "confidence": item.confidence}
            for item in analysis.markers
        ],
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(path, payload)
    except OSError:
        pass


@lru_cache(maxsize=64)
def _analyze_cached(path_text: str, size: int, modified_ns: int, points: int) -> WaveformAnalysis:
    path = Path(path_text)
    info = probe_media(path)
    duration = float(info.duration or 0.0)
    if duration <= 0:
        raise RuntimeError("Die Audiodauer konnte nicht bestimmt werden.")
    peaks, sample_rate = _decode_peaks(path, duration, points)
    return WaveformAnalysis(path, duration, peaks, _detect_markers(peaks, duration), sample_rate)


def analyze_audio(path: Path, *, points: int = 900, refresh: bool = False) -> WaveformAnalysis:
    target = Path(path).expanduser().resolve()
    stat = target.stat()
    selected_points = max(160, min(1800, int(points)))
    persistent = _cache_path(target, stat.st_size, stat.st_mtime_ns, selected_points)
    if not refresh:
        cached = _load_persistent_cache(persistent, target, stat.st_size, stat.st_mtime_ns)
        if cached is not None:
            return cached
    if refresh:
        _analyze_cached.cache_clear()
    analysis = _analyze_cached(str(target), stat.st_size, stat.st_mtime_ns, selected_points)
    _save_persistent_cache(persistent, analysis, stat.st_size, stat.st_mtime_ns)
    return analysis


def markers_from_tuples(values: Iterable[tuple[str, float, str, float]]) -> tuple[SceneMarker, ...]:
    result: list[SceneMarker] = []
    for label, time_seconds, kind, confidence in values:
        selected_kind = str(kind)
        selected_time = float(time_seconds)
        selected_confidence = float(confidence)
        if (
            selected_kind not in _ALLOWED_MARKER_KINDS
            or not math.isfinite(selected_time)
            or selected_time < 0.0
            or not math.isfinite(selected_confidence)
        ):
            continue
        result.append(
            SceneMarker(
                str(label)[:80],
                selected_time,
                selected_kind,
                min(1.0, max(0.0, selected_confidence)),
            )
        )
    return tuple(result)


def scene_change_points(
    duration: float,
    image_count: int,
    markers: Iterable[SceneMarker],
) -> tuple[float, ...]:
    if duration <= 0 or image_count <= 0:
        return ()
    if image_count == 1:
        return (0.0, float(duration))

    internal_needed = image_count - 1
    priority = {"drop": 5, "beat": 4, "quiet": 3, "outro": 2, "intro": 1}
    candidates = [
        item for item in markers
        if 0.15 < item.time_seconds < duration - 0.15 and item.kind not in {"intro"}
    ]
    chosen = sorted(
        sorted(candidates, key=lambda item: (priority.get(item.kind, 0), item.confidence), reverse=True)[:internal_needed],
        key=lambda item: item.time_seconds,
    )
    boundaries = [0.0, *(item.time_seconds for item in chosen), float(duration)]

    desired_minimum = max(0.01, duration / max(100.0, image_count * 15.0))
    minimum = min(desired_minimum, duration / max(2.0, image_count * 2.0))
    while len(boundaries) < image_count + 1:
        intervals = [boundaries[index + 1] - boundaries[index] for index in range(len(boundaries) - 1)]
        index = max(range(len(intervals)), key=intervals.__getitem__)
        midpoint = boundaries[index] + intervals[index] / 2.0
        boundaries.insert(index + 1, midpoint)

    while len(boundaries) > image_count + 1:
        removable = range(1, len(boundaries) - 1)
        index = min(removable, key=lambda item: min(boundaries[item] - boundaries[item - 1], boundaries[item + 1] - boundaries[item]))
        boundaries.pop(index)

    adjusted = [0.0]
    for value in boundaries[1:-1]:
        low = adjusted[-1] + minimum
        high = duration - minimum * (image_count - len(adjusted))
        adjusted.append(min(max(float(value), low), max(low, high)))
    adjusted.append(float(duration))
    return tuple(round(value, 6) for value in adjusted)
