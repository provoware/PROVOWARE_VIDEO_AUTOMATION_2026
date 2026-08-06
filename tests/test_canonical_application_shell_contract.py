from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHELLS = tuple((ROOT / "src/videobatch_fast" / name) for name in (
    "canonical_ui.py",
    "canonical_kpi.py",
    "canonical_kpi_detail_mixin.py",
    "canonical_kpi_compact_mixin.py",
    "canonical_shell_contract.py",
    "canonical_shell_chrome.py",
    "canonical_shell_workspace.py",
    "canonical_dashboard_mixin.py",
    "canonical_help_status_mixin.py",
    "canonical_window_mixin.py",
    "window_geometry.py",
))
APP = ROOT / "src/videobatch_fast/app.py"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_canonical_shell_is_syntactically_valid_and_selected_by_app() -> None:
    for path in SHELLS:
        ast.parse(_source(path), filename=str(path))
    ast.parse(_source(APP), filename=str(APP))
    assert "from .canonical_ui import run_app" in _source(APP)
    assert "from .ui import run_app" not in _source(APP)


def test_shell_keeps_every_existing_workflow_page_reachable() -> None:
    source = "\n".join(_source(path) for path in SHELLS)
    for builder in (
        "_build_start_page",
        "_build_media_page",
        "_build_preview_page",
        "_build_modes_page",
        "_build_production_page",
        "_build_help_page",
    ):
        assert f"self.{builder}(" in source
    for navigation_label in (
        "Dashboard",
        "Medien",
        "Queue",
        "Effekte",
        "Scheduler",
        "Vorschau",
        "Diagnose",
        "Einstellungen",
    ):
        assert navigation_label in source


def test_shell_exposes_complete_primary_action_contract() -> None:
    source = "\n".join(_source(path) for path in SHELLS)
    for callback in (
        "self._new_project",
        "self._add_audio",
        "self._add_media",
        "self._open_settings",
        "self._start",
        "self._choose_directory",
    ):
        assert callback in source
    assert "Startzeituhr · Checkpoint 5" in source
    assert '"disabled"' in source
    assert "kein automatischer Start" in source


def test_shell_uses_canonical_theme_and_font_profiles() -> None:
    source = "\n".join(_source(path) for path in SHELLS)
    for label in ("Midnight Blue", "Emerald Tech", "Violet Pulse", "Amber Graphite"):
        assert label in source
    for label, scale in (("Kompakt", 90), ("Standard", 105), ("Groß", 125)):
        assert f'"{label}": {scale}' in source


def test_checkpoint3_kpi_cards_have_real_states_and_navigation_actions() -> None:
    source = "\n".join(_source(path) for path in SHELLS)
    for state in ("empty", "ready", "loading", "success", "warning", "error", "disabled"):
        assert f'"{state}"' in source
    for label in ("Medien öffnen", "Queue öffnen", "Effekte öffnen", "Checkpoint 5"):
        assert label in source
    assert "build_kpi_snapshots(" in source
    assert "self._select_shell_page(index)" in source
    assert "self._refresh_kpi_cards()" in source
    assert "CanonicalKpiCompactMixin" in source
    assert "ShellKpiLink.TButton" in source


def test_canonical_dashboard_has_all_required_visual_zones() -> None:
    source = "\n".join(_source(path) for path in SHELLS)
    for zone in (
        "Quellen & Projekt",
        "Render Queue",
        "Jobdetails & Vorschau",
        "Startzeituhr",
        "Darstellung",
        "_build_canonical_status_bar",
    ):
        assert zone in source
    assert "dashboard_layout_mode" in source
    assert "responsive_column_count" in source
    assert "normalize_window_geometry" in source
    assert "CanonicalDashboardMixin" in source
    assert "CanonicalHelpStatusMixin" in source
