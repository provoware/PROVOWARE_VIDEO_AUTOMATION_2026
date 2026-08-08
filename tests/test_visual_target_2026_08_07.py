from __future__ import annotations

import inspect
from pathlib import Path

from PIL import Image

from videobatch_fast.canonical_dashboard_mixin import CanonicalDashboardMixin
from videobatch_fast.canonical_shell_chrome import CanonicalShellChromeMixin
from videobatch_fast.canonical_shell_workspace import CanonicalShellWorkspaceMixin
from videobatch_fast.visual_regression import compare_visual


def test_canonical_shell_does_not_build_native_menu_bar() -> None:
    source = inspect.getsource(CanonicalShellWorkspaceMixin._build_ui)
    assert "_build_menu_bar" not in source


def test_dashboard_primary_zones_are_first_class_builders() -> None:
    source = inspect.getsource(CanonicalDashboardMixin._build_canonical_dashboard_page)
    assert "_build_dashboard_sources_card" in source
    assert "_build_dashboard_queue_card" in source
    assert "_build_dashboard_details_card" in source
    assert "_build_dashboard_scheduler_card" in source


def test_header_has_compact_runtime_badges_and_no_theme_combobox() -> None:
    source = inspect.getsource(CanonicalShellChromeMixin._build_shell_header)
    assert "FFmpeg …" in source
    assert "GPU …" in source
    assert "Cache …" in source
    assert "shell_theme_combo" not in source
    assert "shell_font_combo" not in source


def test_visual_compare_reports_relative_geometry_metrics(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.png"
    actual = tmp_path / "actual.png"
    Image.new("RGB", (1448, 1086), "#08111f").save(baseline)
    Image.new("RGB", (1858, 1080), "#08111f").save(actual)

    result = compare_visual("relative-size", baseline, actual)

    assert result.baseline_size == (1448, 1086)
    assert result.actual_size == (1858, 1080)
    assert result.aspect_ratio_delta > 0
    assert 0 <= result.changed_pixel_ratio <= 1
    assert 0 <= result.edge_difference <= 1


def test_visual_capture_targets_real_canonical_application() -> None:
    source = Path("scripts/capture_visual_scenarios.py").read_text(encoding="utf-8")
    assert "CanonicalVideoBatchFastUI(root)" in source
    assert "VideoBatchFastUI(root)" not in source.replace("CanonicalVideoBatchFastUI(root)", "")


def test_header_relayouts_after_dynamic_badge_status_and_font_changes() -> None:
    build_source = inspect.getsource(CanonicalShellChromeMixin._build_shell_header)
    badge_source = inspect.getsource(CanonicalShellChromeMixin._refresh_shell_runtime_badges)
    helper_source = inspect.getsource(CanonicalShellChromeMixin._request_shell_header_layout)
    assert "_request_shell_header_layout()" in build_source
    assert "_request_shell_header_layout()" in badge_source
    assert "after_idle" in helper_source
    assert "_shell_header_layout_after_id" in helper_source


def test_visual_registry_covers_required_zoom_acceptance_profiles() -> None:
    import json

    registry = json.loads(Path("registries/VISUAL_REGRESSION_REGISTRY.json").read_text(encoding="utf-8"))
    dashboard = {(int(item["width"]), int(item["height"]), int(item["font_scale"])) for item in registry["scenarios"] if item.get("group") == "dashboard"}
    assert (1440, 900, 90) in dashboard
    assert (1500, 920, 105) in dashboard
    assert (1440, 900, 125) in dashboard
    assert (1920, 1080, 125) in dashboard
    assert (1920, 1080, 140) in dashboard
