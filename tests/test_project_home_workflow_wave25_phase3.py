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


def test_phase3_workflow_overview_is_second_expanded_lower_card() -> None:
    placeholders = inspect.getsource(ProjectHomeDashboardMixin._build_project_home_placeholders)
    workflow = inspect.getsource(ProjectHomeDashboardMixin._build_project_home_workflow_overview)
    assert "_build_project_home_sources_overview(row, 0)" in placeholders
    assert "_build_project_home_workflow_overview(row, 1)" in placeholders
    assert 'start=2' in placeholders
    assert "Workflow & Queue öffnen" in workflow
    assert "_open_project_workspace(4)" in workflow
    for title in ("Render-Profile", "Historie / Logs"):
        assert title in placeholders
    assert '("Workflow-Module", "effects")' not in placeholders


def test_phase3_workflow_overview_reads_existing_workflow_and_queue_state() -> None:
    harness = _Harness()
    harness.quick_mode = _Var("smart_auto")
    harness.visual_effect = _Var("ken_burns")
    harness.transition = _Var("crossfade")
    harness.jobs = [object(), object()]
    harness._project_home_workflow_mode = _Var()
    harness._project_home_workflow_effect = _Var()
    harness._project_home_workflow_transition = _Var()
    harness._project_home_workflow_jobs = _Var()

    harness._refresh_project_home_workflow()

    assert harness._project_home_workflow_mode.value == "Schnellmodus: smart_auto"
    assert harness._project_home_workflow_effect.value == "Effekt: ken_burns"
    assert harness._project_home_workflow_transition.value == "Übergang: crossfade"
    assert harness._project_home_workflow_jobs.value == "2 Aufträge vorbereitet"


def test_phase3_workflow_overview_handles_single_job_and_missing_variables() -> None:
    harness = _Harness()
    harness.jobs = [object()]
    harness._project_home_workflow_mode = _Var()
    harness._project_home_workflow_effect = _Var()
    harness._project_home_workflow_transition = _Var()
    harness._project_home_workflow_jobs = _Var()

    harness._refresh_project_home_workflow()

    assert harness._project_home_workflow_jobs.value == "1 Auftrag vorbereitet"
    assert harness._project_home_workflow_mode.value == "Schnellmodus: —"
    assert harness._project_home_workflow_effect.value == "Effekt: —"
    assert harness._project_home_workflow_transition.value == "Übergang: —"


def test_phase3_workflow_refresh_is_safe_before_card_creation() -> None:
    harness = _Harness()
    harness.jobs = []
    harness._refresh_project_home_workflow()
