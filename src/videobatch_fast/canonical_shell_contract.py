from __future__ import annotations

from dataclasses import dataclass

CANONICAL_THEME_LABELS = {
    "neon_gravity": "Midnight Blue",
    "acid_paper": "Emerald Tech",
    "toxic_candy": "Violet Pulse",
    "ultraviolet": "Amber Graphite",
}
FONT_PROFILES = {"Kompakt": 90, "Standard": 105, "Groß": 125}


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
