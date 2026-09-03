from __future__ import annotations

import subprocess
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace

from videobatch_fast.error_handling import error_definition
from videobatch_fast.runtime_error_guidance import (
    classify_runtime_exception,
    exception_fingerprint,
    exception_location,
)
from videobatch_fast import error_handling, registry, runtime_error_hooks

ROOT = Path(__file__).resolve().parents[1]


def test_frozen_instance_error_has_stable_specific_contract() -> None:
    exc = FrozenInstanceError("cannot assign to field 'status'")
    guidance = classify_runtime_exception(type(exc), exc, scope="tkinter")
    assert guidance.code == "INTERNAL_IMMUTABLE_STATE_ERROR"
    assert guidance.what != "Unbekanntes Problem"
    assert guidance.solutions


def test_common_runtime_exceptions_are_not_collapsed_to_unknown() -> None:
    cases = (
        (PermissionError("blocked"), "RUNTIME_PERMISSION_DENIED"),
        (FileNotFoundError("missing"), "RUNTIME_FILE_OR_TOOL_MISSING"),
        (MemoryError("memory"), "RUNTIME_MEMORY_LIMIT_REACHED"),
        (subprocess.TimeoutExpired("ffmpeg", 1), "RUNTIME_SUBPROCESS_FAILED"),
        (ValueError("bad value"), "RUNTIME_INVALID_STATE"),
        (OSError("device"), "RUNTIME_OS_ERROR"),
        (RuntimeError("other"), "RUNTIME_UNHANDLED_EXCEPTION"),
    )
    for exc, expected in cases:
        assert classify_runtime_exception(type(exc), exc).code == expected


def test_runtime_registry_definitions_are_resolved() -> None:
    definition = error_definition("INTERNAL_IMMUTABLE_STATE_ERROR")
    assert definition.title == "Ein interner Zustand war schreibgeschützt"
    assert definition.severity == "blocking"
    assert "open_logs" in definition.actions


def test_transient_registry_failure_does_not_poison_runtime_definitions(monkeypatch) -> None:
    real_load = error_handling.load_json
    failed_once = False

    def flaky_load(path: str):
        nonlocal failed_once
        if path == "registries/RUNTIME_ERROR_REGISTRY.json" and not failed_once:
            failed_once = True
            raise error_handling.RegistryError("temporär nicht lesbar")
        return real_load(path)

    monkeypatch.setattr(error_handling, "load_json", flaky_load)
    first = error_handling.error_definition("INTERNAL_IMMUTABLE_STATE_ERROR")
    second = error_handling.error_definition("INTERNAL_IMMUTABLE_STATE_ERROR")
    assert first.title == "Unbekanntes Problem"
    assert second.title == "Ein interner Zustand war schreibgeschützt"


def test_runtime_registry_is_part_of_central_registry_validation() -> None:
    assert "registries/RUNTIME_ERROR_REGISTRY.json" in registry.REQUIRED_REGISTRIES


def test_exception_fingerprint_is_stable_for_same_incident() -> None:
    exc = RuntimeError("same failure")
    first = exception_fingerprint(type(exc), exc, None, scope="runtime")
    second = exception_fingerprint(type(exc), exc, None, scope="runtime")
    other = exception_fingerprint(type(exc), exc, None, scope="thread")
    assert first == second
    assert first != other
    assert len(first) == 16


def test_exception_location_points_to_deepest_python_frame() -> None:
    try:
        raise RuntimeError("location probe")
    except RuntimeError as exc:
        location = exception_location(exc.__traceback__)
    assert "test_runtime_error_hardening.py" in location
    assert "test_exception_location_points_to_deepest_python_frame()" in location


def test_duplicate_incidents_are_suppressed_inside_window(monkeypatch) -> None:
    runtime_error_hooks._recent_fingerprints.clear()
    moments = iter((100.0, 105.0, 113.0))
    monkeypatch.setattr(runtime_error_hooks.time, "monotonic", lambda: next(moments))
    assert runtime_error_hooks._claim_fingerprint("ABC") is True
    assert runtime_error_hooks._claim_fingerprint("ABC") is False
    assert runtime_error_hooks._claim_fingerprint("ABC") is True


def test_capture_adds_code_location_and_falls_back_without_report(monkeypatch) -> None:
    runtime_error_hooks._recent_fingerprints.clear()
    captured: dict[str, object] = {}

    def fake_capture_exception(*args, **kwargs):
        captured.update(kwargs)
        return None

    monkeypatch.setattr(runtime_error_hooks.RUNTIME, "capture_exception", fake_capture_exception)
    try:
        raise PermissionError("denied")
    except PermissionError as exc:
        handled = runtime_error_hooks.capture_runtime_exception(
            type(exc),
            exc,
            exc.__traceback__,
            scope="runtime",
            fatal=False,
            where="test",
            root=None,
            auto_open=False,
        )
    assert handled is False
    context = captured["extra_context"]
    assert isinstance(context, dict)
    assert context["Fehlercode"] == "RUNTIME_PERMISSION_DENIED"
    assert len(str(context["Fehler-Fingerprint"])) == 16
    assert "test_runtime_error_hardening.py" in str(captured["where"])
    assert not runtime_error_hooks._recent_fingerprints


def test_thread_hook_calls_previous_hook_when_central_report_is_unavailable(monkeypatch) -> None:
    seen: list[object] = []
    previous = lambda args: seen.append(args)
    monkeypatch.setattr(runtime_error_hooks, "_thread_hook_installed", False)
    monkeypatch.setattr(runtime_error_hooks.threading, "excepthook", previous)
    monkeypatch.setattr(
        runtime_error_hooks,
        "capture_runtime_exception",
        lambda *args, **kwargs: False,
    )
    runtime_error_hooks.install_thread_debug_hook()
    installed = runtime_error_hooks.threading.excepthook
    args = SimpleNamespace(
        exc_type=RuntimeError,
        exc_value=RuntimeError("worker failed"),
        exc_traceback=None,
        thread=SimpleNamespace(name="worker"),
    )
    installed(args)
    assert seen == [args]


def test_canonical_ui_uses_only_central_runtime_hooks() -> None:
    source = (ROOT / "src/videobatch_fast/canonical_ui.py").read_text(encoding="utf-8")
    assert "from .runtime_error_hooks import (" in source
    assert "root.report_callback_exception = tk_exception_handler(root)" in source
    assert "install_thread_debug_hook()" in source
    assert "capture_runtime_exception(" in source
    assert "def _tk_exception_handler" not in source
    assert "def _install_thread_debug_hook" not in source
    assert 'error_definition("UNKNOWN")' not in source
    assert "except BaseException as exc:" not in source


def test_legacy_ui_entry_delegates_to_canonical_runtime_path() -> None:
    source = (ROOT / "src/videobatch_fast/ui.py").read_text(encoding="utf-8")
    run_app = source[source.rfind("\ndef run_app() -> None:") :]
    assert "from .canonical_ui import run_app as run_canonical_app" in run_app
    assert "run_canonical_app()" in run_app
    assert "report_callback_exception" not in run_app
    assert 'error_definition("UNKNOWN")' not in run_app
