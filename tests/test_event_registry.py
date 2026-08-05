from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from videobatch_fast.app_events import AppEvent, AppEventError, NOISY_EVENT_NAMES, TERMINAL_EVENT_NAMES
from videobatch_fast.event_registry import EVENT_REGISTRY, noisy_event_names, terminal_event_names

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "check_event_registry.py"

CONTRACT_EVENT_NAMES = frozenset(
    {
        "archive_finished",
        "assurance_finished",
        "batch_failed_internal",
        "batch_finished",
        "batch_started",
        "command",
        "fault_lab_finished",
        "job_failed_internal",
        "job_finished",
        "job_started",
        "log",
        "preview_failed",
        "preview_ready",
        "progress",
        "retry_queue_updated",
        "selection_preview_failed",
        "selection_preview_ready",
        "update_finished",
        "waveform_failed",
        "waveform_ready",
    }
)


def test_contract_event_names_are_explicit_and_complete() -> None:
    assert CONTRACT_EVENT_NAMES == frozenset(EVENT_REGISTRY)
    assert NOISY_EVENT_NAMES == noisy_event_names()
    assert TERMINAL_EVENT_NAMES == terminal_event_names()


@pytest.mark.parametrize("event_name", sorted(CONTRACT_EVENT_NAMES))
def test_every_registered_event_has_a_complete_contract(event_name: str) -> None:
    spec = EVENT_REGISTRY[event_name]
    assert spec.handler.startswith("_handle_")
    assert spec.payload_type
    assert spec.modes
    assert spec.required_fields
    assert not (spec.terminal and spec.noisy)


def test_unknown_events_and_legacy_use_of_typed_events_are_rejected() -> None:
    with pytest.raises(AppEventError, match="Unbekanntes AppEvent"):
        AppEvent("unknown_event", {"message": "blocked"})
    with pytest.raises(AppEventError, match="erlaubt Modus 'legacy' nicht"):
        AppEvent.from_legacy("selection_preview_ready", {"token": 1})


def test_current_event_registry_checker_is_green(tmp_path: Path) -> None:
    output = tmp_path / "event-registry.json"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--source-root",
            str(ROOT / "src" / "videobatch_fast"),
            "--contract-test",
            str(Path(__file__)),
            "--output",
            str(output),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    report = json.loads(output.read_text(encoding="utf-8"))
    assert result.returncode == 0, result.stdout + result.stderr
    assert report["status"] == "pass"
    assert report["findings"] == []
