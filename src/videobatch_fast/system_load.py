from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

_PROC_STAT = Path("/proc/stat")
_PROC_MEMINFO = Path("/proc/meminfo")
_KIB = 1024


@dataclass(frozen=True, slots=True)
class CpuTimes:
    idle: int
    total: int


@dataclass(frozen=True, slots=True)
class SystemLoad:
    cpu_percent: float | None
    ram_percent: float | None
    swap_percent: float | None
    ram_used_bytes: int
    ram_total_bytes: int
    swap_used_bytes: int
    swap_total_bytes: int


def _bounded_percent(value: float) -> float:
    return max(0.0, min(100.0, value))


def read_cpu_times(path: Path = _PROC_STAT) -> CpuTimes | None:
    try:
        line = path.read_text(encoding="utf-8").splitlines()[0]
        fields = line.split()
        if not fields or fields[0] != "cpu":
            return None
        values = [int(value) for value in fields[1:]]
        if len(values) < 4:
            return None
    except (OSError, ValueError, IndexError):
        return None

    idle = values[3] + (values[4] if len(values) > 4 else 0)
    return CpuTimes(idle=idle, total=sum(values))


def cpu_usage_percent(previous: CpuTimes | None, current: CpuTimes | None) -> float | None:
    if previous is None or current is None:
        return None
    total_delta = current.total - previous.total
    idle_delta = current.idle - previous.idle
    if total_delta <= 0:
        return None
    busy = total_delta - max(0, idle_delta)
    return _bounded_percent((busy / total_delta) * 100.0)


def read_meminfo(path: Path = _PROC_MEMINFO) -> dict[str, int]:
    values: dict[str, int] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return values

    for line in lines:
        key, separator, remainder = line.partition(":")
        if not separator:
            continue
        parts = remainder.strip().split()
        if not parts:
            continue
        try:
            amount = int(parts[0])
        except ValueError:
            continue
        values[key] = amount * _KIB
    return values


def memory_load(meminfo: dict[str, int]) -> tuple[float | None, int, int, float | None, int, int]:
    ram_total = max(0, int(meminfo.get("MemTotal", 0)))
    available = int(meminfo.get("MemAvailable", -1))
    if available < 0:
        available = sum(
            max(0, int(meminfo.get(key, 0)))
            for key in ("MemFree", "Buffers", "Cached", "SReclaimable")
        )
    ram_used = max(0, ram_total - max(0, available))
    ram_percent = (
        _bounded_percent((ram_used / ram_total) * 100.0)
        if ram_total > 0
        else None
    )

    swap_total = max(0, int(meminfo.get("SwapTotal", 0)))
    swap_free = max(0, int(meminfo.get("SwapFree", 0)))
    swap_used = max(0, swap_total - swap_free)
    swap_percent = (
        _bounded_percent((swap_used / swap_total) * 100.0)
        if swap_total > 0
        else 0.0
    )
    return ram_percent, ram_used, ram_total, swap_percent, swap_used, swap_total


class SystemLoadSampler:
    """Read-only Linux load sampler backed by /proc; no optional dependency required."""

    def __init__(
        self,
        *,
        stat_path: Path = _PROC_STAT,
        meminfo_path: Path = _PROC_MEMINFO,
    ) -> None:
        self._stat_path = Path(stat_path)
        self._meminfo_path = Path(meminfo_path)
        self._previous_cpu: CpuTimes | None = None

    def sample(self) -> SystemLoad:
        current_cpu = read_cpu_times(self._stat_path)
        cpu_percent = cpu_usage_percent(self._previous_cpu, current_cpu)
        if current_cpu is not None:
            self._previous_cpu = current_cpu

        (
            ram_percent,
            ram_used,
            ram_total,
            swap_percent,
            swap_used,
            swap_total,
        ) = memory_load(read_meminfo(self._meminfo_path))
        return SystemLoad(
            cpu_percent=cpu_percent,
            ram_percent=ram_percent,
            swap_percent=swap_percent,
            ram_used_bytes=ram_used,
            ram_total_bytes=ram_total,
            swap_used_bytes=swap_used,
            swap_total_bytes=swap_total,
        )
