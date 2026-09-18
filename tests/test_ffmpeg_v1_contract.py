from __future__ import annotations

import ast
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "diagnostics" / "architecture" / "CP-07_FFMPEG_INVENTORY.json"


def _source(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _tree(relative: str) -> ast.Module:
    return ast.parse(_source(relative), filename=relative)


def _call_name(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        parts = [func.attr]
        value = func.value
        while isinstance(value, ast.Attribute):
            parts.append(value.attr)
            value = value.value
        if isinstance(value, ast.Name):
            parts.append(value.id)
        return ".".join(reversed(parts))
    return ""


def _calls(relative: str) -> list[ast.Call]:
    return [node for node in ast.walk(_tree(relative)) if isinstance(node, ast.Call)]


def _call_names(relative: str) -> list[str]:
    return [_call_name(node) for node in _calls(relative)]


def _inventory() -> dict[str, object]:
    payload = json.loads(INVENTORY.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["checkpoint"] == "CP-07"
    assert payload["mode"] == "inventory_only"
    assert payload["product_code_changed"] is False
    return payload


def test_cp07_inventory_freezes_persistence_dependency_and_render_path() -> None:
    payload = _inventory()
    persistence = payload["persistence_dependency"]
    assert isinstance(persistence, dict)
    assert persistence["status"] == "frozen"

    assert payload["canonical_render_path"] == [
        "src/videobatch_fast/qt_ui.py -> BatchRunner",
        "src/videobatch_fast/runner.py -> command_builder.build_command",
        "src/videobatch_fast/runner.py -> ProcessExecution",
        "src/videobatch_fast/runner_process.py -> subprocess.Popen",
    ]


def test_active_qt_boundary_has_no_direct_process_engine() -> None:
    payload = _inventory()
    boundary = payload["active_qt_boundary"]
    assert isinstance(boundary, dict)
    modules = boundary["modules_checked"]
    assert isinstance(modules, list)

    forbidden_calls = {
        "subprocess.Popen",
        "subprocess.run",
        "subprocess.call",
        "subprocess.check_call",
        "subprocess.check_output",
        "QProcess",
        "QtCore.QProcess",
    }

    for relative in modules:
        relative = str(relative)
        source = _source(relative)
        calls = set(_call_names(relative))
        assert not (calls & forbidden_calls), (
            f"{relative} startet im aktiven Qt6-Pfad direkt einen Prozess: "
            f"{sorted(calls & forbidden_calls)}"
        )
        assert "from subprocess import Popen" not in source
        assert "from subprocess import run" not in source
        assert "from PySide6.QtCore import QProcess" not in source


def test_qt_ui_delegates_production_exclusively_to_batch_runner() -> None:
    source = _source("src/videobatch_fast/qt_ui.py")
    calls = _call_names("src/videobatch_fast/qt_ui.py")

    assert "from .runner import BatchRunner" in source
    assert "BatchRunner" in calls
    assert "self.runner.start" in calls
    assert "self.runner.cancel" in calls
    assert "subprocess.Popen" not in calls
    assert "QProcess" not in calls


def test_batch_runner_delegates_execution_without_spawning_ffmpeg_itself() -> None:
    source = _source("src/videobatch_fast/runner.py")
    calls = _call_names("src/videobatch_fast/runner.py")

    assert "from .runner_process import ProcessExecution" in source
    assert "ProcessExecution" in calls
    assert "execution.run" in calls
    assert "subprocess.Popen" not in calls
    assert "subprocess.run" not in calls


def test_runner_process_is_the_single_canonical_render_spawn_owner() -> None:
    relative = "src/videobatch_fast/runner_process.py"
    calls = _calls(relative)
    popen_calls = [node for node in calls if _call_name(node) == "subprocess.Popen"]

    assert len(popen_calls) == 1
    popen = popen_calls[0]
    start_new_session = next(
        (keyword.value for keyword in popen.keywords if keyword.arg == "start_new_session"),
        None,
    )
    assert isinstance(start_new_session, ast.Constant)
    assert start_new_session.value is True


def test_command_builder_remains_the_render_command_owner() -> None:
    relative = "src/videobatch_fast/command_builder.py"
    source = _source(relative)
    calls = _call_names(relative)

    assert "from .probe import ffmpeg_path" in source
    assert "def build_command(" in source
    assert "ffmpeg_path" in calls
    assert "subprocess.Popen" not in calls
    assert "subprocess.run" not in calls
    assert "QProcess" not in calls


def test_probe_boundary_is_read_only_bounded_and_not_a_render_engine() -> None:
    relative = "src/videobatch_fast/probe.py"
    source = _source(relative)
    calls = _calls(relative)
    names = [_call_name(node) for node in calls]
    run_calls = [node for node in calls if _call_name(node) == "subprocess.run"]

    assert len(run_calls) == 2
    assert "subprocess.Popen" not in names
    assert "QProcess" not in names
    assert "build_command" not in source
    assert '"-progress"' not in source
    assert '"-movflags"' not in source
    assert '"-c:v"' not in source
    assert '"-c:a"' not in source

    timeouts: set[int] = set()
    for call in run_calls:
        timeout = next((keyword.value for keyword in call.keywords if keyword.arg == "timeout"), None)
        assert isinstance(timeout, ast.Constant)
        assert isinstance(timeout.value, int)
        timeouts.add(timeout.value)
    assert timeouts == {5, 20}

    forbidden_writes = {
        "write_text",
        "write_bytes",
        "unlink",
        "replace",
        "rename",
        "atomic_write_json",
    }
    assert not (set(names) & forbidden_writes)
    assert not any(name.rsplit(".", 1)[-1] in forbidden_writes for name in names)


def test_ffmpeg_inventory_declares_no_second_active_render_engine() -> None:
    payload = _inventory()
    boundary = payload["active_qt_boundary"]
    assert isinstance(boundary, dict)
    assert boundary["direct_subprocess_render_calls_found"] == 0
    assert boundary["direct_qprocess_render_calls_found"] == 0
    assert boundary["canonical_ui_delegate"] == "BatchRunner"

    findings = payload["collision_findings"]
    assert isinstance(findings, list)
    assert findings
    assert all(isinstance(item, dict) and item.get("status") == "green" for item in findings)
