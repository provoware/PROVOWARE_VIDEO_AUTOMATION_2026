from __future__ import annotations

from typing import Any


class UiLayoutProfilesMixin:
    """Compatibility layer for the former 2×2 splitter layout.

    RC18 uses stable top-level tabs instead of nested sash positions. Existing
    projects may still contain historic layout profiles; they are preserved but
    no longer applied. This removes the resize drift that could move panels back
    after the user had adjusted them.
    """

    def _on_main_tab_changed(self, _event: Any = None) -> None:
        try:
            selected = int(self.main_notebook.index(self.main_notebook.select()))
        except Exception:
            return
        self.config["active_tab"] = selected

    def _workspace_layout_context(self) -> tuple[int, int, int]:
        self.root.update_idletasks()
        return (
            max(320, int(self.root.winfo_width() or self.root.winfo_screenwidth() or 320)),
            max(240, int(self.root.winfo_height() or self.root.winfo_screenheight() or 240)),
            min(300, max(50, int(self.config.get("font_scale", 100) or 100))),
        )

    def _restore_workspace_layout_profile(self) -> None:
        return

    def _capture_workspace_layout_profile(self) -> bool:
        return False

    def _schedule_workspace_layout_save(self, _event: Any = None) -> None:
        return

    def _persist_workspace_layout_profile(self) -> None:
        return

    def _reset_workspace_layout_profile(self) -> None:
        self._clear_workspace_layout_profiles()
        if hasattr(self, "_event"):
            self._event(
                "TAB_LAYOUT_RESET",
                "Tabansicht zurückgesetzt",
                "Historische Rasterpositionen wurden entfernt. Die stabile Tabansicht bleibt aktiv.",
                level="success",
                solution="Bereiche über die oberen Tabs öffnen und separat zoomen.",
            )

    def _initialize_workspace_layout_store(self, raw: Any) -> None:
        self.workspace_layout_profiles = raw if isinstance(raw, dict) else {}
        self._layout_restore_in_progress = False
        self._layout_save_after_id = None
        self._active_workspace_layout_profile = "tabs"
        self._layout_profile_ready = True

    def _clear_workspace_layout_profiles(self) -> None:
        self.workspace_layout_profiles = {}
        self._active_workspace_layout_profile = "tabs"
        self._layout_profile_ready = True
