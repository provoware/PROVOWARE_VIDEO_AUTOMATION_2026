"""Portable PROVOWARE grid rules: no Qt or VideoBatch dependency."""
from __future__ import annotations

import math

import pytest

from provoware_grid import (
    DEFAULT_ZOOM, GRID_COLUMNS, GRID_ROWS, REFERENCE_HEIGHT,
    REFERENCE_WIDTH, ZOOM_LEVELS, choose_columns, evaluate_matrix,
    grid_area, nearest_zoom,
)


def test_grid_is_relative_and_precise() -> None:
    assert (REFERENCE_WIDTH, REFERENCE_HEIGHT, GRID_COLUMNS, GRID_ROWS) == (800, 600, 120, 80)
    first = grid_area(1, 1, 60, 40)
    assert (first.x, first.y, first.width, first.height) == (0, 0, 0.5, 0.5)
    second = grid_area(61, 41, 60, 40)
    assert (second.x, second.y, second.width, second.height) == (0.5, 0.5, 0.5, 0.5)


@pytest.mark.parametrize("args", [
    (0, 1, 1, 1), (1, 0, 1, 1), (1, 1, 121, 1), (121, 1, 1, 1),
    (1, 81, 1, 1), (1, 1, 0, 1), (True, 1, 1, 1),
])
def test_invalid_grid_coordinates_are_rejected(args) -> None:
    with pytest.raises(ValueError):
        grid_area(*args)


def test_window_size_and_typography_determine_column_count() -> None:
    assert DEFAULT_ZOOM == 110
    assert nearest_zoom(112) == 110
    assert choose_columns(780, zoom_percent=110, panel_min_width=360) == 1
    assert choose_columns(780, zoom_percent=110, panel_min_width=320) == 2
    assert choose_columns(1300, zoom_percent=110) == 2
    assert choose_columns(560, zoom_percent=110) == 1
    assert choose_columns(1300, zoom_percent=200) == 1
    assert choose_columns(1460, zoom_percent=200) == 2
    assert choose_columns(1300, zoom_percent=100, intrinsic_min_widths=(680,)) == 1
    assert choose_columns(1300, zoom_percent=100, max_columns=1) == 1


@pytest.mark.parametrize("width,extra", [
    (0, {}), (-50, {}), (math.inf, {}), (1000, {"panel_min_width": 0}),
    (1000, {"gap": -1}), (1000, {"zoom_percent": float("nan")}),
    (1000, {"intrinsic_min_widths": [float("nan")]}),
    (1000, {"max_columns": 3}),
])
def test_invalid_dimensions_cannot_fake_success(width, extra) -> None:
    with pytest.raises(ValueError):
        choose_columns(width, **extra)


def test_complete_offline_reference_matrix() -> None:
    sizes = [(800, 600), (1024, 768), (1280, 720),
             (1366, 768), (1920, 1080), (2560, 1440)]
    matrix = evaluate_matrix(sizes)
    assert len(matrix) == len(sizes) * len(ZOOM_LEVELS) == 42
    assert all(row["minimum_width_preserved"] for row in matrix)
    assert all(row["columns"] in (1, 2) for row in matrix)
    assert next(row for row in matrix if row["width"] == 800 and row["zoom"] == 200)["stacked"]
    assert not next(row for row in matrix if row["width"] == 1920 and row["zoom"] == 110)["stacked"]


def test_python_grid_has_no_application_or_ui_dependencies() -> None:
    from pathlib import Path
    import provoware_grid
    path = Path(provoware_grid.__file__).parent
    source = "\n".join(p.read_text(encoding="utf-8") for p in path.glob("*.py"))
    assert "import PySide6" not in source
    assert "import videobatch_fast" not in source
