from __future__ import annotations

from tkinter import Tk

from .canonical_kpi_detail_mixin import CanonicalKpiDetailMixin
from .canonical_shell_chrome import CanonicalShellChromeMixin
from .canonical_shell_workspace import CanonicalShellWorkspaceMixin
from .canonical_window_mixin import CanonicalWindowMixin
from .error_handling import error_definition
from .startup_handshake import signal_ui_ready
from .ui import VideoBatchFastUI
from .ui_components import SolutionDialog


class CanonicalVideoBatchFastUI(
    CanonicalKpiDetailMixin,
    CanonicalWindowMixin,
    CanonicalShellWorkspaceMixin,
    CanonicalShellChromeMixin,
    VideoBatchFastUI,
):
    """VB-GFX-1.0 shell around the complete VideoBatch implementation."""


def run_app() -> None:
    root = Tk()
    try:
        root.tk.call("tk", "scaling", max(1.0, root.winfo_fpixels("1i") / 72.0))
    except Exception:
        pass
    CanonicalVideoBatchFastUI(root)
    root.report_callback_exception = lambda exc_type, exc, tb: SolutionDialog(
        root, error_definition("UNKNOWN"), f"{exc_type.__name__}: {exc}"
    )
    root.update_idletasks()
    signal_ui_ready()
    root.mainloop()
