from __future__ import annotations

import re
from dataclasses import dataclass

_GEOMETRY_RE = re.compile(
    r"^\s*(?P<width>\d+)x(?P<height>\d+)"
    r"(?:(?P<xsign>[+-])(?P<x>\d+)(?P<ysign>[+-])(?P<y>\d+))?\s*$"
)


@dataclass(frozen=True, slots=True)
class WindowGeometry:
    width: int
    height: int
    x: int
    y: int

    def as_tk(self) -> str:
        return f"{self.width}x{self.height}+{self.x}+{self.y}"


def _clamp(value: int, minimum: int, maximum: int) -> int:
    if maximum < minimum:
        return maximum
    return min(maximum, max(minimum, value))


def safe_minimum_window_size(
    screen_width: int,
    screen_height: int,
    *,
    preferred_width: int = 1024,
    preferred_height: int = 680,
    margin: int = 56,
) -> tuple[int, int]:
    usable_width = max(640, int(screen_width) - margin)
    usable_height = max(520, int(screen_height) - margin)
    return min(preferred_width, usable_width), min(preferred_height, usable_height)


def normalize_window_geometry(
    raw: str,
    screen_width: int,
    screen_height: int,
    *,
    default_width: int = 1500,
    default_height: int = 920,
    margin: int = 56,
) -> WindowGeometry:
    """Clamp saved geometry to the visible screen without losing valid choices."""
    screen_width = max(640, int(screen_width))
    screen_height = max(520, int(screen_height))
    minimum_width, minimum_height = safe_minimum_window_size(
        screen_width,
        screen_height,
        margin=margin,
    )
    maximum_width = max(minimum_width, screen_width - margin)
    maximum_height = max(minimum_height, screen_height - margin)

    match = _GEOMETRY_RE.fullmatch(str(raw or ""))
    if match:
        width = int(match.group("width"))
        height = int(match.group("height"))
        if match.group("x") is not None:
            x = int(match.group("x")) * (-1 if match.group("xsign") == "-" else 1)
            y = int(match.group("y")) * (-1 if match.group("ysign") == "-" else 1)
        else:
            x = (screen_width - width) // 2
            y = (screen_height - height) // 2
    else:
        width = default_width
        height = default_height
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2

    width = _clamp(width, minimum_width, maximum_width)
    height = _clamp(height, minimum_height, maximum_height)
    x = _clamp(x, 0, max(0, screen_width - width))
    y = _clamp(y, 0, max(0, screen_height - height))
    return WindowGeometry(width=width, height=height, x=x, y=y)
