from __future__ import annotations

from scripts.test_workspace_layout_profiles_gui import _settle


class _NeverIdleTk:
    def __init__(self) -> None:
        self.calls = 0

    def dooneevent(self, _flags: int) -> int:
        self.calls += 1
        return 1


class _FakeRoot:
    def __init__(self) -> None:
        self.tk = _NeverIdleTk()
        self.idle_calls = 0

    def update_idletasks(self) -> None:
        self.idle_calls += 1


def test_settle_is_bounded_even_when_event_queue_never_becomes_empty() -> None:
    root = _FakeRoot()
    _settle(root, max_events=7, max_seconds=10.0)
    assert root.tk.calls == 7
    assert root.idle_calls == 2
