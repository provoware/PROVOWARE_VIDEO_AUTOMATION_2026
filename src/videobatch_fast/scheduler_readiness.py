from __future__ import annotations

import shutil
import subprocess
import time
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class SchedulerReadiness:
    ready: bool
    summary: str
    checks: tuple[tuple[str, bool, str], ...]


def _user_manager_reachable(run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run) -> bool:
    if shutil.which("systemctl") is None:
        return False
    try:
        result = run(
            ["systemctl", "--user", "show-environment"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


_MANAGER_CACHE_VALUE = False
_MANAGER_CACHE_UNTIL = 0.0

def _cached_user_manager_reachable() -> bool:
    global _MANAGER_CACHE_VALUE, _MANAGER_CACHE_UNTIL
    now = time.monotonic()
    if now >= _MANAGER_CACHE_UNTIL:
        _MANAGER_CACHE_VALUE = _user_manager_reachable()
        _MANAGER_CACHE_UNTIL = now + 30.0
    return _MANAGER_CACHE_VALUE

def inspect_scheduler_readiness(
    *,
    user_manager_probe: Callable[[], bool] | None = None,
) -> SchedulerReadiness:
    """Report the concrete prerequisites for the productive X11 scheduler."""
    manager_ok = (user_manager_probe or _cached_user_manager_reachable)()
    checks = (
        ("FFmpeg", shutil.which("ffmpeg") is not None, "Renderlaufzeit erreichbar"),
        ("FFprobe", shutil.which("ffprobe") is not None, "Medienprüfung erreichbar"),
        ("systemd-inhibit", shutil.which("systemd-inhibit") is not None, "Schlafmodus kann während eines Laufs kontrolliert gehemmt werden"),
        ("systemctl", shutil.which("systemctl") is not None, "Benutzertimer können verwaltet werden"),
        ("systemd --user", manager_ok, "Persönlicher systemd-Manager ist erreichbar"),
    )
    available = sum(1 for _name, ok, _detail in checks if ok)
    ready = available == len(checks)
    summary = (
        "Scheduler bereit · systemd-Benutzertimer verfügbar"
        if ready
        else f"Scheduler nicht bereit · Voraussetzungen {available}/{len(checks)} erkannt"
    )
    return SchedulerReadiness(ready=ready, summary=summary, checks=checks)
