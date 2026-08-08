from __future__ import annotations

import inspect

from videobatch_fast.project_home_dashboard import ProjectHomeDashboardMixin


class _Var:
    def __init__(self, value: str = "") -> None:
        self.value = value

    def get(self) -> str:
        return self.value

    def set(self, value: str) -> None:
        self.value = value


class _Harness(ProjectHomeDashboardMixin):
    pass


def _prepare_render_vars(harness: _Harness) -> None:
    harness._project_home_render_resolution = _Var()
    harness._project_home_render_codec = _Var()
    harness._project_home_render_profile = _Var()
    harness._project_home_render_target = _Var()


def test_phase4_render_profiles_is_third_expanded_lower_card_only() -> None:
    placeholders = inspect.getsource(ProjectHomeDashboardMixin._build_project_home_placeholders)
    render = inspect.getsource(ProjectHomeDashboardMixin._build_project_home_render_overview)
    assert '_build_project_home_sources_overview(row, 0)' in placeholders
    assert '_build_project_home_workflow_overview(row, 1)' in placeholders
    assert 'if title == "Render-Profile"' in placeholders
    assert '_build_project_home_render_overview(row, column)' in placeholders
    assert '"Historie / Logs"' in placeholders
    assert placeholders.count('Noch leer') == 1
    assert 'Render & Export öffnen' in render
    assert '_open_project_workspace(4)' in render


def test_phase4_render_profiles_reads_existing_render_state(tmp_path) -> None:
    harness = _Harness()
    harness.resolution = _Var("1920×1080")
    harness.codec = _Var("libx264")
    harness.profile = _Var("fast")
    harness.output_dir = _Var(str(tmp_path / "exports"))
    _prepare_render_vars(harness)

    harness._refresh_project_home_render()

    assert harness._project_home_render_resolution.value == "Auflösung: 1920×1080"
    assert harness._project_home_render_codec.value == "Codec: libx264"
    assert harness._project_home_render_profile.value == "Profil: fast"
    assert harness._project_home_render_target.value == "Ziel: exports"


def test_phase4_render_profiles_falls_back_safely_for_missing_variables() -> None:
    harness = _Harness()
    _prepare_render_vars(harness)

    harness._refresh_project_home_render()

    assert harness._project_home_render_resolution.value == "Auflösung: —"
    assert harness._project_home_render_codec.value == "Codec: —"
    assert harness._project_home_render_profile.value == "Profil: —"
    assert harness._project_home_render_target.value == "Ziel: —"


def test_phase4_render_refresh_is_safe_before_card_creation() -> None:
    harness = _Harness()
    harness._refresh_project_home_render()
