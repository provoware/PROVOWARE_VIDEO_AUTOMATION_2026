from __future__ import annotations

WORKFLOW_LAYOUT_MODES = {"two_columns", "wide", "compact"}
DEFAULT_WORKFLOW_LAYOUT_MODE = "two_columns"


def normalize_workflow_layout_mode(value: object) -> str:
    """Return a supported workflow layout without importing a GUI toolkit."""
    selected = str(value)
    return selected if selected in WORKFLOW_LAYOUT_MODES else DEFAULT_WORKFLOW_LAYOUT_MODE
