from __future__ import annotations

import inspect
from pathlib import Path

from videobatch_fast.project_home_dashboard import ProjectHomeDashboardMixin


class _Var:
    def __init__(self) -> None:
        self.value = ""

    def set(self, value: str) -> None:
        self.value = value


class _Harness(ProjectHomeDashboardMixin):
    pass


def test_phase2_sources_overview_remains_first_expanded_lower_card() -> None:
    placeholders = inspect.getsource(ProjectHomeDashboardMixin._build_project_home_placeholders)
    sources = inspect.getsource(ProjectHomeDashboardMixin._build_project_home_sources_overview)
    assert "_build_project_home_sources_overview(row, 0)" in placeholders
    assert "Medienbibliothek öffnen" in sources
    assert "_open_project_workspace(1)" in sources
    assert placeholders.count("Noch leer") == 1
    assert placeholders.count("Für spätere Inhalte") == 1
    for title in ("Render-Profile", "Historie / Logs"):
        assert title in placeholders
    assert "_build_project_home_workflow_overview(row, 1)" in placeholders


def test_phase2_sources_overview_uses_existing_audio_and_media_collections(tmp_path: Path) -> None:
    existing_audio = tmp_path / "track.wav"
    existing_audio.write_bytes(b"x")
    missing_media = tmp_path / "missing.mp4"
    harness = _Harness()
    harness.audios = [existing_audio]
    harness.media = [missing_media]
    harness._project_home_sources_total = _Var()
    harness._project_home_sources_audio = _Var()
    harness._project_home_sources_media = _Var()
    harness._project_home_sources_missing = _Var()

    harness._refresh_project_home_sources()

    assert harness._project_home_sources_total.value == "2 Quellen"
    assert harness._project_home_sources_audio.value == "Audio: 1"
    assert harness._project_home_sources_media.value == "Bilder / Videos: 1"
    assert harness._project_home_sources_missing.value == "Nicht verfügbar: 1"


def test_phase2_sources_refresh_is_safe_before_card_creation() -> None:
    harness = _Harness()
    harness.audios = []
    harness.media = []
    harness._refresh_project_home_sources()
