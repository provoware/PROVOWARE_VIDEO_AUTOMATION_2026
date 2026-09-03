from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

from videobatch_fast.error_handling import error_definition
from videobatch_fast.runtime_error_guidance import (
    classify_runtime_exception,
    exception_fingerprint,
)
from videobatch_fast import runtime_error_hooks

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


def test_exception_fingerprint_is_stable_for_same_incident() -> None:
    exc = RuntimeError("same failure")
    first = exception_fingerprint(type(exc), exc, None, scope="runtime")
    second = exception_fingerprint(type(exc), exc, None, scope="runtime")
    other = exception_fingerprint(type(exc), exc, None, scope="thread")
    assert first == second
    assert first != other
    assert len(first) == 16


def test_duplicate_incidents_are_suppressed_inside_window(monkeypatch) -> None:
    runtime_error_hooks._recent_fingerprints.clear()
    moments = iter((100.0, 105.0, 113.0))
    monkeypatch.setattr(runtime_error_hooks.time, "monotonic", lambda: next(moments))
    assert runtime_error_hooks._claim_fingerprint("ABC") is True
    assert runtime_error_hooks._claim_fingerprint("ABC") is False
    assert runtime_error_hooks._claim_fingerprint("ABC") is True


def test_capture_adds_code_and_fingerprint_to_debug_context(monkeypatch) -> None:
    runtime_error_hooks._recent_fingerprints.clear()
    captured: dict[str, object] = {}

    def fake_capture_exception(*args, **kwargs):
        captured.update(kwargs)
        return None

    monkeypatch.setattr(runtime_error_hooks.RUNTIME, "capture_exception", fake_capture_exception)
    exc = PermissionError("denied")
    handled = runtime_error_hooks.capture_runtime_exception(
        type(exc),
        exc,
        None,
        scope="runtime",
        fatal=False,
        where="test",
        root=None,
        auto_open=False,
    )
    assert handled is True
    context = captured["extra_context"]
    assert isinstance(context, dict)
    assert context["Fehlercode"] == "RUNTIME_PERMISSION_DENIED"
    assert len(str(context["Fehler-Fingerprint"])) == 16


def test_canonical_ui_uses_only_central_runtime_hooks() -> None:
    source = (ROOT / "src/videobatch_fast/canonical_ui.py").read_text(encoding="utf-8")
    assert "from .runtime_error_hooks import (" in source
    assert "root.report_callback_exception = tk_exception_handler(root)" in source
    assert "install_thread_debug_hook()" in source
    assert "capture_runtime_exception(" in source
    assert "def _tk_exception_handler" not in source
    assert "def _install_thread_debug_hook" not in source
    assert 'error_definition("UNKNOWN")' not in source
