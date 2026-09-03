from __future__ import annotations

from pathlib import Path

from videobatch_fast.config import DEFAULT_CONFIG, normalize_config
from videobatch_fast.debug_runtime import HumanDebugRuntime, debug_enabled_from_config

ROOT = Path(__file__).resolve().parents[1]


def test_debug_mode_defaults_on_and_persists_boolean() -> None:
    assert DEFAULT_CONFIG["debug_mode"] is True
    assert normalize_config({"debug_mode": False})["debug_mode"] is False
    assert normalize_config({"debug_mode": True})["debug_mode"] is True


def test_debug_preference_reads_user_config(monkeypatch, tmp_path: Path) -> None:
    config_home = tmp_path / "config"
    target = config_home / "VideoBatchFast" / "config.json"
    target.parent.mkdir(parents=True)
    target.write_text('{"debug_mode": false}\n', encoding="utf-8")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    monkeypatch.delenv("VIDEOBATCH_DEBUG", raising=False)
    assert debug_enabled_from_config() is False
    monkeypatch.setenv("VIDEOBATCH_DEBUG", "1")
    assert debug_enabled_from_config() is True


def test_human_report_contains_required_questions(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("VIDEOBATCH_DEBUG_DIR", str(tmp_path))
    runtime = HumanDebugRuntime()
    runtime.set_enabled(True)
    incident = runtime.capture_message(
        what="Testfehler",
        how="Vertragstest",
        where="tests/test_debug_runtime_contract.py",
        solutions=("Bericht prüfen", "Schritt reproduzieren"),
        auto_open=False,
        force=True,
        prefix="TESTBERICHT",
    )
    assert incident is not None
    assert incident.path.parent == tmp_path
    assert incident.path.is_file()
    text = incident.path.read_text(encoding="utf-8")
    for heading in (
        "WAS IST PASSIERT?",
        "WIE WURDE ES ERKANNT?",
        "WO IST ES PASSIERT?",
        "LÖSUNGSMÖGLICHKEITEN",
        "SYSTEM- UND SITZUNGSKONTEXT",
    ):
        assert heading in text
    assert "Dieser Bericht wurde lokal erzeugt" in text


def test_exception_report_keeps_traceback_and_source_location(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("VIDEOBATCH_DEBUG_DIR", str(tmp_path))
    runtime = HumanDebugRuntime()
    runtime.set_enabled(True)
    try:
        raise RuntimeError("gezielter-testfehler")
    except RuntimeError as exc:
        incident = runtime.capture_exception(
            type(exc),
            exc,
            exc.__traceback__,
            what="Gezielter Fehler",
            how="Test hat absichtlich eine Ausnahme ausgelöst",
            solutions=("Bericht prüfen",),
            auto_open=False,
            force=True,
        )
    assert incident is not None
    text = incident.path.read_text(encoding="utf-8")
    assert "RuntimeError: gezielter-testfehler" in text
    assert "VOLLSTÄNDIGER PYTHON-TRACEBACK" in text
    assert "test_exception_report_keeps_traceback_and_source_location" in text


def test_clean_shutdown_marker_is_written(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("VIDEOBATCH_DEBUG_DIR", str(tmp_path / "reports"))
    runtime = HumanDebugRuntime()
    marker = tmp_path / "state" / "clean.marker"
    runtime.set_clean_shutdown_marker(marker)
    runtime.mark_clean_shutdown()
    assert marker.is_file()
    assert marker.read_text(encoding="utf-8").strip()


def test_canonical_ui_installs_debug_before_constructing_application() -> None:
    source = (ROOT / "src/videobatch_fast/canonical_ui.py").read_text(encoding="utf-8")
    assert "CanonicalDebugMixin" in source
    assert source.index("root.report_callback_exception") < source.index("CanonicalVideoBatchFastUI(root)")
    assert "capture_runtime_exception(" in source
    assert "VIDEOBATCH_DEBUG_CLEAN_MARKER" in source


def test_debug_controls_are_visible_and_persistent() -> None:
    source = (ROOT / "src/videobatch_fast/canonical_debug_mixin.py").read_text(encoding="utf-8")
    for label in (
        "Debugmodus · ausführliche verständliche Diagnose",
        "Debugbericht jetzt erstellen",
        "Debugging-Ordner öffnen",
    ):
        assert label in source
    assert 'self.config["debug_mode"] = enabled' in source
    assert "RUNTIME.set_enabled(enabled)" in source
    assert "ab dem nächsten Programmstart vollständig aktiv" in source


def test_interactive_dialog_supports_solution_and_action_selection() -> None:
    source = (ROOT / "src/videobatch_fast/debug_runtime.py").read_text(encoding="utf-8")
    for token in (
        "LÖSUNG?",
        "selected_solution",
        "Ausgewählte Lösung kopieren",
        "Interaktive Aktion auswählen:",
        "Ausgewählte Aktion ausführen",
    ):
        assert token in source


def test_launchers_route_normal_start_through_debug_wrapper() -> None:
    start_here = (ROOT / "STARTEN.sh").read_text(encoding="utf-8")
    start = (ROOT / "start.sh").read_text(encoding="utf-8")
    launcher = (ROOT / "scripts/debug_launcher.py").read_text(encoding="utf-8")
    videobatch = (ROOT / "videobatch.sh").read_text(encoding="utf-8")
    assert "scripts/debug_launcher.py" in start_here
    assert 'exec "$ROOT_DIR/STARTEN.sh"' in start
    assert "_monitor_application" in launcher
    assert "PROZESSABSTURZ" in launcher
    assert "UI_READY pid=" in launcher
    assert "bootstrap_*.log" in videobatch
    assert "application_*.log" in videobatch
    assert "MENSCHLICHER DEBUGBERICHT" in videobatch


def test_debugging_folder_does_not_version_generated_reports() -> None:
    ignore = (ROOT / "debugging/.gitignore").read_text(encoding="utf-8")
    assert "*.txt" in ignore
    assert "*.log" in ignore
    assert "*.json" in ignore
    assert (ROOT / "debugging/README.md").is_file()
