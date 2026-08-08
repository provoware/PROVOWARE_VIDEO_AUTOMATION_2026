from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .ffmpeg_capabilities import read_ffmpeg_capabilities
from .paths import cache_dir


@dataclass(frozen=True, slots=True)
class SystemMetrics:
    cpu_percent: float | None
    ram_used_bytes: int | None
    ram_total_bytes: int | None
    ffmpeg: str
    gpu_acceleration: str
    cache_bytes: int


def _read_cpu_times() -> tuple[int, int] | None:
    try:
        first = Path('/proc/stat').read_text(encoding='utf-8').splitlines()[0].split()[1:]
        values = [int(value) for value in first]
    except (OSError, ValueError, IndexError):
        return None
    total = sum(values)
    idle = (values[3] if len(values) > 3 else 0) + (values[4] if len(values) > 4 else 0)
    return total, idle


_PREVIOUS_CPU = _read_cpu_times()


def cpu_percent() -> float | None:
    global _PREVIOUS_CPU
    current = _read_cpu_times()
    previous = _PREVIOUS_CPU
    _PREVIOUS_CPU = current
    if current is None or previous is None:
        return None
    total_delta = current[0] - previous[0]
    idle_delta = current[1] - previous[1]
    if total_delta <= 0:
        return None
    value = 100.0 * (1.0 - idle_delta / total_delta)
    return round(max(0.0, min(100.0, value)), 1)


def ram_usage() -> tuple[int | None, int | None]:
    try:
        values: dict[str, int] = {}
        for line in Path('/proc/meminfo').read_text(encoding='utf-8').splitlines():
            key, raw = line.split(':', 1)
            values[key] = int(raw.strip().split()[0]) * 1024
        total = values.get('MemTotal')
        available = values.get('MemAvailable')
        if total is None or available is None:
            return None, total
        return max(0, total - available), total
    except (OSError, ValueError):
        return None, None


def directory_size(path: Path, *, limit_files: int = 10000) -> int:
    total = 0
    visited = 0
    try:
        for entry in path.rglob('*'):
            if visited >= limit_files:
                break
            visited += 1
            try:
                if entry.is_file() and not entry.is_symlink():
                    total += entry.stat().st_size
            except OSError:
                continue
    except OSError:
        return 0
    return total


def format_bytes(value: int | None) -> str:
    if value is None:
        return 'unbekannt'
    size = float(value)
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if size < 1024 or unit == 'TB':
            return f'{size:.0f} {unit}' if unit in {'B', 'KB'} else f'{size:.1f} {unit}'
        size /= 1024
    return f'{size:.1f} TB'


def collect_system_metrics() -> SystemMetrics:
    used, total = ram_usage()
    capabilities = read_ffmpeg_capabilities()
    ffmpeg = 'fehlt' if not capabilities.binary else Path(capabilities.binary).name
    if capabilities.error:
        gpu = 'unbekannt'
    else:
        encoders = capabilities.encoders
        gpu = 'aktivierbar' if any(
            token in encoder
            for encoder in encoders
            for token in ('nvenc', 'vaapi', 'qsv', 'videotoolbox', 'amf')
        ) else 'nicht erkannt'
    return SystemMetrics(
        cpu_percent=cpu_percent(),
        ram_used_bytes=used,
        ram_total_bytes=total,
        ffmpeg=ffmpeg,
        gpu_acceleration=gpu,
        cache_bytes=directory_size(cache_dir()),
    )
