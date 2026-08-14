from __future__ import annotations

import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tkinter import END, PhotoImage, StringVar, TclError, Toplevel, ttk

from .incremental_directory import DirectoryRecord, scan_directory_batches
from .media_dialog_layout import build_media_actions
from .media_dialog_runtime import MediaDialogRuntimeMixin
from .media_dialog_support import human_size, media_filter_matches, safe_media_directory, sort_directory_records
from .preview_service import build_preview
from .probe import AUDIO_EXTENSIONS, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS, probe_media
from .thumbnail_grid import VirtualThumbnailGrid


def preview_candidate(selection: tuple[str, ...], focus: str) -> str | None:
    """Choose the last actively focused row instead of the first selected row."""
    if focus and focus in selection:
        return focus
    return selection[-1] if selection else None


class MediaImportDialog(MediaDialogRuntimeMixin):
    """Thread-safe media chooser with list and virtual thumbnail views."""

    KEEP_OPEN_LABEL = "Auswahl übernehmen + im Ordner bleiben"

    def __init__(self, parent, *, audio: bool, initial_dir: Path, modal: bool = True) -> None:
        self.parent = parent
        self.audio = audio
        self.allowed = AUDIO_EXTENSIONS if audio else IMAGE_EXTENSIONS | VIDEO_EXTENSIONS
        self.current_dir = safe_media_directory(initial_dir)
        self.result: tuple[Path, ...] = ()
        self.collected: list[Path] = []
        self.preview_photo: PhotoImage | None = None
        self.preview_generation = 0
        self.sort_key = "name"
        self.sort_reverse = False
        self._records: list[DirectoryRecord] = []
        self._visible_records: list[DirectoryRecord] = []
        self._scan_generation = 0
        self._scan_cancel = threading.Event()
        self._preview_busy = threading.Event()
        self._preview_lock = threading.Lock()
        self._preview_workers = 0
        self._scan_complete = False
        self._closed = False
        self._poll_job: str | None = None
        self._selection_job: str | None = None
        self._render_job: str | None = None
        self._preview_future = None
        self._last_clicked_path: Path | None = None
        self._last_preview_path: Path | None = None
        self._events: queue.Queue[tuple] = queue.Queue(maxsize=256)
        self._executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="videobatch-media")

        window = Toplevel(parent)
        self.window = window
        window.title("Audio auswählen" if audio else "Bilder und Videos auswählen")
        window.geometry("1220x760")
        window.minsize(1060, 700)
        window.transient(parent)
        window.protocol("WM_DELETE_WINDOW", self._cancel)

        self.path_value = StringVar(window, value=str(self.current_dir))
        self.filter_value = StringVar(window, value="")
        self.type_filter_value = StringVar(window, value="Alle Dateien")
        self.status_value = StringVar(window, value="Ordner wird geladen …")
        self.collection_value = StringVar(window, value="Noch keine Dateien übernommen")
        self.preview_value = StringVar(window, value="Datei auswählen")
        self.scan_value = StringVar(window, value="Scan wird vorbereitet …")
        self.view_mode = StringVar(window, value="list" if audio else "icons")
        self.sort_value = StringVar(window, value="Name")

        outer = ttk.Frame(window, padding=14, style="MediaDialog.TFrame")
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(2, weight=1)
        self._build_header(outer)
        self._build_navigation(outer)
        self._build_content(outer)
        build_media_actions(self, outer)
        self.filter_value.trace_add("write", lambda *_args: self._schedule_render())
        self.type_filter_value.trace_add("write", lambda *_args: self._schedule_render())
        self._start_event_pump()
        self._load_directory()
        if modal:
            window.grab_set()
            window.wait_window()

    def _build_header(self, parent) -> None:
        header = ttk.Frame(parent, padding=(12, 10), style="MediaToolbar.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        title = "Audiodateien auswählen" if self.audio else "Bilder und Videos auswählen"
        ttk.Label(header, text=title, style="HeaderTitle.TLabel").pack(side="left")
        ttk.Label(
            header,
            text="Mehrfachauswahl · Vorschau · Sammeln ohne Schließen",
            style="HeaderHint.TLabel",
        ).pack(side="left", padx=(14, 0))
        modes = ttk.Frame(header, style="Toolbar.TFrame")
        modes.pack(side="right")
        self.list_mode_button = ttk.Button(modes, text="☷ Liste", command=lambda: self._set_view_mode("list"))
        self.list_mode_button.pack(side="left")
        self.icon_mode_button = ttk.Button(modes, text="▦ Symbole", command=lambda: self._set_view_mode("icons"))
        self.icon_mode_button.pack(side="left", padx=(6, 0))
        self._refresh_view_buttons()

    def _build_navigation(self, parent) -> None:
        shell = ttk.Frame(parent, padding=10, style="MediaToolbar.TFrame")
        shell.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        row = ttk.Frame(shell, style="Toolbar.TFrame")
        row.pack(fill="x", pady=(0, 7))
        ttk.Button(row, text="← Hoch", command=self._go_up).pack(side="left")
        ttk.Button(row, text="Home", command=lambda: self._navigate(Path.home())).pack(side="left", padx=5)
        ttk.Button(row, text="Downloads", command=lambda: self._navigate(Path.home() / "Downloads")).pack(side="left")
        entry = ttk.Entry(row, textvariable=self.path_value)
        entry.pack(side="left", fill="x", expand=True, padx=9)
        entry.bind("<Return>", lambda _event: self._navigate(Path(self.path_value.get())))
        ttk.Button(row, text="Ordner laden", style="Accent.TButton", command=lambda: self._navigate(Path(self.path_value.get()))).pack(side="right")
        tools = ttk.Frame(shell, style="Toolbar.TFrame")
        tools.pack(fill="x")
        self.scan_stop_button = ttk.Button(tools, text="Stoppen", width=8, command=self._stop_scan)
        self.scan_stop_button.pack(side="right")
        ttk.Label(tools, text="Dateien finden", style="HeaderHint.TLabel").pack(side="left")
        ttk.Entry(tools, textvariable=self.filter_value).pack(side="left", fill="x", expand=True, padx=(7, 9))
        categories = ("Alle Dateien", "Audio") if self.audio else ("Alle Dateien", "Bilder", "Videos")
        type_combo = ttk.Combobox(tools, textvariable=self.type_filter_value, values=categories, state="readonly", width=12)
        type_combo.pack(side="left", padx=(0, 9))
        ttk.Label(tools, text="Sortieren", style="HeaderHint.TLabel").pack(side="left", padx=(0, 6))
        sort_combo = ttk.Combobox(tools, textvariable=self.sort_value, values=("Name", "Größe", "Geändert", "Art"), state="readonly", width=11)
        sort_combo.pack(side="left", padx=(0, 5))
        sort_combo.bind("<<ComboboxSelected>>", self._sort_from_combo)
        self.sort_direction_button = ttk.Button(tools, text="↑", width=3, command=self._toggle_sort_direction)
        self.sort_direction_button.pack(side="left", padx=(0, 8))
        self.scan_progress = ttk.Progressbar(tools, mode="indeterminate", length=52)
        self.scan_progress.pack(side="left", padx=(0, 8))
        ttk.Label(tools, textvariable=self.scan_value, style="HeaderHint.TLabel").pack(side="left")

    def _build_content(self, parent) -> None:
        panes = ttk.Panedwindow(parent, orient="horizontal")
        panes.grid(row=2, column=0, sticky="nsew")

        left = ttk.Frame(panes, padding=10, style="MediaCard.TFrame")
        right = ttk.Frame(panes, padding=12, style="MediaPreview.TFrame")
        panes.add(left, weight=7)
        panes.add(right, weight=3)

        self.view_stack = ttk.Frame(left, style="MediaCard.TFrame")
        self.view_stack.pack(fill="both", expand=True)
        self.view_stack.rowconfigure(0, weight=1)
        self.view_stack.columnconfigure(0, weight=1)

        list_frame = ttk.Frame(self.view_stack, style="MediaCard.TFrame")
        list_frame.grid(row=0, column=0, sticky="nsew")
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)
        self.tree = ttk.Treeview(
            list_frame,
            columns=("kind", "name", "size", "modified", "state"),
            show="headings",
            selectmode="extended",
            height=18,
        )
        headings = (
            ("kind", "Art", 90),
            ("name", "Name", 360),
            ("size", "Größe", 110),
            ("modified", "Geändert", 155),
            ("state", "Auswahlstatus", 130),
        )
        for key, title, width in headings:
            self.tree.heading(key, text=title, command=lambda current=key: self._change_sort(current))
            self.tree.column(key, width=width, minwidth=70, stretch=key == "name")
        yscroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        xscroll = ttk.Scrollbar(list_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        self.tree.bind("<ButtonPress-1>", self._tree_pointer_press, add="+")
        self.tree.bind("<Double-1>", self._tree_double_click)
        self.tree.bind("<<TreeviewSelect>>", self._tree_selection_event)
        self.tree.bind("<KeyRelease-Up>", self._tree_selection_event, add="+")
        self.tree.bind("<KeyRelease-Down>", self._tree_selection_event, add="+")

        icon_frame = ttk.Frame(self.view_stack, style="MediaCard.TFrame")
        icon_frame.grid(row=0, column=0, sticky="nsew")
        self.icon_grid = VirtualThumbnailGrid(
            icon_frame,
            on_selection=self._icon_selection_changed,
            on_activate=self._activate_path,
            request_thumbnail=self._request_thumbnail,
            audio=self.audio,
        )
        self.icon_grid.pack(fill="both", expand=True)
        self.list_frame = list_frame
        self.icon_frame = icon_frame

        ttk.Label(left, textvariable=self.status_value, style="Hint.TLabel").pack(fill="x", pady=(7, 0))
        ttk.Label(left, textvariable=self.collection_value, style="Success.TLabel").pack(fill="x", pady=(3, 0))

        ttk.Label(right, text="Live-Vorschau", style="MediaPreview.TLabel").pack(anchor="w")
        self.preview = ttk.Label(
            right,
            textvariable=self.preview_value,
            width=28,
            anchor="center",
            justify="center",
            style="MediaPreview.TLabel",
        )
        self.preview.pack(fill="both", expand=True, pady=8)
        self.meta = ttk.Label(right, text="", justify="left", wraplength=470, style="MediaPreview.TLabel")
        self.meta.pack(fill="x")
        self._set_view_mode(self.view_mode.get())

    def _set_view_mode(self, mode: str) -> None:
        selected = mode if mode in {"list", "icons"} else "list"
        previous = self.view_mode.get()
        if hasattr(self, "list_frame") and previous != selected:
            if previous == "list":
                paths = {Path(item) for item in self.tree.selection()}
                self.icon_grid.selected = paths
                focus = self.tree.focus()
                self.icon_grid.focus_path = Path(focus) if focus else None
            else:
                valid = [str(path) for path in self.icon_grid.selected_paths() if self.tree.exists(str(path))]
                self.tree.selection_set(valid)
                if self.icon_grid.focus_path and self.tree.exists(str(self.icon_grid.focus_path)):
                    self.tree.focus(str(self.icon_grid.focus_path))
        self.view_mode.set(selected)
        if not hasattr(self, "list_frame"):
            return
        if selected == "icons":
            self.icon_frame.tkraise()
        else:
            self.list_frame.tkraise()
        self._refresh_view_buttons()
        self._update_status()

    def _refresh_view_buttons(self) -> None:
        if not hasattr(self, "list_mode_button"):
            return
        self.list_mode_button.configure(style="MediaModeSelected.TButton" if self.view_mode.get() == "list" else "MediaMode.TButton")
        self.icon_mode_button.configure(style="MediaModeSelected.TButton" if self.view_mode.get() == "icons" else "MediaMode.TButton")

    def _navigate(self, path: Path) -> None:
        candidate = safe_media_directory(path)
        self.current_dir = candidate
        self.path_value.set(str(candidate))
        self._load_directory()

    def _go_up(self) -> None:
        self._navigate(self.current_dir.parent)

    def _stop_scan(self) -> None:
        self._scan_cancel.set()
        self.scan_value.set(f"Scan angehalten · {len(self._records)} Einträge gefunden")
        self.status_value.set("Scan gestoppt. Gefundene Dateien bleiben auswählbar.")
        self.scan_stop_button.configure(state="disabled")
        self.scan_progress.stop()

    def _load_directory(self) -> None:
        self._scan_cancel.set()
        self._scan_generation += 1
        generation = self._scan_generation
        self._scan_cancel = threading.Event()
        self._records = []
        self._visible_records = []
        self._scan_complete = False
        self.tree.delete(*self.tree.get_children())
        self.icon_grid.set_records(())
        self.preview.configure(image="")
        self.preview_photo = None
        self.preview_value.set("Datei auswählen")
        self.meta.configure(text="")
        self.status_value.set("Erste Dateien werden geladen …")
        self.scan_value.set("0 gefunden")
        self.scan_stop_button.configure(state="normal")
        self.scan_progress.start(12)

        directory = self.current_dir
        cancel = self._scan_cancel

        def worker() -> None:
            error = ""
            try:
                for batch in scan_directory_batches(
                    directory,
                    self.allowed,
                    cancel=cancel,
                    pause=self._preview_busy,
                    batch_size=128,
                ):
                    if cancel.is_set() or self._closed:
                        break
                    self._post_event(("scan_batch", generation, batch))
            except OSError as exc:
                error = str(exc)
            self._post_event(("scan_done", generation, error))

        self._submit(worker)

    def _apply_scan_batch(self, generation: int, batch: list[DirectoryRecord]) -> None:
        if generation != self._scan_generation or self._closed:
            return
        self._records.extend(batch)
        self.scan_value.set(f"{len(self._records)} gefunden · Scan läuft")
        self._schedule_render(60)

    def _finish_scan(self, generation: int, error: str) -> None:
        if generation != self._scan_generation or self._closed:
            return
        self._scan_complete = True
        self.scan_progress.stop()
        self.scan_stop_button.configure(state="disabled")
        self._render_records()
        if error:
            self.scan_value.set("Scan mit Einschränkung beendet")
            self.status_value.set(f"Ordner konnte nicht vollständig gelesen werden: {error}")
        elif self._scan_cancel.is_set():
            self.scan_value.set(f"angehalten · {len(self._records)} gefunden")
        else:
            self.scan_value.set(f"{len(self._records)} gefunden")

    def _sorted_records(self) -> list[DirectoryRecord]:
        return sort_directory_records(self._records, self.sort_key, self.sort_reverse)

    def _schedule_render(self, delay_ms: int = 20) -> None:
        if self._closed:
            return
        try:
            if self._render_job:
                self.window.after_cancel(self._render_job)
            self._render_job = self.window.after(delay_ms, self._run_scheduled_render)
        except TclError:
            self._render_job = None

    def _run_scheduled_render(self) -> None:
        self._render_job = None
        self._render_records()

    def _render_records(self) -> None:
        if self._closed or not hasattr(self, "tree"):
            return
        selected = set(self.tree.selection())
        self.tree.delete(*self.tree.get_children())
        filter_text = self.filter_value.get().strip().casefold()
        visible: list[DirectoryRecord] = []
        for record in self._sorted_records():
            if filter_text and filter_text not in record.path.name.casefold() and not record.is_dir:
                continue
            if not media_filter_matches(record, self.type_filter_value.get()):
                continue
            visible.append(record)
            self._insert_record(record)
        self._visible_records = visible
        valid_selected = [item for item in selected if self.tree.exists(item)]
        if valid_selected:
            self.tree.selection_set(valid_selected)
        self.icon_grid.set_records(visible, collected=self.collected)
        self._update_status()

    def _insert_record(self, record: DirectoryRecord) -> None:
        path = record.path
        iid = str(path)
        if self.tree.exists(iid):
            return
        kind = "Ordner" if record.is_dir else ("Audio" if self.audio else ("Bild" if path.suffix.lower() in IMAGE_EXTENSIONS else "Video"))
        size = "—" if record.is_dir else human_size(record.size)
        modified = time.strftime("%d.%m.%Y %H:%M", time.localtime(record.modified))
        state = "Übernommen" if path in self.collected else ""
        self.tree.insert("", END, iid=iid, values=(kind, path.name, size, modified, state))

    def _update_status(self) -> None:
        if not hasattr(self, "tree"):
            return
        current = len(self._selected_paths())
        visible_count = len(self._visible_records)
        scan_state = "Scan läuft" if not self._scan_complete and not self._scan_cancel.is_set() else "Scan beendet"
        view = "Symbolansicht" if self.view_mode.get() == "icons" else "Listenansicht"
        self.status_value.set(f"{visible_count} sichtbar · {current} markiert · {view} · {scan_state}")
        noun = "Audios" if self.audio else "Medien"
        self.collection_value.set(f"Übernommen: {len(self.collected)} {noun} · weitere Auswahlrunden möglich")

    def _change_sort(self, key: str) -> None:
        if self.sort_key == key:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_key = key
            self.sort_reverse = key in {"size", "modified"}
        labels = {"name": "Name", "size": "Größe", "modified": "Geändert", "kind": "Art"}
        self.sort_value.set(labels.get(key, "Name"))
        self._refresh_sort_direction()
        self._render_records()

    def _sort_from_combo(self, _event=None) -> None:
        keys = {"Name": "name", "Größe": "size", "Geändert": "modified", "Art": "kind"}
        key = keys.get(self.sort_value.get(), "name")
        if key != self.sort_key:
            self.sort_key = key
            self.sort_reverse = key in {"size", "modified"}
        self._refresh_sort_direction()
        self._render_records()

    def _toggle_sort_direction(self) -> None:
        self.sort_reverse = not self.sort_reverse
        self._refresh_sort_direction()
        self._render_records()

    def _refresh_sort_direction(self) -> None:
        if hasattr(self, "sort_direction_button"):
            self.sort_direction_button.configure(text="↓" if self.sort_reverse else "↑")

    def _selected_paths(self) -> list[Path]:
        if self.view_mode.get() == "icons":
            candidates = self.icon_grid.selected_paths()
        else:
            candidates = tuple(Path(item) for item in self.tree.selection())
        result: list[Path] = []
        for path in candidates:
            try:
                if path.is_file() and path.suffix.lower() in self.allowed:
                    result.append(path)
            except OSError:
                continue
        return result

    def _tree_pointer_press(self, event) -> None:
        iid = self.tree.identify_row(event.y)
        if iid:
            self.tree.focus(iid)
            self._last_clicked_path = Path(iid)

    def _tree_selection_event(self, _event=None) -> None:
        if self._closed:
            return
        if self._selection_job:
            try:
                self.window.after_cancel(self._selection_job)
            except TclError:
                pass
        self._selection_job = self.window.after_idle(self._process_tree_selection)

    def _process_tree_selection(self) -> None:
        self._selection_job = None
        selected = self.tree.selection()
        focus = str(self._last_clicked_path) if self._last_clicked_path and str(self._last_clicked_path) in selected else self.tree.focus()
        target = preview_candidate(selected, focus)
        self._selection_changed(tuple(Path(item) for item in selected), Path(target) if target else None)

    def _tree_double_click(self, event=None) -> None:
        if event is not None:
            iid = self.tree.identify_row(event.y)
            if iid:
                self._activate_path(Path(iid))
                return
        selected = self.tree.selection()
        target = preview_candidate(selected, self.tree.focus())
        if target:
            self._activate_path(Path(target))

    def _icon_selection_changed(self, selection: tuple[Path, ...], focus: Path | None) -> None:
        self._selection_changed(selection, focus)

    def _selection_changed(self, _selection: tuple[Path, ...], focus: Path | None) -> None:
        self._update_status()
        if focus is None:
            return
        if focus.is_dir():
            self.preview.configure(image="")
            self.preview_photo = None
            self.preview_value.set("Ordner doppelt anklicken")
            self.meta.configure(text=str(focus))
            return
        self._request_preview(focus)

    def _activate_path(self, path: Path) -> None:
        try:
            if path.is_dir():
                self._navigate(path)
            elif path.is_file():
                self._collect_and_continue()
        except OSError:
            self.status_value.set("Die Datei ist nicht mehr erreichbar. Bitte Ordner neu laden.")

    def _request_preview(self, path: Path) -> None:
        if path == self._last_preview_path:
            return
        self._last_preview_path = path
        self.preview_generation += 1
        generation = self.preview_generation
        self.preview.configure(image="")
        self.preview_photo = None
        self.preview_value.set("Vorschau wird geladen …")
        self.meta.configure(text=path.name)
        if self._preview_future is not None:
            self._preview_future.cancel()
        self._preview_enter()

        def worker() -> None:
            try:
                info = probe_media(path)
                preview_path = build_preview(path, 560) if not self.audio else None
                payload = (info, preview_path, None)
            except Exception as exc:
                payload = (None, None, str(exc))
            self._post_event(("preview", path, generation, payload))

        self._preview_future = self._submit(worker)
        if self._preview_future is None:
            self._preview_leave()
        else:
            self._preview_future.add_done_callback(lambda _future: self._preview_leave())

    def _show_preview(self, path: Path, generation: int, payload) -> None:
        if generation != self.preview_generation or self._closed:
            return
        info, preview_path, error = payload
        if error:
            self.preview_value.set("Vorschau nicht verfügbar")
            self.meta.configure(text=f"{path.name}\n{error}")
            return
        if preview_path:
            try:
                photo = PhotoImage(file=str(preview_path))
                factor = max(1.0, photo.width() / 520.0, photo.height() / 420.0)
                if factor > 1:
                    divisor = int(factor) + (0 if factor.is_integer() else 1)
                    photo = photo.subsample(divisor)
                self.preview_photo = photo
                self.preview.configure(image=self.preview_photo, text="")
            except (TclError, OSError):
                self.preview.configure(image="")
                self.preview_value.set("Vorschau konnte nicht angezeigt werden")
        else:
            self.preview.configure(image="")
            self.preview_value.set("Audio ausgewählt")
        try:
            size = path.stat().st_size
        except OSError:
            size = 0
        duration = "—" if not info or not info.duration else f"{int(info.duration) // 60:02d}:{int(info.duration) % 60:02d}"
        geometry = f"\nAuflösung: {info.width} × {info.height}" if info and info.width and info.height else ""
        codec = info.codec if info and info.codec else "wird beim Auftrag geprüft"
        self.meta.configure(
            text=f"{path.name}\nGröße: {human_size(size)}\nDauer: {duration}\nCodec: {codec}{geometry}\nAktuell markiert: {len(self._selected_paths())}"
        )

    def _request_thumbnail(self, path: Path) -> None:
        if self._closed:
            return

        def worker() -> None:
            try:
                preview_path = build_preview(path, 150)
                error = ""
            except Exception as exc:
                preview_path = None
                error = str(exc)
            self._post_event(("thumbnail", path, preview_path, error))

        self._submit(worker)

    def _show_thumbnail(self, path: Path, preview_path: Path | None, error: str) -> None:
        if self._closed:
            return
        if error or preview_path is None:
            self.icon_grid.mark_thumbnail_failed(path)
            return
        try:
            photo = PhotoImage(file=str(preview_path))
            factor = max(1, (max(photo.width() / 122, photo.height() / 86)))
            if factor > 1:
                photo = photo.subsample(int(factor) + (0 if factor.is_integer() else 1))
        except (TclError, OSError):
            self.icon_grid.mark_thumbnail_failed(path)
            return
        self.icon_grid.install_thumbnail(path, photo)

    def _merge_current_selection(self) -> int:
        added = 0
        for path in self._selected_paths():
            if path not in self.collected:
                self.collected.append(path)
                added += 1
        self._refresh_collection_marks()
        return added

    def _collect_all_visible(self) -> None:
        added = 0
        for record in self._visible_records:
            path = record.path
            try:
                eligible = path.is_file() and path.suffix.lower() in self.allowed
            except OSError:
                eligible = False
            if eligible and path not in self.collected:
                self.collected.append(path)
                added += 1
        self._refresh_collection_marks()
        self.status_value.set(f"{added} sichtbare Datei(en) übernommen. Weitere Ordner oder Filter können verwendet werden.")
        self._update_status()

    def _refresh_collection_marks(self) -> None:
        collected = set(self.collected)
        for item in self.tree.get_children():
            values = list(self.tree.item(item, "values"))
            if len(values) < 5:
                values.extend([""] * (5 - len(values)))
            values[4] = "Übernommen" if Path(item) in collected else ""
            self.tree.item(item, values=values)
        self.icon_grid.set_collected(collected)
        self._update_status()

    def _collect_and_continue(self) -> None:
        added = self._merge_current_selection()
        if not added:
            self.status_value.set("Bitte mindestens eine noch nicht übernommene Datei markieren.")
            return
        if self.view_mode.get() == "icons":
            self.icon_grid.clear_selection()
        else:
            self.tree.selection_remove(*self.tree.selection())
        self.preview.configure(image="")
        self.preview_photo = None
        self._last_preview_path = None
        self.preview_value.set("Auswahl übernommen · weitere Dateien können markiert werden")
        self.meta.configure(text="")
        self._update_status()

    def _clear_collection(self) -> None:
        self.collected.clear()
        self._refresh_collection_marks()

    def _accept(self) -> None:
        self._merge_current_selection()
        if not self.collected:
            self.status_value.set("Bitte mindestens eine Datei auswählen.")
            return
        self.result = tuple(self.collected)
        self._close()

    def _cancel(self) -> None:
        self.result = ()
        self._close()

    def _close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._scan_cancel.set()
        if self._poll_job:
            try:
                self.window.after_cancel(self._poll_job)
            except TclError:
                pass
        if self._selection_job:
            try:
                self.window.after_cancel(self._selection_job)
            except TclError:
                pass
        if self._render_job:
            try:
                self.window.after_cancel(self._render_job)
            except TclError:
                pass
        self._executor.shutdown(wait=False, cancel_futures=True)
        try:
            self.window.grab_release()
        except TclError:
            pass
        try:
            self.window.destroy()
        except TclError:
            pass
