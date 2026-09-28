from __future__ import annotations

from pathlib import Path

from videobatch_fast.system_load import (
    CpuTimes,
    SystemLoadSampler,
    cpu_usage_percent,
    memory_load,
    read_cpu_times,
    read_meminfo,
)


def test_cpu_usage_uses_delta_between_samples() -> None:
    previous = CpuTimes(idle=700, total=1000)
    current = CpuTimes(idle=760, total=1200)
    assert cpu_usage_percent(previous, current) == 70.0
    assert cpu_usage_percent(None, current) is None


def test_proc_cpu_parser_includes_iowait_in_idle(tmp_path: Path) -> None:
    stat = tmp_path / "stat"
    stat.write_text("cpu  100 20 30 700 50 10 5 0 0 0\n", encoding="utf-8")
    assert read_cpu_times(stat) == CpuTimes(idle=750, total=915)


def test_memory_load_uses_available_memory_and_swap(tmp_path: Path) -> None:
    meminfo = tmp_path / "meminfo"
    meminfo.write_text(
        "MemTotal:       8000000 kB\n"
        "MemAvailable:   2000000 kB\n"
        "SwapTotal:      4000000 kB\n"
        "SwapFree:       3000000 kB\n",
        encoding="utf-8",
    )
    values = read_meminfo(meminfo)
    ram_percent, ram_used, ram_total, swap_percent, swap_used, swap_total = memory_load(values)
    assert ram_percent == 75.0
    assert ram_used == 6_000_000 * 1024
    assert ram_total == 8_000_000 * 1024
    assert swap_percent == 25.0
    assert swap_used == 1_000_000 * 1024
    assert swap_total == 4_000_000 * 1024


def test_sampler_is_read_only_and_handles_swap_disabled(tmp_path: Path) -> None:
    stat = tmp_path / "stat"
    meminfo = tmp_path / "meminfo"
    stat.write_text("cpu  10 0 10 80 0 0 0 0\n", encoding="utf-8")
    meminfo.write_text(
        "MemTotal: 1000 kB\nMemAvailable: 250 kB\nSwapTotal: 0 kB\nSwapFree: 0 kB\n",
        encoding="utf-8",
    )
    sampler = SystemLoadSampler(stat_path=stat, meminfo_path=meminfo)
    first = sampler.sample()
    stat.write_text("cpu  30 0 20 100 0 0 0 0\n", encoding="utf-8")
    second = sampler.sample()

    assert first.cpu_percent is None
    assert first.ram_percent == 75.0
    assert first.swap_percent == 0.0
    assert second.cpu_percent == 60.0
    assert second.swap_total_bytes == 0
