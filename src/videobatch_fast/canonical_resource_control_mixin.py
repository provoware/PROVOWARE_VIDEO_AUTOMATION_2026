from __future__ import annotations

from .controlled_runner import ControlledBatchRunner
from .ui_resource_controls_mixin import UiResourceControlsMixin


class CanonicalResourceControlMixin(UiResourceControlsMixin):
    """Attach controlled rendering and the compact resource panel to the canonical shell."""

    def __init__(self, root) -> None:
        super().__init__(root)
        self.runner = ControlledBatchRunner(self.events.put)

    def _build_dashboard_queue_card(self, parent):
        card = super()._build_dashboard_queue_card(parent)
        self._build_resource_process_panel(card, row=5)
        return card
