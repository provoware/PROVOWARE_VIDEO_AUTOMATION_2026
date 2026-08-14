from __future__ import annotations

import math
from pathlib import Path
from tkinter import Canvas, PhotoImage, ttk
from typing import Callable, Iterable

from .incremental_directory import DirectoryRecord
from .probe import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS
from .theme import COLORS, best_text_color
from .ui_components import Tooltip

SelectionCallback = Callable[[tuple[Path, ...], Path | None], None]
ActivateCallback = Callable[[Path], None]
ThumbnailRequest = Callable[[Path], None]


def compact_filename(name: str, limit: int = 18) -> tuple[str, bool]:
    """Shorten long names without hiding a useful file extension."""
    if len(name) <= limit:
        return name, False
    suffix = Path(name).suffix
    stem_limit = limit - len(suffix) - 1
    compact = f"{Path(name).stem[:stem_limit]}…{suffix}" if stem_limit > 2 else f"{name[: limit - 1]}…"
    return compact, True


class VirtualThumbnailGrid:
    """Virtualized thumbnail grid that only draws visible tiles.

    The grid deliberately uses one Canvas instead of thousands of Tk widgets.
    This keeps large folders responsive and makes selection independent from
    background preview generation.
    """

    def __init__(
        self,
        parent,
        *,
        on_selection: SelectionCallback,
        on_activate: ActivateCallback,
        request_thumbnail: ThumbnailRequest,
        audio: bool,
    ) -> None:
        self.frame = ttk.Frame(parent)
        self.canvas = Canvas(
            self.frame,
            background=COLORS["panel"],
            highlightthickness=1,
            highlightbackground=COLORS["border_subtle"],
            highlightcolor=COLORS["accent2"],
            takefocus=True,
        )
        self.scrollbar = ttk.Scrollbar(self.frame, orient="vertical", command=self._yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.frame.rowconfigure(0, weight=1)
        self.frame.columnconfigure(0, weight=1)

        self.on_selection = on_selection
        self.on_activate = on_activate
        self.request_thumbnail = request_thumbnail
        self.audio = audio
        self.records: list[DirectoryRecord] = []
        self.selected: set[Path] = set()
        self.collected: set[Path] = set()
        self.focus_path: Path | None = None
        self.anchor_index: int | None = None
        self.photos: dict[Path, PhotoImage] = {}
        self.pending: set[Path] = set()
        self.failed: set[Path] = set()
        self.max_photo_cache = 256
        self.tile_width = 176
        self.tile_height = 176
        self.padding = 10
        self.columns = 1
        self._redraw_job: str | None = None
        self._hover_path: Path | None = None
        self.name_tooltip = Tooltip(self.canvas, "")

        self.canvas.bind("<Configure>", self._schedule_redraw)
        self.canvas.bind("<Button-1>", self._click)
        self.canvas.bind("<Double-1>", self._double_click)
        self.canvas.bind("<MouseWheel>", self._wheel)
        self.canvas.bind("<Button-4>", self._wheel)
        self.canvas.bind("<Button-5>", self._wheel)
        self.canvas.bind("<Motion>", self._hover)
        self.canvas.bind("<Leave>", self._leave, add=True)
        self.canvas.bind("<FocusIn>", self._focus_tooltip, add=True)
        self.canvas.bind("<KeyPress-space>", self._toggle_focus)
        self.canvas.bind("<KeyPress-Return>", self._activate_focus)

    def pack(self, **kwargs) -> None:
        self.frame.pack(**kwargs)

    def grid(self, **kwargs) -> None:
        self.frame.grid(**kwargs)

    def tkraise(self) -> None:
        self.frame.tkraise()

    def destroy(self) -> None:
        self.photos.clear()
        self.pending.clear()
        self.failed.clear()
        self.frame.destroy()

    def set_records(self, records: Iterable[DirectoryRecord], *, collected: Iterable[Path] = ()) -> None:
        self.records = list(records)
        self.collected = set(collected)
        valid = {record.path for record in self.records}
        self.selected.intersection_update(valid)
        self.pending.intersection_update(valid)
        self.failed.intersection_update(valid)
        self.photos = {path: photo for path, photo in self.photos.items() if path in valid}
        if self.focus_path not in valid:
            self.focus_path = None
        self._update_scrollregion()
        self._schedule_redraw()

    def set_collected(self, paths: Iterable[Path]) -> None:
        self.collected = set(paths)
        self._schedule_redraw()

    def clear_selection(self) -> None:
        self.selected.clear()
        self.focus_path = None
        self.anchor_index = None
        self._schedule_redraw()
        self.on_selection((), None)

    def selected_paths(self) -> tuple[Path, ...]:
        order = {record.path: index for index, record in enumerate(self.records)}
        return tuple(sorted(self.selected, key=lambda path: order.get(path, 10**9)))

    def install_thumbnail(self, path: Path, photo: PhotoImage | None) -> None:
        self.pending.discard(path)
        self.failed.discard(path)
        if photo is not None:
            self.photos.pop(path, None)
            self.photos[path] = photo
            while len(self.photos) > self.max_photo_cache:
                oldest = next(iter(self.photos))
                self.photos.pop(oldest, None)
        self._schedule_redraw()

    def mark_thumbnail_failed(self, path: Path) -> None:
        self.pending.discard(path)
        self.failed.add(path)
        self._schedule_redraw()

    def _update_scrollregion(self) -> None:
        width = max(1, self.canvas.winfo_width())
        self.columns = max(1, width // self.tile_width)
        rows = math.ceil(len(self.records) / self.columns) if self.records else 1
        self.canvas.configure(scrollregion=(0, 0, width, rows * self.tile_height + self.padding))

    def _schedule_redraw(self, _event=None) -> None:
        try:
            if self._redraw_job:
                self.canvas.after_cancel(self._redraw_job)
            self._redraw_job = self.canvas.after_idle(self._redraw)
        except Exception:
            self._redraw_job = None

    def _redraw(self) -> None:
        self._redraw_job = None
        if not self.canvas.winfo_exists():
            return
        self._update_scrollregion()
        self.canvas.delete("tile")
        if not self.records:
            self.canvas.create_text(
                24,
                24,
                anchor="nw",
                text="Keine passenden Dateien sichtbar.",
                fill=COLORS["muted"],
                tags=("tile",),
            )
            return

        top = self.canvas.canvasy(0)
        bottom = top + max(1, self.canvas.winfo_height())
        first_row = max(0, int(top // self.tile_height) - 1)
        last_row = min(math.ceil(len(self.records) / self.columns), int(bottom // self.tile_height) + 2)
        for row in range(first_row, last_row):
            for column in range(self.columns):
                index = row * self.columns + column
                if index >= len(self.records):
                    break
                self._draw_tile(index, row, column)

    def _draw_tile(self, index: int, row: int, column: int) -> None:
        record = self.records[index]
        path = record.path
        x1 = column * self.tile_width + self.padding
        y1 = row * self.tile_height + self.padding
        x2 = x1 + self.tile_width - self.padding * 2
        y2 = y1 + self.tile_height - self.padding
        selected = path in self.selected
        collected = path in self.collected
        fill = COLORS["selection"] if selected else COLORS["panel2"]
        outline = COLORS["success"] if collected else (COLORS["accent2"] if selected else COLORS["border_subtle"])
        text_color = best_text_color(fill)
        self.canvas.create_rectangle(
            x1,
            y1,
            x2,
            y2,
            fill=fill,
            outline=outline,
            width=3 if selected or collected else 1,
            tags=("tile",),
        )

        preview_y = y1 + 58
        photo = self.photos.get(path)
        if photo is not None:
            self.canvas.create_image((x1 + x2) / 2, preview_y, image=photo, anchor="center", tags=("tile",))
        else:
            badge, badge_fill = self._badge(record)
            self.canvas.create_rectangle(
                x1 + 42,
                y1 + 18,
                x2 - 42,
                y1 + 92,
                fill=badge_fill,
                outline=COLORS["border"],
                width=1,
                tags=("tile",),
            )
            self.canvas.create_text(
                (x1 + x2) / 2,
                y1 + 55,
                text=badge,
                fill=best_text_color(badge_fill),
                font=("DejaVu Sans", 12, "bold"),
                tags=("tile",),
            )
            if self._supports_thumbnail(record) and path not in self.pending and path not in self.failed:
                self.pending.add(path)
                self.request_thumbnail(path)

        name, _truncated = compact_filename(path.name)
        self.canvas.create_text(
            (x1 + x2) / 2,
            y1 + 116,
            text=name,
            width=self.tile_width - 30,
            justify="center",
            fill=text_color,
            font=("DejaVu Sans", 11, "bold"),
            tags=("tile",),
        )
        detail = "Ordner" if record.is_dir else self._format_size(record.size)
        if collected:
            detail += " · übernommen"
        self.canvas.create_text(
            (x1 + x2) / 2,
            y1 + 148,
            text=detail,
            width=self.tile_width - 24,
            justify="center",
            fill=text_color,
            font=("DejaVu Sans", 9),
            tags=("tile",),
        )

    def _badge(self, record: DirectoryRecord) -> tuple[str, str]:
        if record.is_dir:
            return "ORDNER", COLORS["tile_gold"]
        suffix = record.path.suffix.lower()
        if suffix in IMAGE_EXTENSIONS:
            return "BILD", COLORS["tile_magenta"]
        if suffix in VIDEO_EXTENSIONS:
            return "VIDEO", COLORS["tile_blue"]
        return "AUDIO", COLORS["tile_green"]

    def _supports_thumbnail(self, record: DirectoryRecord) -> bool:
        return not self.audio and not record.is_dir and record.path.suffix.lower() in IMAGE_EXTENSIONS | VIDEO_EXTENSIONS

    def _index_at(self, event) -> int | None:
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        column = int(x // self.tile_width)
        row = int(y // self.tile_height)
        index = row * self.columns + column
        return index if 0 <= index < len(self.records) else None

    def _click(self, event) -> str:
        index = self._index_at(event)
        self.canvas.focus_set()
        if index is None:
            self.clear_selection()
            return "break"
        path = self.records[index].path
        ctrl = bool(event.state & 0x4)
        shift = bool(event.state & 0x1)
        if shift and self.anchor_index is not None:
            start, end = sorted((self.anchor_index, index))
            if not ctrl:
                self.selected.clear()
            self.selected.update(record.path for record in self.records[start : end + 1])
        elif ctrl:
            if path in self.selected:
                self.selected.remove(path)
            else:
                self.selected.add(path)
            self.anchor_index = index
        else:
            self.selected = {path}
            self.anchor_index = index
        self.focus_path = path
        self._schedule_redraw()
        self.on_selection(self.selected_paths(), self.focus_path)
        return "break"

    def _hover(self, event) -> None:
        index = self._index_at(event)
        path = self.records[index].path if index is not None else None
        name, truncated = compact_filename(path.name) if path else ("", False)
        hover_path = path if truncated else None
        if hover_path == self._hover_path:
            return
        self._hover_path = hover_path
        self.name_tooltip.update_message(path.name if hover_path else "")

    def _focus_tooltip(self, _event=None) -> None:
        if self._hover_path is not None:
            return
        path = self.focus_path
        _name, truncated = compact_filename(path.name) if path else ("", False)
        self.name_tooltip.update_message(path.name if path and truncated else "")

    def _leave(self, _event=None) -> None:
        self._hover_path = None
        self.name_tooltip.update_message("")

    def _double_click(self, event) -> str:
        index = self._index_at(event)
        if index is not None:
            path = self.records[index].path
            self.focus_path = path
            self.on_activate(path)
        return "break"

    def _toggle_focus(self, _event=None) -> str:
        if self.focus_path is None:
            return "break"
        if self.focus_path in self.selected:
            self.selected.remove(self.focus_path)
        else:
            self.selected.add(self.focus_path)
        self._schedule_redraw()
        self.on_selection(self.selected_paths(), self.focus_path)
        return "break"

    def _activate_focus(self, _event=None) -> str:
        if self.focus_path is not None:
            self.on_activate(self.focus_path)
        return "break"

    def _wheel(self, event) -> str:
        if getattr(event, "num", None) == 4:
            delta = -3
        elif getattr(event, "num", None) == 5:
            delta = 3
        else:
            delta = -int(getattr(event, "delta", 0) / 120) * 3
        if delta:
            self.canvas.yview_scroll(delta, "units")
            self._schedule_redraw()
        return "break"

    def _yview(self, *args) -> None:
        self.canvas.yview(*args)
        self._schedule_redraw()

    @staticmethod
    def _format_size(value: int) -> str:
        number = float(value)
        for unit in ("B", "KB", "MB", "GB"):
            if number < 1024 or unit == "GB":
                return f"{number:.1f} {unit}"
            number /= 1024
        return f"{value} B"
