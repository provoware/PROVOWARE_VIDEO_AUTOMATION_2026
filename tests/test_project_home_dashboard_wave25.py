from __future__ import annotations

import inspect

from videobatch_fast.canonical_ui import CanonicalVideoBatchFastUI
from videobatch_fast.project_home_dashboard import ProjectHomeDashboardMixin


def test_wave25_project_home_is_first_mixin_in_canonical_ui() -> None:
    assert CanonicalVideoBatchFastUI.__mro__[1] is ProjectHomeDashboardMixin


def test_project_home_exact_first_step_structure_is_declared() -> None:
    source = inspect.getsource(ProjectHomeDashboardMixin)
    for token in (
        "PROVOWARE VIDEO AUTOMATION",
        "Schritt 1 – Projektstart & Grundkontext",
        "Projektbasis",
        "Medienquellen",
        "Automationsregeln",
        "Render & Export",
        "Infodashboard",
        "Tipps",
        "Quellenübersicht",
        "Workflow-Module",
        "Render-Profile",
        "Historie / Logs",
        "Allgemeine Einstellungen",
        "Projektregeln",
        "Benachrichtigungen",
        "Systempfade",
        "Klar. Robust. Automatisiert.",
        "Noch leer",
        "Für spätere Inhalte",
    ):
        assert token in source


def test_project_home_keeps_four_primary_and_four_placeholder_columns() -> None:
    tiles = inspect.getsource(ProjectHomeDashboardMixin._build_project_home_tiles)
    placeholders = inspect.getsource(ProjectHomeDashboardMixin._build_project_home_placeholders)
    actions = inspect.getsource(ProjectHomeDashboardMixin._build_project_home_actions)
    assert "range(4)" in tiles
    assert "range(4)" in placeholders
    assert "range(4)" in actions
    assert "uniform=\"project-home-tiles\"" in tiles
    assert "uniform=\"project-home-placeholders\"" in placeholders
    assert "uniform=\"project-home-actions\"" in actions


def test_project_home_starts_sparse_and_does_not_embed_live_feature_content() -> None:
    source = inspect.getsource(ProjectHomeDashboardMixin._build_project_home_placeholders)
    assert source.count("Noch leer") == 1
    assert source.count("Für spätere Inhalte") == 1
    assert "Treeview" not in source
    assert "Notebook" not in source


def test_project_home_preserves_existing_workspace_behind_overlay() -> None:
    source = inspect.getsource(ProjectHomeDashboardMixin._build_ui)
    assert "super()._build_ui()" in source
    assert "_build_project_home_overlay" in source


def test_dashboard_navigation_can_return_to_project_home() -> None:
    from videobatch_fast.canonical_shell_workspace import CanonicalShellWorkspaceMixin

    source = inspect.getsource(CanonicalShellWorkspaceMixin._select_shell_page)
    assert 'page_index == 0' in source
    assert '_show_project_home' in source
    assert '_hide_project_home' in source


def test_project_home_is_treated_as_pure_ui_in_business_coverage_scope() -> None:
    pyproject = open("pyproject.toml", encoding="utf-8").read()
    assert '"*/project_home_dashboard.py"' in pyproject
