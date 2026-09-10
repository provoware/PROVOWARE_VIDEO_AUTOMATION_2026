from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "videobatch_fast"

PHASE3_FILES = (
    SRC / "qt_phase3.py",
    SRC / "qt_phase3_components.py",
)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase3_qt_modules_are_tk_free_and_parseable() -> None:
    for path in PHASE3_FILES:
        source = _text(path)
        ast.parse(source, filename=str(path))
        lowered = source.casefold()
        assert "tkinter" not in lowered
        assert "toplevel(" not in lowered
        assert "mainloop(" not in lowered
        assert "pyside6" in lowered


def test_phase3_reuses_verified_project_and_assurance_services() -> None:
    app = _text(SRC / "qt_phase3.py")
    components = _text(SRC / "qt_phase3_components.py")

    for symbol in (
        "load_project_state",
        "save_project_state",
        "projects_dir",
        "build_diagnostic_payload",
        "VideoBatchQtPhase2Window",
    ):
        assert symbol in app

    for symbol in (
        "run_scenarios",
        "run_fault_lab",
        "WorkspaceNavigationPanel",
        "ProjectPanel",
        "DiagnosticsPanel",
    ):
        assert symbol in components


def test_phase3_workspace_routes_cover_complete_operator_flow() -> None:
    source = _text(SRC / "qt_phase3_components.py")
    for route in (
        "dashboard",
        "media",
        "preview",
        "slideshow",
        "effects",
        "queue",
        "project",
        "diagnostics",
    ):
        assert f'(\"{route}\",' in source


def test_project_persistence_is_fail_safe_during_active_processing() -> None:
    source = _text(SRC / "qt_phase3.py")
    tree = ast.parse(source)
    functions = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert "_autosave_project" in functions
    assert "_save_current_project" in functions
    assert "runner.running" in source
    assert "self.preparing" in source
    assert "AUTOSAVE_INTERVAL_MS = 300_000" in source


def test_phase3_does_not_switch_the_legacy_entrypoint_yet() -> None:
    app = _text(SRC / "app.py")
    phase3 = _text(SRC / "qt_phase3.py")
    assert "from .canonical_ui import run_app" in app
    assert "def main()" in phase3
    assert "VideoBatchQtPhase3Window" in phase3


