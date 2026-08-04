from __future__ import annotations

from pathlib import Path
from tkinter import Canvas, PhotoImage, ttk
from collections.abc import Callable

from PIL import Image, ImageDraw, ImageOps, ImageTk

from .audio_waveform import WaveformAnalysis
from .theme import COLORS
from .text_resources import text


class ThumbnailOrderStrip(ttk.Frame):
    """Horizontal thumbnail strip with mouse-driven reordering and anchors."""

    def __init__(
        self,
        parent,
        *,
        on_move: Callable[[int, int], None],
        on_select: Callable[[Path | None], None] | None = None,
    ) -> None:
        super().__init__(parent, style="Card.TFrame")
        self._on_move = on_move
        self._on_select = on_select
        self._paths: list[Path] = []
        self._start: Path | None = None
        self._end: Path | None = None
        self._photos: list[PhotoImage] = []
        self._selected_index: int | None = None
        self._drag_index: int | None = None
        self._drag_target: int | None = None
        self._item_width = 152
        self._item_height = 132

        self.canvas = Canvas(
            self,
            height=self._item_height + 12,
            background=COLORS["panel"],
            highlightthickness=1,
            highlightbackground=COLORS["border_subtle"],
            cursor="hand2",
        )
        scrollbar = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(xscrollcommand=scrollbar.set)
        self.canvas.pack(fill="both", expand=True)
        scrollbar.pack(fill="x")
        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._motion)
        self.canvas.bind("<ButtonRelease-1>", self._release)
        self.canvas.bind("<Configure>", lambda _event: self._draw())
        self.canvas.bind("<MouseWheel>", self._horizontal_wheel)
        self.canvas.bind("<Button-4>", lambda _event: self.canvas.xview_scroll(-2, "units"))
        self.canvas.bind("<Button-5>", lambda _event: self.canvas.xview_scroll(2, "units"))

    @property
    def selected_path(self) -> Path | None:
        if self._selected_index is None or self._selected_index >= len(self._paths):
            return None
        return self._paths[self._selected_index]

    def set_items(self, paths: list[Path], *, start: Path | None = None, end: Path | None = None) -> None:
        selected = self.selected_path
        self._paths = list(paths)
        self._start = start if start in self._paths else None
        self._end = end if end in self._paths else None
        self._selected_index = self._paths.index(selected) if selected in self._paths else (0 if self._paths else None)
        self._draw()

    def _thumbnail(self, path: Path) -> PhotoImage:
        width, height = 126, 84
        try:
            with Image.open(path) as image:
                image = ImageOps.exif_transpose(image).convert("RGB")
                image.thumbnail((width, height), Image.Resampling.LANCZOS)
                canvas = Image.new("RGB", (width, height), "#09131d")
                canvas.paste(image, ((width - image.width) // 2, (height - image.height) // 2))
        except (OSError, ValueError):
            canvas = Image.new("RGB", (width, height), "#28131f")
            draw = ImageDraw.Draw(canvas)
            draw.rectangle((5, 5, width - 6, height - 6), outline="#ff5c7c", width=3)
            draw.line((12, 12, width - 12, height - 12), fill="#ff5c7c", width=3)
            draw.line((width - 12, 12, 12, height - 12), fill="#ff5c7c", width=3)
        return ImageTk.PhotoImage(canvas)

    def _draw(self) -> None:
        self.canvas.delete("all")
        self._photos = []
        if not self._paths:
            self.canvas.create_text(
                18,
                28,
                anchor="nw",
                text=text("ui.slideshow.editor.empty"),
                fill=COLORS["muted"],
                font=("DejaVu Sans", 12),
            )
            self.canvas.configure(scrollregion=(0, 0, max(600, self.canvas.winfo_width()), self._item_height))
            return
        for index, path in enumerate(self._paths):
            left = 10 + index * self._item_width
            top = 8
            selected = index == self._selected_index
            border = COLORS["accent2"] if selected else COLORS["border"]
            if path == self._start:
                border = COLORS["success"]
            elif path == self._end:
                border = COLORS["warning"]
            self.canvas.create_rectangle(
                left,
                top,
                left + self._item_width - 10,
                top + self._item_height,
                fill=COLORS["panel2"],
                outline=border,
                width=4 if selected or path in {self._start, self._end} else 2,
                tags=(f"item:{index}",),
            )
            photo = self._thumbnail(path)
            self._photos.append(photo)
            self.canvas.create_image(left + 8, top + 8, image=photo, anchor="nw", tags=(f"item:{index}",))
            name = path.name if len(path.name) <= 21 else path.name[:18] + "…"
            self.canvas.create_text(
                left + 8,
                top + 98,
                anchor="nw",
                text=f"{index + 1}. {name}",
                fill=COLORS["text"],
                font=("DejaVu Sans", 9, "bold"),
                tags=(f"item:{index}",),
            )
            badges: list[str] = []
            if path == self._start:
                badges.append("START")
            if path == self._end:
                badges.append("ENDE")
            if badges:
                self.canvas.create_text(
                    left + self._item_width - 20,
                    top + 10,
                    anchor="ne",
                    text=" · ".join(badges),
                    fill=COLORS["accent_text"],
                    font=("DejaVu Sans", 8, "bold"),
                    tags=(f"item:{index}",),
                )
        if self._drag_target is not None:
            x = 10 + self._drag_target * self._item_width
            self.canvas.create_line(x, 4, x, self._item_height + 10, fill=COLORS["accent2"], width=4, dash=(5, 3))
        width = 20 + len(self._paths) * self._item_width
        self.canvas.configure(scrollregion=(0, 0, max(width, self.canvas.winfo_width()), self._item_height + 14))

    def _index_at(self, event) -> int | None:
        x = self.canvas.canvasx(event.x)
        index = int(max(0, x - 10) // self._item_width)
        return index if 0 <= index < len(self._paths) else None

    def _press(self, event) -> None:
        index = self._index_at(event)
        self._selected_index = index
        self._drag_index = index
        self._drag_target = index
        self._draw()
        if self._on_select is not None:
            self._on_select(self.selected_path)

    def _motion(self, event) -> None:
        if self._drag_index is None:
            return
        x = self.canvas.canvasx(event.x)
        target = round(max(0, x - 10) / self._item_width)
        self._drag_target = max(0, min(len(self._paths) - 1, target))
        self._draw()

    def _release(self, _event) -> None:
        source = self._drag_index
        target = self._drag_target
        self._drag_index = None
        self._drag_target = None
        if source is not None and target is not None and source != target:
            self._on_move(source, target)
        else:
            self._draw()

    def _horizontal_wheel(self, event) -> str:
        delta = -1 if event.delta > 0 else 1
        self.canvas.xview_scroll(delta * 3, "units")
        return "break"


class WaveformSceneView(ttk.Frame):
    def __init__(self, parent) -> None:
        super().__init__(parent, style="Card.TFrame")
        self.analysis: WaveformAnalysis | None = None
        self.canvas = Canvas(
            self,
            height=250,
            background=COLORS["preview"],
            highlightthickness=1,
            highlightbackground=COLORS["border"],
        )
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _event: self.redraw())

    def set_analysis(self, analysis: WaveformAnalysis | None) -> None:
        self.analysis = analysis
        self.redraw()

    def redraw(self) -> None:
        self.canvas.delete("all")
        width = max(320, self.canvas.winfo_width())
        height = max(170, self.canvas.winfo_height())
        middle = height * 0.58
        self.canvas.create_line(0, middle, width, middle, fill=COLORS["border_subtle"])
        analysis = self.analysis
        if analysis is None or not analysis.peaks:
            self.canvas.create_text(
                18,
                18,
                anchor="nw",
                text=text("ui.slideshow.waveform.empty"),
                fill=COLORS["muted"],
                font=("DejaVu Sans", 11),
            )
            return
        points = analysis.peaks
        step = width / max(1, len(points) - 1)
        coordinates: list[float] = []
        amplitude = height * 0.35
        for index, value in enumerate(points):
            x = index * step
            y = middle - max(1.0, value * amplitude)
            coordinates.extend((x, y))
        if len(coordinates) >= 4:
            self.canvas.create_line(*coordinates, fill=COLORS["accent2"], width=2, smooth=True)
            mirrored: list[float] = []
            for index, value in enumerate(points):
                mirrored.extend((index * step, middle + max(1.0, value * amplitude * 0.55)))
            self.canvas.create_line(*mirrored, fill=COLORS["active"], width=1, smooth=True)

        marker_colors = {
            "intro": COLORS["success"],
            "beat": COLORS["accent2"],
            "quiet": COLORS["warning"],
            "drop": COLORS["danger"],
            "outro": COLORS["accent"],
        }
        for row, marker in enumerate(analysis.markers):
            x = width * marker.time_seconds / max(analysis.duration, 0.001)
            color = marker_colors.get(marker.kind, COLORS["text"])
            self.canvas.create_line(x, 12, x, height - 18, fill=color, width=2, dash=(5, 3))
            minutes, seconds = divmod(round(marker.time_seconds), 60)
            anchor = "w" if x < width * 0.78 else "e"
            offset = 5 if anchor == "w" else -5
            self.canvas.create_text(
                x + offset,
                14 + (row % 2) * 20,
                anchor=f"n{anchor}",
                text=f"{marker.label} · {minutes}:{seconds:02d}",
                fill=color,
                font=("DejaVu Sans", 9, "bold"),
            )
