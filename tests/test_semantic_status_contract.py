from __future__ import annotations

import inspect

from videobatch_fast.canonical_semantic_status_mixin import (
    CanonicalSemanticStatusMixin,
    semantic_status_state,
)


def test_semantic_status_state_prioritizes_errors_over_warnings() -> None:
    assert semantic_status_state("WARNUNG: Fehler im Zielpfad") == "error"
    assert semantic_status_state("Fehlgeschlagen") == "error"


def test_semantic_status_state_covers_warning_success_and_neutral() -> None:
    assert semantic_status_state("Prüfung läuft") == "warning"
    assert semantic_status_state("Achtung: wenig Speicher") == "warning"
    assert semantic_status_state("Bereit") == "success"
    assert semantic_status_state("Export bestanden") == "success"
    assert semantic_status_state("VideoBatch Fast") == "neutral"


def test_semantic_status_layer_is_presentation_only() -> None:
    source = inspect.getsource(CanonicalSemanticStatusMixin)
    forbidden = (
        "command=",
        "write_text(",
        "write_bytes(",
        "unlink(",
        "remove(",
        "rename(",
        "self.jobs =",
        "self.media =",
        "self.audios =",
        "subprocess",
        "ffmpeg",
    )
    for token in forbidden:
        assert token not in source
    assert "status_text.trace_add" in source
    assert "ShellSemanticStatus" in source
    assert "ShellSemanticSidebar" in source
