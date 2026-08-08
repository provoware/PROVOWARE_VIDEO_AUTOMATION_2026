from __future__ import annotations

from videobatch_fast.ui_services_mixin import UiServicesMixin


class _Runner:
    running = False


class _SelectionPreviews:
    def shutdown(self, timeout=0):
        return True


class _Tasks:
    def shutdown(self, timeout=0):
        return ()


class _Audio:
    def stop(self):
        return None


class _Root:
    def __init__(self):
        self.destroy_calls = 0

    def destroy(self):
        self.destroy_calls += 1


class _Harness(UiServicesMixin):
    def __init__(self):
        self.runner = _Runner()
        self.selection_previews = _SelectionPreviews()
        self.tasks = _Tasks()
        self.audio_player = _Audio()
        self.root = _Root()
        self.events = []
        self.autosave_calls = 0
        self.settings_calls = 0

    def _cancel_pending_selection_preview(self):
        return None

    def _autosave_project(self, force=False):
        self.autosave_calls += 1
        raise OSError("disk read-only")

    def _save_settings(self):
        self.settings_calls += 1
        raise OSError("settings unavailable")

    def _event(self, *args, **kwargs):
        self.events.append((args, kwargs))


def test_shutdown_is_idempotent_and_destroy_is_guaranteed_on_persistence_errors() -> None:
    harness = _Harness()
    harness._close()
    harness._close()
    assert harness.root.destroy_calls == 1
    assert harness.autosave_calls == 1
    assert harness.settings_calls == 1
    assert any(args and args[0] == "SHUTDOWN_PARTIAL_FAILURE" for args, _kwargs in harness.events)
