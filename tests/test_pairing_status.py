"""Human-readable readiness must match render start preflight."""
from videobatch_fast.pairing_status import pairing_status


def test_empty_pairing_explains_first_step() -> None:
    state = pairing_status(0, 0, "/tmp/output")
    assert not state.ready
    assert "mindestens eine Audiodatei" in state.explanation


def test_missing_audio_or_media_is_precise() -> None:
    media_missing = pairing_status(3, 2, "/tmp/output")
    assert not media_missing.ready and media_missing.missing_media == 1
    assert "1 Bild" in media_missing.explanation
    audio_missing = pairing_status(1, 3, "/tmp/output")
    assert audio_missing.missing_audio == 2
    assert "2 Audiodatei" in audio_missing.explanation


def test_ready_requires_output_destination() -> None:
    incomplete = pairing_status(2, 2, "   ")
    assert incomplete.pairs_complete and not incomplete.ready
    assert "Ausgabeordner" in incomplete.explanation
    good = pairing_status(2, 2, "/tmp/output")
    assert good.ready and "Bereit für 2" in good.explanation


def test_negative_counts_rejected() -> None:
    import pytest
    with pytest.raises(ValueError):
        pairing_status(-1, 0, "/tmp")
