from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from videobatch_fast.failure_intelligence import (
    capture_exception_with_intelligence,
    load_summary,
    mark_resolved,
    record_exception,
)


def _raise_failure(job_id: int) -> None:
    raise RuntimeError(
        f"job {job_id} failed at /tmp/videobatch-run-{job_id}/output token=top-secret"
    )


def _capture(job_id: int, directory: Path):
    try:
        _raise_failure(job_id)
    except RuntimeError as exc:
        return record_exception(
            type(exc),
            exc,
            exc.__traceback__,
            directory=directory,
            operation_id=f"job:{job_id}",
        )
    raise AssertionError("Testfehler wurde nicht ausgelöst")


def test_same_semantic_failure_gets_unique_occurrences_and_stable_fingerprint(tmp_path: Path) -> None:
    first, _ = _capture(101812177021, tmp_path)
    second, _ = _capture(101812176629, tmp_path)

    assert first.occurrence_id != second.occurrence_id
    assert first.fingerprint == second.fingerprint
    assert first.regression_state == "new"
    assert second.regression_state == "known"
    assert second.occurrence_count == 2
    assert first.source_file.endswith("tests/test_failure_intelligence.py")
    assert first.source_line > 0
    assert first.source_function == "_raise_failure"
    assert "top-secret" not in first.message
    assert "101812177021" not in first.message
    assert "101812176629" not in second.message

    rows = [
        json.loads(line)
        for line in (tmp_path / "failure_occurrences.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    assert len(rows) == 2
    assert rows[0]["fingerprint"] == rows[1]["fingerprint"]
    assert rows[0]["occurrence_id"] != rows[1]["occurrence_id"]


def test_resolved_failure_is_classified_as_regression_on_reappearance(tmp_path: Path) -> None:
    first, _ = _capture(11, tmp_path)
    resolved = mark_resolved(
        first.fingerprint,
        directory=tmp_path,
        resolution="Regressionstest ergänzt und Ursache behoben.",
    )
    assert resolved["state"] == "resolved"
    assert resolved["resolved_at"]

    repeated, _ = _capture(12, tmp_path)
    assert repeated.fingerprint == first.fingerprint
    assert repeated.regression_state == "regressed"
    assert repeated.occurrence_count == 2
    assert repeated.regression_count == 1

    summary = load_summary(directory=tmp_path)
    assert summary["total"] == 1
    assert summary["counts"] == {
        "new": 0,
        "known": 0,
        "resolved": 0,
        "regressed": 1,
    }


def test_different_semantic_failures_do_not_collapse_to_one_fingerprint(tmp_path: Path) -> None:
    first, _ = _capture(1, tmp_path)

    try:
        raise ValueError("different semantic failure")
    except ValueError as exc:
        second, _ = record_exception(
            type(exc),
            exc,
            exc.__traceback__,
            directory=tmp_path,
        )

    assert first.fingerprint != second.fingerprint


def test_corrupt_ledger_is_quarantined_before_recovery(tmp_path: Path) -> None:
    ledger = tmp_path / "failure_regressions.json"
    ledger.write_text("{not-json", encoding="utf-8")

    occurrence, quarantined = _capture(42, tmp_path)

    assert occurrence.regression_state == "new"
    assert quarantined is not None
    assert quarantined.is_file()
    assert quarantined.read_text(encoding="utf-8") == "{not-json"
    recovered = json.loads(ledger.read_text(encoding="utf-8"))
    assert recovered["schema_version"] == 1
    assert occurrence.fingerprint in recovered["entries"]


class _RuntimeProbe:
    def __init__(self) -> None:
        self.args: tuple[Any, ...] | None = None
        self.kwargs: dict[str, Any] | None = None

    def capture_exception(self, *args: Any, **kwargs: Any) -> str:
        self.args = args
        self.kwargs = kwargs
        return "captured"


def test_capture_wrapper_adds_exact_source_and_regression_details(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("VIDEOBATCH_DEBUG_DIR", str(tmp_path))
    runtime = _RuntimeProbe()

    try:
        _raise_failure(77)
    except RuntimeError as exc:
        result = capture_exception_with_intelligence(
            runtime,
            type(exc),
            exc,
            exc.__traceback__,
            operation_id="ui-callback",
            what="Testfehler",
            how="Gezielt ausgelöst",
            where="Tkinter-Callback",
            extra_context={"Bestehend": "bleibt"},
            fatal=False,
            auto_open=False,
        )

    assert result == "captured"
    assert runtime.kwargs is not None
    where = runtime.kwargs["where"]
    details = runtime.kwargs["extra_context"]
    assert "Tkinter-Callback · Fehlerursprung:" in where
    assert "tests/test_failure_intelligence.py:" in where
    assert "_raise_failure()" in where
    assert details["Bestehend"] == "bleibt"
    assert len(details["Ereignis-ID"]) == 32
    assert len(details["Fehler-Fingerprint"]) == 24
    assert details["Regressionsstatus"] == "new"
    assert details["Quelldatei"].endswith("tests/test_failure_intelligence.py")
    assert details["Zeile"] > 0
    assert details["Funktion"] == "_raise_failure"
    assert details["Operations-ID"] == "ui-callback"


def test_canonical_ui_routes_all_exception_channels_through_intelligence() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "videobatch_fast"
        / "canonical_ui.py"
    ).read_text(encoding="utf-8")

    assert "from .failure_intelligence import capture_exception_with_intelligence" in source
    assert source.count("capture_exception_with_intelligence(") == 3
    assert "RUNTIME.capture_exception(" not in source
    assert 'operation_id="ui-callback"' in source
    assert 'operation_id=f"thread:{args.thread.name}"' in source
    assert 'operation_id="application-main"' in source
