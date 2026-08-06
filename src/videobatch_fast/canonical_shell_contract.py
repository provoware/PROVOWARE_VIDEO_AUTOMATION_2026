from __future__ import annotations

from dataclasses import dataclass

CANONICAL_THEME_LABELS = {
    "neon_gravity": "Midnight Blue",
    "acid_paper": "Emerald Tech",
    "toxic_candy": "Violet Pulse",
    "ultraviolet": "Amber Graphite",
}
FONT_PROFILES = {"Kompakt": 90, "Standard": 105, "Groß": 125}

# Breakpoints beziehen sich auf die tatsächlich verfügbare Inhaltsbreite rechts
# neben der festen Sidebar. Dadurch bleiben sie bei KDE-Skalierung und
# unterschiedlichen Fensterdekorationen reproduzierbar.
DASHBOARD_STACKED_MAX = 759
DASHBOARD_TWO_COLUMN_MAX = 1119
DASHBOARD_COLUMN_WEIGHTS = (22, 48, 30)
SIDEBAR_WIDTH = 220


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
    ShellNavigationItem("scheduler", "◷  Scheduler", None, "disabled"),
    ShellNavigationItem("preview", "▣  Vorschau", 2),
    ShellNavigationItem("diagnostics", "◎  Diagnose", 5),
    ShellNavigationItem("settings", "⚙  Einstellungen", 3, "settings"),
)
