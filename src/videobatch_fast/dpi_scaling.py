from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Protocol


class TkScalingRoot(Protocol):
    tk: object


@dataclass(frozen=True)
class TkScalingDecision:
    previous: float
    effective: float
    changed: bool
    source: str


def _finite_positive(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or number <= 0:
        return None
    return number


def requested_tk_scaling(environment: dict[str, str] | None = None) -> float | None:
    """Return an explicit Tk scaling override or None for system-managed scaling."""

    env = os.environ if environment is None else environment
    raw = str(env.get("VIDEOBATCH_TK_SCALING", "")).strip().lower()
    if raw in {"", "auto", "system", "desktop"}:
        return None
    value = _finite_positive(raw)
    if value is None:
        return None
    return max(0.75, min(4.0, value))


def apply_tk_scaling(root: TkScalingRoot) -> TkScalingDecision:
    """Respect the platform Tk scaling unless an explicit override is configured."""

    try:
        current = _finite_positive(root.tk.call("tk", "scaling")) or 1.0  # type: ignore[attr-defined]
    except Exception:
        current = 1.0

    requested = requested_tk_scaling()
    if requested is None:
        return TkScalingDecision(
            previous=current,
            effective=current,
            changed=False,
            source="system",
        )

    try:
        root.tk.call("tk", "scaling", requested)  # type: ignore[attr-defined]
        effective = _finite_positive(root.tk.call("tk", "scaling")) or requested  # type: ignore[attr-defined]
    except Exception:
        return TkScalingDecision(
            previous=current,
            effective=current,
            changed=False,
            source="override-failed",
        )
    return TkScalingDecision(
        previous=current,
        effective=effective,
        changed=abs(effective - current) > 1e-6,
        source="override",
    )
