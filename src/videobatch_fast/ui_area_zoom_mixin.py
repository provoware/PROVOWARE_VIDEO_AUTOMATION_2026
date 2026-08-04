from __future__ import annotations

from tkinter import TclError, ttk
from typing import Any

from .text_resources import text


AREA_KEYS = ("start", "media", "preview", "modes", "production", "help")


class UiAreaZoomMixin:
    """Independent zoom controls for the large top-level work areas."""

    def _initialize_area_zoom(self) -> None:
        raw = self.config.get("area_zoom", {})
        source = raw if isinstance(raw, dict) else {}
        self.area_zoom: dict[str, int] = {}
        self.area_roots: dict[str, Any] = {}
        self.area_zoom_labels: dict[str, ttk.Label] = {}
        for key in AREA_KEYS:
            try:
                value = int(source.get(key, 100))
            except (TypeError, ValueError):
                value = 100
            self.area_zoom[key] = min(180, max(70, value))
        self.root.bind_all("<Control-MouseWheel>", self._on_ctrl_mousewheel, add="+")
        self.root.bind_all("<Control-Button-4>", lambda event: self._zoom_from_pointer(event, 10), add="+")
        self.root.bind_all("<Control-Button-5>", lambda event: self._zoom_from_pointer(event, -10), add="+")

    def _area_header(self, parent, area: str, title: str, subtitle: str = ""):
        wrapper = ttk.Frame(parent, style="Header.TFrame", padding=(10, 7))
        wrapper.pack(fill="x", pady=(0, 8))
        labels = ttk.Frame(wrapper, style="Header.TFrame")
        labels.pack(side="left", fill="x", expand=True)
        ttk.Label(labels, text=title, style="Section.TLabel").pack(anchor="w")
        if subtitle:
            ttk.Label(labels, text=subtitle, style="Hint.TLabel", wraplength=760).pack(anchor="w")
        controls = ttk.Frame(wrapper, style="Header.TFrame")
        controls.pack(side="right")
        ttk.Label(controls, text=text("ui.area_zoom.label", "Bereichszoom"), style="Hint.TLabel").pack(side="left", padx=(0, 6))
        ttk.Button(controls, text=text("ui.symbol.minus"), width=3, command=lambda: self._change_area_zoom(area, -10)).pack(side="left")
        label = ttk.Label(controls, text=f"{self.area_zoom.get(area, 100)} %", width=7, anchor="center")
        label.pack(side="left", padx=4)
        self.area_zoom_labels[area] = label
        ttk.Button(controls, text=text("ui.symbol.plus"), width=3, command=lambda: self._change_area_zoom(area, 10)).pack(side="left")
        ttk.Button(controls, text=text("ui.area_zoom.reset", "100 %"), command=lambda: self._set_area_zoom(area, 100)).pack(side="left", padx=(6, 0))
        return wrapper

    def _register_area(self, area: str, root) -> None:
        self.area_roots[area] = root
        self.root.after_idle(lambda key=area: self._apply_area_zoom(key))

    def _on_ctrl_mousewheel(self, event):
        delta = 10 if getattr(event, "delta", 0) > 0 else -10
        return self._zoom_from_pointer(event, delta)

    def _zoom_from_pointer(self, event, delta: int):
        area = self._area_for_widget(getattr(event, "widget", None)) or self._selected_area()
        if area:
            self._change_area_zoom(area, delta)
            self.guidance_text.set(
                text("ui.area_zoom.mouse_feedback", "Bereich {area}: {zoom} %", area=area.title(), zoom=self.area_zoom[area])
            )
            return "break"
        self._set_global_zoom(self.global_font_scale.get() + delta)
        return "break"

    def _selected_area(self) -> str | None:
        notebook = getattr(self, "main_notebook", None)
        if notebook is None:
            return None
        try:
            index = int(notebook.index(notebook.select()))
        except Exception:
            return None
        return {0: "start", 1: "media", 2: "preview", 3: "modes", 4: "production", 5: "help"}.get(index)

    def _area_for_widget(self, widget) -> str | None:
        current = widget
        while current is not None:
            for area, root in self.area_roots.items():
                if current is root:
                    return area
            try:
                parent_name = current.winfo_parent()
                current = current.nametowidget(parent_name) if parent_name else None
            except Exception:
                return None
        return None

    def _change_area_zoom(self, area: str, delta: int) -> None:
        self._set_area_zoom(area, self.area_zoom.get(area, 100) + delta)

    def _set_area_zoom(self, area: str, value: int) -> None:
        self.area_zoom[area] = min(180, max(70, int(value)))
        label = self.area_zoom_labels.get(area)
        if label:
            label.configure(text=f"{self.area_zoom[area]} %")
        self._apply_area_zoom(area)
        if hasattr(self, "_save_settings"):
            self.root.after_idle(self._save_settings)

    def _apply_area_zoom(self, area: str) -> None:
        root = self.area_roots.get(area)
        if root is None:
            return
        percent = self.area_zoom.get(area, 100)
        global_percent = int(self.config.get("font_scale", 100) or 100)
        size = max(9, min(28, round(11 * global_percent / 100 * percent / 100)))
        bold_size = max(size, min(30, size + 1))
        normal_font = ("DejaVu Sans", size)
        bold_font = ("DejaVu Sans", bold_size, "bold")
        self._apply_font_recursive(root, normal_font, bold_font, area, percent)
        grid = getattr(self, "workflow_grids", {}).get(area) if hasattr(self, "workflow_grids") else None
        if grid is not None:
            self.root.after_idle(grid.refresh)

    def _apply_font_recursive(self, widget, normal_font, bold_font, area: str, percent: int) -> None:
        widget_class = widget.winfo_class()
        try:
            if widget_class == "Treeview":
                style_name = f"Area{area.title()}.Treeview"
                style = ttk.Style(self.root)
                style.configure(style_name, font=normal_font, rowheight=max(30, round(36 * percent / 100)))
                style.configure(style_name + ".Heading", font=bold_font, padding=(8, max(7, round(9 * percent / 100))))
                widget.configure(style=style_name)
            elif widget_class in {"Listbox", "Text", "Entry", "Label", "Button", "Checkbutton", "Radiobutton"}:
                widget.configure(font=normal_font)
            elif widget_class in {"TButton", "TLabel", "TEntry", "TCombobox", "TCheckbutton", "TRadiobutton"}:
                base_style = str(widget.cget("style") or widget_class)
                derived = f"Area{area.title()}.{base_style}"
                font = bold_font if any(token in base_style for token in ("Title", "Section", "Status", "Recommended", "Accent", "QuickMode", "Choice")) else normal_font
                ttk.Style(self.root).configure(derived, font=font)
                widget.configure(style=derived)
        except (TclError, TypeError):
            pass
        for child in widget.winfo_children():
            self._apply_font_recursive(child, normal_font, bold_font, area, percent)

    def _reset_all_area_zoom(self) -> None:
        for area in AREA_KEYS:
            self.area_zoom[area] = 100
            if area in self.area_zoom_labels:
                self.area_zoom_labels[area].configure(text=text("ui.area_zoom.reset"))
            self._apply_area_zoom(area)
        if hasattr(self, "_save_settings"):
            self._save_settings()
