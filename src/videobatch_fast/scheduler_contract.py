from __future__ import annotations

from typing import Any

DEFAULT_PRIORITY = 50
MIN_PRIORITY = 0
MAX_PRIORITY = 100


def normalize_governance(raw: Any) -> dict[str, Any]:
    source = dict(raw or {}) if isinstance(raw, dict) else {}
    priority = int(source.get("priority", DEFAULT_PRIORITY))
    if priority < MIN_PRIORITY or priority > MAX_PRIORITY:
        raise ValueError("Scheduler-Priorität muss zwischen 0 und 100 liegen.")
    return {"priority": priority}
