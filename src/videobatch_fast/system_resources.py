from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SystemLoadSnapshot:
    cpu_percent: float
    ram_used: int
    ram_total: int
    swap_used: int
    swap_total: int
    zram_used: int
    zram_total: int
    disk_free: int
    disk_total: int


def format_bytes(value: int) -> str:
    amount = max(0, int(value))
    for suffix in ("B", "KB", "MB", "GB", "TB"):
        if amount < 1024 or suffix == "TB":
            return f"{amount:.0f} {suffix}" if suffix in {"B", "KB"} else f"{amount:.1f} {suffix}"
        amount /= 1024
    return f"{amount:.1f} TB"


def _meminfo() -> dict[str, int]:
    values: dict[str, int] = {}
    try:
        lines = Path("/proc/meminfo").read_text(encoding="utf-8").splitlines()
    except OSError:
        return values
    for line in lines:
        if ":" not in line:
            continue
        key, raw = line.split(":", 1)
        token = raw.strip().split()[0] if raw.strip() else "0"
        try:
            values[key] = int(token) * 1024
        except ValueError:
            continue
    return values


def _zram_usage() -> tuple[int, int]:
    used = 0
    total = 0
    try:
        lines = Path("/proc/swaps").read_text(encoding="utf-8").splitlines()[1:]
    except OSError:
        return used, total
    for line in lines:
        fields = line.split()
        if len(fields) < 5 or "/zram" not in fields[0]:
            continue
        try:
            total += int(fields[2]) * 1024
            used += int(fields[3]) * 1024
        except ValueError:
            continue
    return used, total


def _cpu_ticks() -> tuple[int, int]:
    try:
        fields = Path("/proc/stat").read_text(encoding="utf-8").splitlines()[0].split()[1:]
        ticks = [int(value) for value in fields]
    except (OSError, ValueError, IndexError):
        return 0, 0
    idle = sum(ticks[index] for index in (3, 4) if index < len(ticks))
    return sum(ticks), idle


class SystemResourceMonitor:
    """Small Linux-first load monitor without external packages."""

    def __init__(self) -> None:
        self._last_total = 0
        self._last_idle = 0

    def _cpu_percent(self) -> float:
        total, idle = _cpu_ticks()
        delta_total = max(0, total - self._last_total)
        delta_idle = max(0, idle - self._last_idle)
        self._last_total, self._last_idle = total, idle
        if not delta_total:
            return 0.0
        return min(100.0, max(0.0, (delta_total - delta_idle) / delta_total * 100.0))

    def sample(self, disk_path: Path) -> SystemLoadSnapshot:
        memory = _meminfo()
        ram_total = memory.get("MemTotal", 0)
        ram_available = memory.get("MemAvailable", memory.get("MemFree", 0))
        swap_total = memory.get("SwapTotal", 0)
        swap_free = memory.get("SwapFree", 0)
        zram_used, zram_total = _zram_usage()
        target = disk_path if disk_path.exists() else Path.home()
        try:
            disk = shutil.disk_usage(target)
        except OSError:
            disk = shutil.disk_usage(Path.home())
        return SystemLoadSnapshot(
            cpu_percent=self._cpu_percent(),
            ram_used=max(0, ram_total - ram_available),
            ram_total=ram_total,
            swap_used=max(0, swap_total - swap_free),
            swap_total=swap_total,
            zram_used=zram_used,
            zram_total=zram_total,
            disk_free=disk.free,
            disk_total=disk.total,
        )
