from __future__ import annotations

import ast
from pathlib import Path

from videobatch_fast.canonical_shell_contract import (
    dashboard_layout_mode,
    responsive_column_count,
)
from videobatch_fast.window_geometry import (
    normalize_window_geometry,
    safe_minimum_window_size,
)

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "src" / "videobatch_fast" / "canonical_shell_workspace.py"
DASHBOARD = ROOT / "src" / "videobatch_fast" / "canonical_dashboard_mixin.py"
HELP_STATUS = ROOT / "src" / "videobatch_fast" / "canonical_help_status_mixin.py"
CHROME = ROOT / "src" / "videobatch_fast" / "canonical_shell_chrome.py"
CANONICAL_UI = ROOT / "src" / "videobatch_fast" / "canonical_ui.py"
WINDOW_MIXIN = ROOT / "src" / "videobatch_fast" / "canonical_window_mixin.py"
TEST_SH = ROOT / "test.sh"
VERIFY_SH = ROOT / "verify_release.sh"
VIDEOBATCH_SH = ROOT / "videobatch.sh"


def test_dashboard_breakpoints_are_complete_and_stable() -> None:
    assert dashboard_layout_mode(0) == "stacked"
    assert dashboard_layout_mode(759) == "stacked"
    assert dashboard_layout_mode(760) == "two_columns"
    assert dashboard_layout_mode(1119) == "two_columns"
    assert dashboard_layout_mode(1120) == "three_columns"


def test_responsive_column_count_never_returns_invalid_values() -> None:
    assert responsive_column_count(0, 220, 5) == 1
    assert responsive_column_count(300, 220, 5) == 1
    assert responsive_column_count(700, 220, 5) == 3
    assert responsive_column_count(5000, 220, 5) == 5
    assert responsive_column_count(500, 0, 0) == 1


def test_saved_window_geometry_is_clamped_to_visible_screen() -> None:
    minimum = safe_minimum_window_size(1366, 768)
    assert minimum == (1024, 680)
    geometry = normalize_window_geometry("2200x1400-500-400", 1366, 768)
    assert geometry.width <= 1310
    assert geometry.height <= 712
    assert geometry.x >= 0
    assert geometry.y >= 0
    assert geometry.x + geometry.width <= 1366
    assert geometry.y + geometry.height <= 768


def test_invalid_window_geometry_falls_back_deterministically() -> None:
    first = normalize_window_geometry("kaputt", 1920, 1080)
    second = normalize_window_geometry("", 1920, 1080)
    assert first == second
    assert first.as_tk().startswith("1500x920+")


def test_canonical_dashboard_contains_real_scrollable_zones() -> None:
    workspace = WORKSPACE.read_text(encoding="utf-8")
    dashboard = DASHBOARD.read_text(encoding="utf-8")
    help_status = HELP_STATUS.read_text(encoding="utf-8")
    for path, source in (
        (WORKSPACE, workspace),
        (DASHBOARD, dashboard),
        (HELP_STATUS, help_status),
    ):
        ast.parse(source, filename=str(path))
    for token in (
        "_build_canonical_dashboard_page",
        "_build_dashboard_sources_card",
        "_build_dashboard_queue_card",
        "_build_dashboard_details_card",
        "_build_dashboard_scheduler_card",
        "_build_dashboard_appearance_card",
        "yscrollcommand",
        "scrollregion",
        "dashboard_layout_mode",
        "Reale Aufträge aus dem aktuellen Projekt; keine Musterwerte.",
        "_refresh_dashboard_sources",
        "_select_dashboard_job",
    ):
        assert token in dashboard
    assert "self._build_start_page(assistant_body)" in dashboard
    assert "kein automatischer Start" in dashboard
    assert "self._build_dashboard_page(pages[0])" in workspace
    assert "responsive_column_count" in help_status
    assert "_build_canonical_status_bar" in help_status


def test_header_and_controls_use_requested_width_instead_of_fixed_wrap_only() -> None:
    source = CHROME.read_text(encoding="utf-8")
    ast.parse(source, filename=str(CHROME))
    assert "winfo_reqwidth()" in source
    assert "_layout_shell_header" in source
    assert "_layout_shell_kpis" in source
    assert "_layout_shell_actions" in source
    assert "wraplength=max(130" in source


def test_canonical_window_mixin_is_selected_before_shell_workspace() -> None:
    ui_source = CANONICAL_UI.read_text(encoding="utf-8")
    mixin_source = WINDOW_MIXIN.read_text(encoding="utf-8")
    ast.parse(ui_source, filename=str(CANONICAL_UI))
    ast.parse(mixin_source, filename=str(WINDOW_MIXIN))
    assert ui_source.index("CanonicalWindowMixin") < ui_source.index(
        "CanonicalShellWorkspaceMixin"
    )
    assert "CanonicalDashboardMixin" in ui_source
    assert "CanonicalHelpStatusMixin" in ui_source
    assert "normalize_window_geometry" in mixin_source
    assert "self.root.minsize" in mixin_source


def test_local_verification_does_not_claim_reproducible_release() -> None:
    test_source = TEST_SH.read_text(encoding="utf-8")
    verify_source = VERIFY_SH.read_text(encoding="utf-8")
    starter_source = VIDEOBATCH_SH.read_text(encoding="utf-8")
    assert "--local" in test_source
    assert "run_external_quality.py" in test_source
    assert "KEINE STABLE-FREIGABE" in test_source
    assert 'exec "$ROOT_DIR/test.sh" --local' in verify_source
    assert "--strict" in verify_source
    assert 'exec "$ROOT_DIR/verify_release.sh" "$@"' in starter_source
    assert "verify --strict" in starter_source
