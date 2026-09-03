from __future__ import annotations

from dataclasses import dataclass

CANONICAL_THEME_LABELS = {
    "neon_gravity": "Midnight Blue",
    "acid_paper": "Emerald Tech",
    "toxic_candy": "Violet Pulse",
    "ultraviolet": "Amber Graphite",
}
FONT_PROFILES = {"Kompakt": 90, "Standard": 105, "Groß": 125}

DASHBOARD_STACKED_MAX = 759
DASHBOARD_TWO_COLUMN_MAX = 1119
DASHBOARD_COLUMN_WEIGHTS = (22, 48, 30)
# A33: mehr Nutzfläche auf 1024/1280/1366px, ohne die Navigation unlesbar zu machen.
SIDEBAR_WIDTH = 188


def dashboard_layout_mode(content_width: int) -> str:
    """Return the canonical dashboard mode for the usable content width."""
    width = max(0, int(content_width))
    if width <= DASHBOARD_STACKED_MAX:
        return "stacked"
    if width <= DASHBOARD_TWO_COLUMN_MAX:
        return "two_columns"
    return "three_columns"


def responsive_column_count(
    available_width: int,
    requested_item_width: int,
    maximum: int,
    *,
    minimum_item_width: int = 145,
) -> int:
    """Fit complete controls without ever returning zero or too many columns."""
    limit = max(1, int(maximum))
    available = max(0, int(available_width))
    requested = max(int(minimum_item_width), int(requested_item_width))
    if available <= 0:
        return 1
    return max(1, min(limit, available // requested))


@dataclass(frozen=True)
class ShellNavigationItem:
    key: str
    label: str
    page_index: int | None
    action: str = "page"


SHELL_NAVIGATION = (
    ShellNavigationItem("dashboard", "⌂  Dashboard", 0),
    ShellNavigationItem("media", "▧  Medien", 1),
    ShellNavigationItem("queue", "☷  Queue", 4),
    ShellNavigationItem("effects", "✦  Effekte", 3),
    ShellNavigationItem("scheduler", "◷  Scheduler · Startzeit", None, "disabled"),
    ShellNavigationItem("preview", "▣  Vorschau", 2),
    ShellNavigationItem("diagnostics", "◎  Hilfe & Diagnose", 5),
    ShellNavigationItem("settings", "⚙  Einstellungen", 3, "settings"),
)
