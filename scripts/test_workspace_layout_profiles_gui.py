#!/usr/bin/env python3
from __future__ import annotations

import os
import tempfile
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
        controller = getattr(app, "_selection_preview_controller", None)
        if controller is not None:
            controller.close()
    except Exception:
        pass
    _cancel_callbacks(root)
    root.destroy()


def main() -> int:
    """Verify the current tab/grid layout instead of the retired splitter API."""
    with tempfile.TemporaryDirectory(prefix="vbfast_layout_gui_") as tmp:
        base = Path(tmp)
        os.environ["XDG_CONFIG_HOME"] = str(base / "config")
        os.environ["XDG_STATE_HOME"] = str(base / "state")
        os.environ["XDG_CACHE_HOME"] = str(base / "cache")

        from tkinter import Tk
        from videobatch_fast.ui import VideoBatchFastUI

        root = Tk()
        app = VideoBatchFastUI(root)
        root.geometry("1280x720")
        app.main_notebook.select(1)
        app._set_area_zoom("media", 140)
        app._save_settings()
        root.update_idletasks()
        root.update()

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
        app = VideoBatchFastUI(root)
        root.geometry("1280x720")
        root.update_idletasks()
        root.update()
        if app._active_workspace_layout_profile != "tabs":
            raise AssertionError("Tablayout wurde nach Neustart nicht wiederhergestellt.")
        if app.area_zoom.get("media") != 140:
            raise AssertionError("Bereichszoom wurde nach Neustart nicht wiederhergestellt.")
        app.main_notebook.select(1)
        root.update_idletasks()
        grid = app.workflow_grids["media"]
        bbox = grid.canvas.bbox("all")
        if not bbox or bbox[3] <= 0:
            raise AssertionError("Medienraster besitzt keinen erreichbaren Inhaltsbereich.")
        _destroy(root, app)

    print("GUI-TAB-GRID-ROUNDTRIP BESTANDEN · Tabs + Scrollraster + Bereichszoom")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
