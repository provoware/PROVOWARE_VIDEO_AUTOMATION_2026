from __future__ import annotations

import inspect

from videobatch_fast.canonical_help_status_mixin import (
    CanonicalHelpStatusMixin,
    compact_feedback_text,
)


def test_compact_feedback_text_separates_state_from_next_step() -> None:
    status, guidance = compact_feedback_text(
        "  Prüfung\nläuft  ",
        "  Zielordner prüfen\nund danach Queue starten.  ",
    )
    assert status == "Status: Prüfung läuft"
    assert guidance == "Nächster Schritt: Zielordner prüfen und danach Queue starten."


def test_compact_feedback_text_has_safe_fallbacks_and_bounds() -> None:
    status, guidance = compact_feedback_text("", "", status_limit=12, guidance_limit=24)
    assert status == "Status: Bereit"
    assert guidance == "Nächster Schritt: Keine Aktion erforderlich."

    status, guidance = compact_feedback_text(
        "x" * 100,
        "y" * 300,
        status_limit=12,
        guidance_limit=24,
    )
    assert status == "Status: " + ("x" * 11) + "…"
    assert guidance == "Nächster Schritt: " + ("y" * 23) + "…"


def test_feedback_footer_is_responsive_and_updates_both_information_channels() -> None:
    source = inspect.getsource(CanonicalHelpStatusMixin)
    formatter = inspect.getsource(compact_feedback_text)
    for token in (
        'self.guidance_text.trace_add("write", sync_feedback)',
        'self.status_text.trace_add("write", sync_feedback)',
        '_semantic_footer_status_label',
        'available < 760',
        'guidance.configure(wraplength=max(240, available - 20))',
    ):
        assert token in source
    assert 'f"Status: {status_value}"' in formatter
    assert 'f"Nächster Schritt: {guidance_value}"' in formatter


def test_feedback_footer_remains_presentation_only() -> None:
    source = inspect.getsource(CanonicalHelpStatusMixin)
    forbidden = (
        "write_text(",
        "write_bytes(",
        "unlink(",
        "remove(",
        "rename(",
        "subprocess",
        "ffmpeg",
        "self.jobs =",
        "self.media =",
        "self.audios =",
    )
    for token in forbidden:
        assert token not in source