def _load_acceptance_isolation_module():
    import importlib.util

    path = ROOT / "scripts" / "validate_acceptance_isolation.py"
    spec = importlib.util.spec_from_file_location("validate_acceptance_isolation_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_one_click_acceptance_isolates_all_persistent_user_paths_before_runtime_prepare() -> None:
    source = _text(ROOT / "KUBUNTU_26_04_QT_ABNAHME.sh")
    required = (
        'export HOME="$TEST_HOME"',
        'export XDG_DATA_HOME="$TEST_HOME/.local/share"',
        'export XDG_CONFIG_HOME="$TEST_HOME/.config"',
        'export XDG_STATE_HOME="$TEST_HOME/.local/state"',
        'export XDG_CACHE_HOME="$TEST_HOME/.cache"',
        "validate_acceptance_isolation.py",
        "unset VIDEOBATCH_INSTALL_ROOT",
    )
    for text in required:
        assert text in source

    prepare = source.index('toolchain.py" prepare --scope runtime')
    for text in required[:5]:
        assert source.index(text) < prepare

    assert "export XDG_RUNTIME_DIR=" not in source
    assert "unset XDG_RUNTIME_DIR" not in source


def test_acceptance_isolation_validator_is_fail_closed(tmp_path) -> None:
    isolation = _load_acceptance_isolation_module()
    home = tmp_path / "test-home"
    report_root = home / ".local/state/VideoBatchFast/acceptance/run/startpfad-state/VideoBatchFast/installer"
    report_root.mkdir(parents=True)
    env = {
        "HOME": str(home),
        "XDG_DATA_HOME": str(home / ".local/share"),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "XDG_STATE_HOME": str(home / ".local/state"),
        "XDG_CACHE_HOME": str(home / ".cache"),
        "XDG_RUNTIME_DIR": "/run/user/1000",
    }
    report = {
        "schema_version": 1,
        "canonical_install_root": str(home / ".local/share/VideoBatchFast"),
        "current_install_root": None,
        "destructive_cleanup_allowed": False,
        "legacy_installations_detected": [],
        "legacy_installations_retired": [],
        "legacy_installations_blocked": [],
        "desktop_entries_removed": [],
        "canonical_desktop_entry": str(home / ".local/share/applications/videobatch-fast.desktop"),
        "canonical_launcher": str(home / ".local/bin/videobatch-fast"),
        "controller_versions_removed": [],
        "protected_user_data": [
            str(home / ".config/VideoBatchFast"),
            str(home / ".local/state/VideoBatchFast"),
            str(home / ".cache/VideoBatchFast"),
            str(home / "Videos"),
        ],
    }
    report_path = report_root / isolation.REPORT_NAME
    import json

    report_path.write_text(json.dumps(report), encoding="utf-8")
    result = isolation.validate(home, home / ".local/state/VideoBatchFast/acceptance", env)
    assert result["status"] == "passed", result

    report["canonical_launcher"] = str(tmp_path / "real-home/.local/bin/videobatch-fast")
    report_path.write_text(json.dumps(report), encoding="utf-8")
    result = isolation.validate(home, home / ".local/state/VideoBatchFast/acceptance", env)
    assert result["status"] == "failed"
    assert any("canonical_launcher" in error for error in result["errors"])


def test_remote_wayland_launcher_proves_the_same_isolated_user_boundary() -> None:
    workflow = _text(ROOT / ".github" / "workflows" / "qt6-phase3-smoke.yml")
    for token in (
        "HOME: ${{ runner.temp }}/videobatch-start-normal/home",
        "XDG_DATA_HOME: ${{ runner.temp }}/videobatch-start-normal/home/.local/share",
        "XDG_STATE_HOME: ${{ runner.temp }}/videobatch-start-normal/home/.local/state",
        "XDG_CONFIG_HOME: ${{ runner.temp }}/videobatch-start-normal/home/.config",
        "XDG_CACHE_HOME: ${{ runner.temp }}/videobatch-start-normal/home/.cache",
        "scripts/validate_acceptance_isolation.py",
        '--test-home "$HOME"',
        '--report-root "$XDG_STATE_HOME/VideoBatchFast/installer"',
    ):
        assert token in workflow

    prepare = workflow.index("Prepare verified private Qt runtime for launcher")
    launch = workflow.index("Prove STARTEN.sh to Qt UI-ready, isolated user paths and clean shutdown")
    assert prepare < launch
    assert workflow.count("VIDEOBATCH_INSTALL_ROOT VIDEOBATCH_PORTABLE_LAUNCHER VIDEOBATCH_PORTABLE") >= 2


def _load_qt_acceptance_module():
    import importlib.util

    path = ROOT / "scripts" / "qt_desktop_acceptance.py"
    spec = importlib.util.spec_from_file_location("qt_desktop_acceptance_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_internal_qt_acceptance_fails_closed_without_isolated_test_home(tmp_path) -> None:
    acceptance = _load_qt_acceptance_module()
    real_home = tmp_path / "real-home"
    env = {
        "HOME": str(real_home),
        "XDG_DATA_HOME": str(real_home / ".local/share"),
        "XDG_CONFIG_HOME": str(real_home / ".config"),
        "XDG_STATE_HOME": str(real_home / ".local/state"),
        "XDG_CACHE_HOME": str(real_home / ".cache"),
    }
    ok, detail = acceptance.acceptance_environment_status(env)
    assert ok is False
    assert "VIDEOBATCH_ACCEPTANCE_TEST_HOME fehlt" in detail

    test_home = tmp_path / "test-home"
    env.update({
        "VIDEOBATCH_ACCEPTANCE_TEST_HOME": str(test_home),
        "HOME": str(test_home),
        "XDG_DATA_HOME": str(test_home / ".local/share"),
        "XDG_CONFIG_HOME": str(test_home / ".config"),
        "XDG_STATE_HOME": str(test_home / ".local/state"),
        "XDG_CACHE_HOME": str(test_home / ".cache"),
    })
    ok, detail = acceptance.acceptance_environment_status(env)
    assert ok is True, detail

    source = _text(ROOT / "scripts" / "qt_desktop_acceptance.py")
    main = source.index("def main() -> int:")
    guard = source.index("acceptance_environment_status()", main)
    first_write = source.index("folder = run_dir()", main)
    assert guard < first_write
    assert "VIDEOBATCH_ACCEPTANCE_TEST_HOME" not in _text(ROOT / "scripts" / "bootstrap.py")


def test_remote_safe_mode_reuses_verified_runtime_without_leaving_its_test_home() -> None:
    workflow = _text(ROOT / ".github" / "workflows" / "qt6-phase3-smoke.yml")
    for token in (
        "HOME: ${{ runner.temp }}/videobatch-start-safe/home",
        "XDG_DATA_HOME: ${{ runner.temp }}/videobatch-start-safe/home/.local/share",
        "XDG_STATE_HOME: ${{ runner.temp }}/videobatch-start-safe/home/.local/state",
        "XDG_CONFIG_HOME: ${{ runner.temp }}/videobatch-start-safe/home/.config",
        "XDG_CACHE_HOME: ${{ runner.temp }}/videobatch-start-safe/home/.cache",
        'NORMAL_DATA_HOME="$RUNNER_TEMP/videobatch-start-normal/home/.local/share"',
        'XDG_DATA_HOME="$NORMAL_DATA_HOME" python scripts/toolchain.py path --scope runtime --quiet',
        'test -x "$RUNTIME_PY"',
        '"scripts/qt_desktop_acceptance.py"',
        '"docs/KUBUNTU_26_04_QT_ABNAHME.md"',
    ):
        assert token in workflow
