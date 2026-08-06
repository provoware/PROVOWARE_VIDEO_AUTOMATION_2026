from __future__ import annotations

from .window_geometry import normalize_window_geometry, safe_minimum_window_size


class CanonicalWindowMixin:
    """Apply screen-bounded geometry before the canonical shell is constructed."""

    def _build_ui(self) -> None:
        screen_width = max(1, int(self.root.winfo_screenwidth()))
        screen_height = max(1, int(self.root.winfo_screenheight()))
        minimum_width, minimum_height = safe_minimum_window_size(
            screen_width,
            screen_height,
        )
        geometry = normalize_window_geometry(
            str(self.config.get("window_geometry", "1500x920")),
            screen_width,
            screen_height,
        )
        self.root.minsize(minimum_width, minimum_height)
        self.root.geometry(geometry.as_tk())
        self.config["window_geometry"] = geometry.as_tk()
        super()._build_ui()
