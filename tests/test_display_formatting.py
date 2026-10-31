from __future__ import annotations

import pytest

from videobatch_fast.display_formatting import format_eta


@pytest.mark.parametrize(
    "invalid",
    [float("nan"), float("inf"), float("-inf"), "unbekannt", object(), 10**400],
)
def test_invalid_eta_is_unavailable(invalid: object) -> None:
    assert format_eta(invalid, 21, 50) == "nicht verfügbar"


def test_valid_and_pending_eta_remain_unchanged() -> None:
    assert format_eta(125, 21, 50) == "aktuelle Schätzung · ca. 00:02:05"
    assert format_eta(None, 3, 0) == "wird berechnet"
