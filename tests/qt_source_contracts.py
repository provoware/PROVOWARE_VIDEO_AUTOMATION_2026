"""Follow explicit Qt composition boundaries in the existing static contracts.

Behavioral GUI tests remain separate. Moving a helper must not silently drop its
source from architecture, accessibility, or event contract inspections.
"""
from pathlib import Path

_PARTS = {
    "qt_theme.py": ("qt_style_data.py",),
    "qt_ui.py": ("qt_desktop_actions.py", "qt_production_events.py", "qt_media_list.py"),
    "qt_main_layout.py": ("qt_layout_sections.py",),
    "qt_workspace_layout.py": ("qt_workflow_footer.py",),
    "qt_source_panel.py": ("qt_desktop_actions.py",),
    "qt_phase2_components.py": ("qt_slideshow_layout.py",),
    "qt_phase3.py": ("qt_project_persistence.py",),
    "qt_media_import_dialog.py": ("qt_media_browser_layout.py", "qt_media_browser_view.py"),
}


def read_qt_sources(path: Path, encoding: str = "utf-8") -> str:
    paths = (path, *(path.with_name(name) for name in _PARTS.get(path.name, ())))
    source = "\n".join(p.read_text(encoding=encoding) for p in paths)
    # A composed inspection unit must remain parseable by AST-based contracts.
    source = source.replace("from __future__ import annotations\n", "")
    return "from __future__ import annotations\n" + source
