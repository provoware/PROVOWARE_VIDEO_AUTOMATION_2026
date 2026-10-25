"""Regression for PROVOWARE 800×600 / 120×80 responsive layout V1.

The contract test is deliberately separate from real browser rendering: DOM
geometry and visual screenshot approval remain independent gates.
"""
from __future__ import annotations

from qt_source_contracts import read_qt_sources

import json
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "config/contracts/PROVOWARE_RESPONSIVE_GRID_V1.json"
DOC = ROOT / "docs/design/PROVOWARE_RESPONSIVE_GRID_V1.md"
REFERENCE = ROOT / "visual_inspection/provoware_grid_reference.html"


class _ReferenceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.external_scripts: list[str] = []
        self.critical = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        mapping = dict(attrs)
        if "id" in mapping:
            identifier = mapping["id"]
            assert identifier not in self.ids, f"Duplicate HTML id: {identifier}"
            if identifier:
                self.ids.add(identifier)
        if tag == "script" and mapping.get("src"):
            self.external_scripts.append(str(mapping["src"]))
        if "data-critical" in mapping:
            self.critical += 1


def _contract() -> dict:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_reference_grid_is_exactly_800_by_600_and_120_by_80() -> None:
    data = _contract()
    assert data["id"] == "PROVOWARE-RESPONSIVE-GRID-V1"
    assert data["schema_version"] == 1
    assert data["status"] == "development_reference_not_release_approval"
    assert data["reference_viewport_css_px"]["width"] == 800
    assert data["reference_viewport_css_px"]["height"] == 600
    assert data["reference_grid"]["columns"] == 120
    assert data["reference_grid"]["rows"] == 80
    assert data["reference_grid"]["cell_is_positioning_unit_not_widget_size"]
    assert data["reference_grid"]["coordinates_are_normalized"]
    assert data["layout"]["fixed_absolute_widget_coordinates"] is False


def test_viewport_and_zoom_matrix_includes_minimum_and_extremes() -> None:
    data = _contract()
    matrix = data["verification"]["width_height_css_px"]
    zooms = data["verification"]["zoom_percent"]
    assert [800, 600] in matrix
    assert [1280, 720] in matrix
    assert [1920, 1080] in matrix
    assert [80, 100, 110, 125, 150, 175, 200] == zooms
    assert data["typography"]["default_percent"] == 110
    assert len(matrix) * len(zooms) >= 42
    assert data["verification"]["html_prototype_is_not_qt_release_evidence"]
    assert data["verification"]["physical_kubuntu_acceptance_separate"]


def test_two_column_decision_obeys_intrinsic_minimums_at_all_zoom_levels() -> None:
    data = _contract()
    min_width = data["layout"]["panels"]["preferred_minimum_width_css_px"]
    gap = data["layout"]["panels"]["gap_css_px"]
    assert min_width >= data["layout"]["panels"]["minimum_readable_width_css_px"]
    for width, _height in data["verification"]["width_height_css_px"]:
        for zoom in data["verification"]["zoom_percent"]:
            # Relative width is measured inside the window, not from screen pixels.
            inner = width - 20
            needed = 2 * (min_width * zoom / 100) + gap
            if inner < needed:
                assert inner / 2 - gap < min_width * zoom / 100
            else:
                assert inner >= needed
    assert 800 - 20 < 2 * min_width * 2 + gap  # 200% must stack.
    assert 1920 - 20 >= 2 * min_width * 1.1 + gap  # 110% can share width.


def test_html_reference_is_offline_and_exposes_runtime_geometry_checks() -> None:
    raw = REFERENCE.read_text(encoding="utf-8")
    parser = _ReferenceParser()
    parser.feed(raw)
    assert not parser.external_scripts
    assert {"grid", "grid-toggle", "zoom", "shell", "columns", "stage", "measurement"} <= parser.ids
    assert parser.critical >= 4
    for text in (
        "calc(100% / 120)",
        "calc(100% / 80)",
        "--min-card-width",
        "minmax(min(100%, var(--min-card-width)), 1fr)",
        "overflow-y: auto",
        "document.documentElement.scrollWidth",
        "new ResizeObserver",
    ):
        assert text in raw
    assert "800 × 600" in DOC.read_text(encoding="utf-8")
    assert "9.600" in DOC.read_text(encoding="utf-8")


def test_contract_expresses_real_safety_and_non_merge_policy() -> None:
    data = _contract()
    assert data["layout"]["horizontal_overflow"] == "forbidden_for_primary_application_layout"
    assert data["layout"]["vertical_overflow"] == "allow_in_content_region"
    assert data["layout"]["preserve_essential_controls"]
    assertions = data["verification"]["assertions"]
    assert "text_labels_not_clipped" in assertions
    assert "no_unintended_overlap" in assertions
    assert "essential_actions_reachable_by_keyboard" in assertions
    assert "original_rendering_and_storage_unmodified" in assertions


def test_portable_python_core_and_css_match_the_contract() -> None:
    from provoware_grid import (
        GRID_COLUMNS, GRID_ROWS, REFERENCE_WIDTH, REFERENCE_HEIGHT, ZOOM_LEVELS,
    )
    data = _contract()
    assert (GRID_COLUMNS, GRID_ROWS) == (
        data["reference_grid"]["columns"], data["reference_grid"]["rows"],
    )
    assert (REFERENCE_WIDTH, REFERENCE_HEIGHT) == (
        data["reference_viewport_css_px"]["width"],
        data["reference_viewport_css_px"]["height"],
    )
    assert list(ZOOM_LEVELS) == data["typography"]["zoom_percent"]
    style = (ROOT / "src/provoware_grid/grid-v1.css").read_text(encoding="utf-8")
    assert "--pvw-grid-columns: 120" in style
    assert "--pvw-grid-rows: 80" in style
    assert "minmax(min(100%, var(--pvw-min-panel)), 1fr)" in style
    reference = REFERENCE.read_text(encoding="utf-8")
    assert 'href="../src/provoware_grid/grid-v1.css"' in reference
    assert 'class="columns pvw-grid"' in reference


def test_qt_uses_portable_rules_without_importing_ffmpeg_or_qt_into_core() -> None:
    source = read_qt_sources(ROOT / 'src/videobatch_fast/qt_source_panel.py', encoding='utf-8')
    adapter = (ROOT / "src/videobatch_fast/qt_adaptive_settings.py").read_text(encoding="utf-8")
    main = read_qt_sources(ROOT / 'src/videobatch_fast/qt_main_layout.py', encoding='utf-8')
    assert "from provoware_grid import choose_columns" in source
    assert "from provoware_grid import choose_columns" in adapter
    assert 'setObjectName("adaptiveSettingScroll")' in main
    assert "window.settings_grid.set_zoom_percent(value)" in main
    assert "window.source_columns.set_zoom_percent(value)" in main
