from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from videobatch_fast.canonical_dashboard_mixin import CanonicalDashboardMixin


class _Tree:
    def __init__(self):
        self.insert_calls = []
    def get_children(self): return ()
    def delete(self, _item): pass
    def insert(self, parent, index, **kwargs):
        assert kwargs.get("image", "missing") is not None
        self.insert_calls.append(kwargs)
        return "row1"
    def selection_set(self, _item): pass
    def focus(self, _item): pass


class _Var:
    def __init__(self, value): self.value = value
    def get(self): return self.value


class _Harness(CanonicalDashboardMixin):
    def __init__(self):
        self._dashboard_queue_tree = _Tree()
        self._dashboard_selected_job_index = None
        self._dashboard_queue_filter = _Var("")
        self._dashboard_queue_status_filter = _Var("Alle")
        self.quick_mode = _Var("smart_auto")
        self.visual_effect = _Var("none")
    def _queue_thumbnail_source(self, _job): return Path("/missing/source.png")
    def _queue_thumbnail_photo(self, _source): return None
    def _request_queue_thumbnail(self, _item, _job): pass
    def _prune_queue_thumbnail_refs(self, _sources): pass


def test_queue_insert_omits_image_option_when_thumbnail_is_not_ready() -> None:
    harness = _Harness()
    job = SimpleNamespace(index=1, output=Path("out.mp4"), audio=Path("a.wav"))
    harness._refresh_dashboard_queue((job,), ())
    assert len(harness._dashboard_queue_tree.insert_calls) == 1
    assert "image" not in harness._dashboard_queue_tree.insert_calls[0]
