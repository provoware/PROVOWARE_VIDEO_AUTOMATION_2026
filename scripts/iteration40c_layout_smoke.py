#!/usr/bin/env python3
from __future__ import annotations

import os
from tkinter import Tk

os.environ.setdefault("VIDEOBATCH_SAFE_MODE", "1")

from videobatch_fast.canonical_ui import CanonicalVideoBatchFastUI


def main() -> int:
    root = Tk()
    root.geometry("1858x1080")
    app = CanonicalVideoBatchFastUI(root)
    app._set_area_zoom("production", 70)
    app._select_shell_page(4)
    root.update_idletasks()

    grid = app.workflow_grids["production"]
    assert len(grid.cards) == 4
    assert len(app.preparation_tree.get_children()) >= 1

    grid.canvas.yview_moveto(0.55)
    root.update_idletasks()
    before = grid.canvas.yview()[0]
    if grid.canvas.yview()[1] < 1.0:
        assert before > 0.0

    app._select_shell_page(4)
    root.update_idletasks()
    assert grid.canvas.yview()[0] == 0.0

    for _ in range(5):
        root.update_idletasks()

    root.destroy()
    print("ITERATION40C_WORKSPACE_GEOMETRY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
