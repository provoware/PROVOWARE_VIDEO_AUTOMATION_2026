from videobatch_fast.error_handling import explain_runtime_problem


def test_no_space_error_includes_actionable_solution() -> None:
    title, help_text = explain_runtime_problem("ffmpeg: No space left on device")
    assert "Speicher" in title
    assert "anderen Ausgabeordner" in help_text


def test_unknown_error_never_claims_recovery() -> None:
    title, help_text = explain_runtime_problem("not identified by the mapping")
    assert "konnte nicht abgeschlossen" in title
    assert "prüfen" in help_text


def test_permissions_must_not_recommend_unsafe_chmod() -> None:
    title, help_text = explain_runtime_problem("Permission denied")
    assert "zugreifen" in title
    assert "777" not in help_text
    assert "sudo" not in help_text
