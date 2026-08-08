from __future__ import annotations

from pathlib import Path

from videobatch_fast.preparation_assistant import PreparationCheck
from videobatch_fast.startup_readiness import build_startup_readiness

ROOT = Path(__file__).resolve().parents[1]


def _green_checks() -> list[PreparationCheck]:
    return [
        PreparationCheck("audio", "ok", "Audio", "2 ausgewählt"),
        PreparationCheck("media", "ok", "Medien", "8 ausgewählt"),
        PreparationCheck("analysis", "ok", "Analyse", "Bereit"),
        PreparationCheck("settings", "ok", "Einstellungen", "Geprüft"),
        PreparationCheck("output", "ok", "Ausgabe", "/tmp"),
        PreparationCheck("archive", "ok", "Ablage", "Aus"),
        PreparationCheck("pairing", "ok", "Zuordnung", "2 Aufträge"),
    ]


def test_warning_is_not_painted_green() -> None:
    checks = _green_checks()
    checks[2] = PreparationCheck(
        "analysis", "warning", "Analyse", "Analyse läuft", "focus_waveform"
    )
    model = build_startup_readiness(project_name="Projekt", checks=checks)
    assert model.overall_status == "warning"
    assert model.next_step_key == "media"
    assert not model.ready
    assert model.steps[-1].status == "warning"


def test_render_is_green_only_when_every_precursor_is_green() -> None:
    model = build_startup_readiness(project_name="Projekt", checks=_green_checks())
    assert model.ready
    assert model.ready_count == 6
    assert model.warning_count == 0
    assert model.error_count == 0
    assert model.steps[-1].detail == "Render bereit"


def test_blocker_propagates_to_render_and_next_action() -> None:
    checks = _green_checks()
    checks[0] = PreparationCheck("audio", "error", "Audio", "Fehlt", "add_audio")
    model = build_startup_readiness(project_name="Projekt", checks=checks)
    media = next(step for step in model.steps if step.key == "media")
    assert media.status == "error"
    assert media.action == "add_audio"
    assert model.overall_status == "error"
    assert model.next_step_key == "media"
    assert model.steps[-1].status == "error"


def test_unwritable_missing_project_path_falls_back_to_user_state(tmp_path, monkeypatch) -> None:
    from videobatch_fast import project_state

    requested = tmp_path / "blocked" / "sicherer_start.vbfast.json"
    fallback = tmp_path / "state" / "aktuelles_projekt.vbfast.json"
    real_atomic_write = project_state.atomic_write_json

    monkeypatch.setattr(project_state, "ensure_app_dirs", lambda: None)
    monkeypatch.setattr(project_state, "default_project_file", lambda: fallback)

    def guarded_write(path: Path, payload, **kwargs):
        if Path(path) == requested:
            raise PermissionError(13, "Permission denied", str(path))
        return real_atomic_write(path, payload, **kwargs)

    monkeypatch.setattr(project_state, "atomic_write_json", guarded_write)
    selected, state, healed = project_state.load_project_state(requested)

    assert selected == fallback
    assert fallback.is_file()
    assert healed is True
    assert state["schema_version"] == project_state.PROJECT_SCHEMA_VERSION


def test_canonical_shell_contains_start_check_without_dashboard_bloat() -> None:
    ui_source = (ROOT / "src/videobatch_fast/canonical_ui.py").read_text(encoding="utf-8")
    workspace = (ROOT / "src/videobatch_fast/canonical_shell_workspace.py").read_text(
        encoding="utf-8"
    )
    dashboard = (ROOT / "src/videobatch_fast/canonical_dashboard_mixin.py").read_text(
        encoding="utf-8"
    )

    assert "CanonicalStartCheckMixin" in ui_source
    assert "self._build_shell_start_check(content)" in workspace
    assert "workspace.grid(row=4" in workspace
    assert "build_startup_readiness" not in dashboard


def test_runtime_residue_is_ignored_without_overblocking_debugging() -> None:
    root_ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    debug_ignore = (ROOT / "debugging/.gitignore").read_text(encoding="utf-8")

    assert "/diagnostics/**/*.log" in root_ignore
    assert "*.tmp" in root_ignore
    assert "*.bak" in root_ignore
    assert "/debugging/*" not in root_ignore
    assert "*.txt" in debug_ignore
    assert "*.log" in debug_ignore
    assert "*.json" in debug_ignore
    assert "*_save_.md" not in root_ignore
