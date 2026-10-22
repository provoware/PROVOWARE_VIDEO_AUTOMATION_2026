"""Pure Python PROVOWARE responsive 120×80 grid rules.

No Qt, browser, application or third-party dependency. Safe to copy to other
single-user offline Python projects.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable

REFERENCE_WIDTH = 800
REFERENCE_HEIGHT = 600
GRID_COLUMNS = 120
GRID_ROWS = 80
ZOOM_LEVELS = (80, 100, 110, 125, 150, 175, 200)
DEFAULT_ZOOM = 110
DEFAULT_GAP = 12
DEFAULT_PANEL_MIN_WIDTH = 360


@dataclass(frozen=True)
class GridArea:
    """Fractional position of a rectangle; dimensions are derived at runtime."""

    x: float
    y: float
    width: float
    height: float


def grid_area(
    column: int,
    row: int,
    column_span: int,
    row_span: int,
    *,
    columns: int = GRID_COLUMNS,
    rows: int = GRID_ROWS,
) -> GridArea:
    """Map one-based grid coordinates into normalized, resolution-free ratios."""
    if not all(isinstance(v, int) and not isinstance(v, bool)
               for v in (column, row, column_span, row_span, columns, rows)):
        raise ValueError("Rasterkoordinaten müssen ganze Zahlen sein")
    if columns < 1 or rows < 1 or column < 1 or row < 1:
        raise ValueError("Rastergröße und Startposition müssen positiv sein")
    if column_span < 1 or row_span < 1:
        raise ValueError("Rasterflächen müssen mindestens eine Zelle groß sein")
    if column + column_span - 1 > columns or row + row_span - 1 > rows:
        raise ValueError("Rasterfläche liegt außerhalb des Bezugsrasters")
    return GridArea(
        x=(column - 1) / columns,
        y=(row - 1) / rows,
        width=column_span / columns,
        height=row_span / rows,
    )


def nearest_zoom(percent: int | float) -> int:
    """Snap arbitrary interface zoom to one of the standard accessible values."""
    if isinstance(percent, bool) or not isinstance(percent, (int, float)):
        raise ValueError("Schriftgröße muss eine Zahl sein")
    if not isfinite(percent) or percent <= 0:
        raise ValueError("Schriftgröße muss positiv und endlich sein")
    return min(ZOOM_LEVELS, key=lambda value: abs(value - percent))


def choose_columns(
    available_width: int | float,
    *,
    zoom_percent: int | float = DEFAULT_ZOOM,
    panel_min_width: int | float = DEFAULT_PANEL_MIN_WIDTH,
    gap: int | float = DEFAULT_GAP,
    intrinsic_min_widths: Iterable[int | float] = (),
    max_columns: int = 2,
) -> int:
    """Choose 1 or 2 readable equally weighted columns.

    Width is the *actual inner container width*. Content minimums are measured
    in already-scaled pixels; the nominal minimum is scaled with UI zoom.
    """
    inputs = (available_width, panel_min_width, gap)
    if any(isinstance(v, bool) or not isinstance(v, (int, float))
           or not isfinite(v) for v in inputs):
        raise ValueError("Breite, Mindestgröße und Abstand müssen endlich sein")
    if available_width <= 0 or panel_min_width <= 0 or gap < 0:
        raise ValueError("Breite und Mindestgröße müssen positiv sein")
    if max_columns not in (1, 2):
        raise ValueError("Für zwei gleich große Bereiche sind nur 1–2 Spalten erlaubt")
    zoom = nearest_zoom(zoom_percent)
    required = panel_min_width * zoom / 100
    for minimum in intrinsic_min_widths:
        if isinstance(minimum, bool) or not isinstance(minimum, (int, float)):
            raise ValueError("Gemessene Mindestbreiten müssen Zahlen sein")
        if not isfinite(minimum) or minimum < 0:
            raise ValueError("Gemessene Mindestbreiten müssen endlich und positiv sein")
        required = max(required, minimum)
    return 2 if max_columns == 2 and available_width >= 2 * required + gap else 1


def evaluate_matrix(
    sizes: Iterable[tuple[int, int]],
    zoom_levels: Iterable[int] = ZOOM_LEVELS,
    *,
    panel_min_width: int = DEFAULT_PANEL_MIN_WIDTH,
    gap: int = DEFAULT_GAP,
    outer_margin: int = 10,
) -> list[dict[str, int | bool]]:
    """Portable, deterministic rule checks (not browser screenshot evidence)."""
    results: list[dict[str, int | bool]] = []
    for width, height in sizes:
        if not isinstance(width, int) or not isinstance(height, int) or width < 1 or height < 1:
            raise ValueError("Fenstergrößen müssen positive ganze Zahlen sein")
        if width <= 2 * outer_margin:
            raise ValueError("Fensterbreite reicht für die Seitenränder nicht aus")
        for zoom in zoom_levels:
            usable = width - 2 * outer_margin
            n = choose_columns(usable, zoom_percent=zoom,
                               panel_min_width=panel_min_width, gap=gap)
            required = panel_min_width * nearest_zoom(zoom) / 100
            readable = n == 1 or (usable - gap) / 2 >= required
            results.append({
                "width": width, "height": height, "zoom": nearest_zoom(zoom),
                "columns": n, "stacked": n == 1, "minimum_width_preserved": readable,
            })
    return results
