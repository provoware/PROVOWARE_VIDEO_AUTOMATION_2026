#!/usr/bin/env python3
from __future__ import annotations

import os
import tempfile
from itertools import combinations
from pathlib import Path


def _cancel_callbacks(root) -> None:
    try:
        for callback_id in root.tk.call("after", "info"):
            try:
                root.after_cancel(callback_id)
            except Exception:
                pass
    except Exception:
        pass


def _destroy(root, app) -> None:
    try:
        controller = getattr(app, "selection_previews", None)
        if controller is not None:
            controller.close()
    except Exception:
        pass
    _cancel_callbacks(root)
    root.destroy()


def _rect(widget) -> tuple[int, int, int, int]:
    x = int(widget.winfo_x())
    y = int(widget.winfo_y())
    return x, y, x + int(widget.winfo_width()), y + int(widget.winfo_height())


def _assert_no_overlap(widgets, label: str) -> None:
    visible = [
        widget
        for widget in widgets
        if bool(widget.winfo_ismapped())
        and int(widget.winfo_width()) > 1
        and int(widget.winfo_height()) > 1
    ]
    for left, right in combinations(visible, 2):
        lx1, ly1, lx2, ly2 = _rect(left)
        rx1, ry1, rx2, ry2 = _rect(right)
        overlap_width = min(lx2, rx2) - max(lx1, rx1)
        overlap_height = min(ly2, ry2) - max(ly1, ry1)
        if overlap_width > 1 and overlap_height > 1:
            raise AssertionError(
                f"{label}: Widgets überlagern sich: "
                f"{left.winfo_class()} {_rect(left)} / "
                f"{right.winfo_class()} {_rect(right)}"
            )


def _assert_inside_parent(parent, widgets, label: str, tolerance: int = 2) -> None:
    parent_width = int(parent.winfo_width())
    parent_height = int(parent.winfo_height())
    if parent_width <= 1 or parent_height <= 1:
        raise AssertionError(f"{label}: Container besitzt keine nutzbare Größe.")
    for widget in widgets:
        if not bool(widget.winfo_ismapped()):
            continue
        x1, y1, x2, y2 = _rect(widget)
        if x1 < -tolerance or y1 < -tolerance:
            raise AssertionError(f"{label}: Widget beginnt außerhalb: {_rect(widget)}")
        if x2 > parent_width + tolerance or y2 > parent_height + tolerance:
            raise AssertionError(
                f"{label}: Widget endet außerhalb {_rect(widget)} / "
                f"Container {(parent_width, parent_height)}"
            )


def _settle(root) -> None:
    root.update_idletasks()
    root.update()
    root.update_idletasks()


def _assert_canonical_layout(root, app, geometry: str, scale: int) -> None:
    app._set_global_zoom(scale)
    root.geometry(geometry)
    app.main_notebook.select(0)
    _settle(root)

    if app._dashboard_layout_mode not in {"stacked", "two_columns", "three_columns"}:
        raise AssertionError(
            f"Unbekannter Dashboardmodus: {app._dashboard_layout_mode!r}"
        )
    if not bool(app._dashboard_canvas.cget("yscrollcommand")):
        raise AssertionError("Dashboard besitzt keinen vertikalen Scrollvertrag.")
    if not app._dashboard_canvas.cget("scrollregion"):
        raise AssertionError("Dashboard besitzt keinen berechneten Scrollbereich.")

    header_children = (
        app._shell_header_identity,
        app._shell_header_search_host,
        app._shell_header_controls,
    )
    _assert_no_overlap(header_children, "Kopfzeile")
    _assert_inside_parent(app._shell_header, header_children, "Kopfzeile")

    _assert_no_overlap(app._shell_kpi_cards, "KPI-Zeile")
    _assert_inside_parent(app._shell_kpi_row, app._shell_kpi_cards, "KPI-Zeile")

    action_parent = app._shell_action_buttons[0].master
    _assert_no_overlap(app._shell_action_buttons, "Aktionsleiste")
    _assert_inside_parent(
        action_parent,
        app._shell_action_buttons,
        "Aktionsleiste",
    )

    dashboard_cards = (
        app._dashboard_sources_card,
        app._dashboard_queue_card,
        app._dashboard_details_card,
        app._dashboard_scheduler_card,
        app._dashboard_appearance_card,
    )
    _assert_no_overlap(dashboard_cards, "Dashboardkarten")
    _assert_inside_parent(
        app._dashboard_surface,
        dashboard_cards,
        "Dashboardkarten",
    )

    app.main_notebook.select(5)
    _settle(root)
    help_widgets = tuple(app.help_intent_buttons.values()) + (
        app._help_intent_note,
    )
    _assert_no_overlap(help_widgets, "Hilfeeinstiege")
    _assert_inside_parent(
        app._help_intent_frame,
        help_widgets,
        "Hilfeeinstiege",
    )


def main() -> int:
    """Verify tabs, area zoom and the canonical responsive shell in one GUI run."""
    with tempfile.TemporaryDirectory(prefix="vbfast_layout_gui_") as tmp:
        base = Path(tmp)
        os.environ["XDG_CONFIG_HOME"] = str(base / "config")
        os.environ["XDG_STATE_HOME"] = str(base / "state")
        os.environ["XDG_CACHE_HOME"] = str(base / "cache")

        from tkinter import Tk
        from videobatch_fast.canonical_ui import CanonicalVideoBatchFastUI

        root = Tk()
        app = CanonicalVideoBatchFastUI(root)
        for geometry, scale in (
            ("1024x680+0+0", 125),
            ("1366x768+0+0", 105),
            ("1500x920+0+0", 90),
        ):
            _assert_canonical_layout(root, app, geometry, scale)

        app.main_notebook.select(1)
        app._set_area_zoom("media", 140)
        app._save_settings()
        _settle(root)

        if app._active_workspace_layout_profile != "tabs":
            raise AssertionError("Aktueller Layoutvertrag ist nicht auf stabile Tabs gebunden.")
        if app._capture_workspace_layout_profile():
            raise AssertionError("Historische Splitterpositionen dürfen nicht mehr gespeichert werden.")
        grid = app.workflow_grids.get("media")
        if grid is None or len(grid.cards) < 1:
            raise AssertionError("Medien-Workflowraster wurde nicht aufgebaut.")
        if not bool(grid.canvas.cget("yscrollcommand")):
            raise AssertionError("Workflowraster besitzt keinen sichtbaren Scrollvertrag.")
        if app.area_zoom.get("media") != 140:
            raise AssertionError("Bereichszoom wurde nicht angewendet.")
        _destroy(root, app)

        root = Tk()
        app = CanonicalVideoBatchFastUI(root)
        root.geometry("1280x720+0+0")
        _settle(root)
        if app._active_workspace_layout_profile != "tabs":
            raise AssertionError("Tablayout wurde nach Neustart nicht wiederhergestellt.")
        if app.area_zoom.get("media") != 140:
            raise AssertionError("Bereichszoom wurde nach Neustart nicht wiederhergestellt.")
        app.main_notebook.select(1)
        _settle(root)
        grid = app.workflow_grids["media"]
        bbox = grid.canvas.bbox("all")
        if not bbox or bbox[3] <= 0:
            raise AssertionError("Medienraster besitzt keinen erreichbaren Inhaltsbereich.")
        _destroy(root, app)

    print(
        "GUI-TAB-GRID-ROUNDTRIP BESTANDEN · "
        "kanonische Shell + Überlagerungsschutz + Tabs + Scrollraster + Bereichszoom"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
