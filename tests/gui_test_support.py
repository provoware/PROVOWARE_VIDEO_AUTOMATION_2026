from __future__ import annotations


def legacy_tk_gui_available() -> bool:
    """Return True only when Tk can actually connect to an X display.

    DISPLAY may be set in containers even when no X server is reachable. Legacy
    Tk tests are therefore skipped unless a real display connection succeeds.
    The productive target remains native Qt/Wayland.
    """
    try:
        from tkinter import Tk

        root = Tk()
        root.withdraw()
        root.update_idletasks()
        root.destroy()
    except Exception:
        return False
    return True
