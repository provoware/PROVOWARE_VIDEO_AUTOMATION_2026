from __future__ import annotations

import time
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

from videobatch_fast.media_import_dialog import preview_candidate
from videobatch_fast.theme import best_text_color, contrast_ratio, safe_text_color

ROOT = Path(__file__).resolve().parents[1]


def test_background_workers_never_call_tk_directly() -> None:
    source = (ROOT / "src/videobatch_fast/media_import_dialog.py").read_text(encoding="utf-8")
    assert "ThreadPoolExecutor" in source
    runtime = (ROOT / "src/videobatch_fast/media_dialog_runtime.py").read_text(encoding="utf-8")
    assert "self._post_event" in source
    assert "queue.Queue(maxsize=256)" in source
    assert "self._events.put" in runtime
    assert "self.window.after(0" not in source
    assert 'view_mode = StringVar(window, value="list" if audio else "icons")' in source
    assert "VirtualThumbnailGrid" in source


def test_contrast_helpers_force_dark_text_on_white_fields() -> None:
    assert best_text_color("#FFFFFF").lower() == "#111318"
    assert contrast_ratio("#FFFFFF", best_text_color("#FFFFFF")) >= 4.5
    assert contrast_ratio("#111111", best_text_color("#111111")) >= 4.5
    assert safe_text_color("#FFFFFF", "#F8F8F8") == best_text_color("#FFFFFF")
    assert safe_text_color("#FFFFFF", "#171717") == "#171717"


def test_preview_candidate_still_tracks_last_active_item() -> None:
    selected = ("/tmp/a.png", "/tmp/b.png", "/tmp/c.png")
    assert preview_candidate(selected, "/tmp/b.png") == "/tmp/b.png"
    assert preview_candidate(selected, "") == "/tmp/c.png"


def test_media_dialog_rapid_selection_is_thread_safe_and_icon_view_works(tmp_path: Path, monkeypatch) -> None:
    from tkinter import Tk, ttk

    import videobatch_fast.media_import_dialog as dialog_module
    from videobatch_fast.media_import_dialog import MediaImportDialog
    from videobatch_fast.theme import apply_theme

    for index in range(7):
        Image.new("RGB", (240 + index, 160), (20 * index, 70, 130)).save(tmp_path / f"image-{index}.png")

    def fake_preview(path: Path, _width: int) -> Path:
        return path

    def fake_probe(_path: Path):
        return SimpleNamespace(kind="image", duration=0.0, width=240, height=160, codec="png")

    monkeypatch.setattr(dialog_module, "build_preview", fake_preview)
    monkeypatch.setattr(dialog_module, "probe_media", fake_probe)

    root = Tk()
    root.geometry("1050x760+0+0")
    apply_theme(root, 100, "acid_paper")
    style = ttk.Style(root)
    field_bg = style.lookup("TEntry", "fieldbackground")
    field_fg = style.lookup("TEntry", "foreground")
    assert contrast_ratio(field_bg, field_fg) >= 4.5

    dialog = MediaImportDialog(root, audio=False, initial_dir=tmp_path, modal=False)
    deadline = time.monotonic() + 5
    while not dialog._scan_complete and time.monotonic() < deadline:
        root.update()
        time.sleep(0.01)
    assert len(dialog._records) == 7
    assert dialog.view_mode.get() == "icons"
    assert dialog.icon_frame.winfo_width() >= 2 * dialog.preview.master.winfo_width()
    assert dialog.preview.master.winfo_width() >= dialog.preview.winfo_reqwidth()

    dialog._set_view_mode("list")
    children = dialog.tree.get_children()
    assert len(children) == 7
    for index in range(60):
        chosen = children[index % len(children)]
        dialog.tree.selection_set(children[:3])
        dialog.tree.focus(chosen)
        dialog._last_clicked_path = Path(chosen)
        dialog._process_tree_selection()
        root.update()
    deadline = time.monotonic() + 2
    while (dialog._events.qsize() or dialog._preview_busy.is_set()) and time.monotonic() < deadline:
        root.update()
        time.sleep(0.01)
    assert dialog._last_preview_path is not None
    assert not dialog._preview_busy.is_set()
    assert dialog._preview_workers == 0

    dialog._set_view_mode("icons")
    first, second = Path(children[1]), Path(children[2])
    dialog.icon_grid.selected = {first, second}
    dialog.icon_grid.focus_path = second
    dialog._icon_selection_changed(dialog.icon_grid.selected_paths(), second)
    for _ in range(20):
        root.update()
        time.sleep(0.005)
    assert dialog._selected_paths() == [first, second]
    assert dialog._last_preview_path == second

    dialog._cancel()
    root.update()
    root.destroy()


def test_media_dialog_support_sorting_and_safe_fallback(tmp_path: Path, monkeypatch) -> None:
    import videobatch_fast.media_dialog_support as support
    from videobatch_fast.incremental_directory import DirectoryRecord

    downloads = tmp_path / "Downloads"
    downloads.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    assert support.safe_media_directory(tmp_path / "missing") == downloads
    assert support.human_size(512) == "512.0 B"
    assert support.human_size(2048) == "2.0 KB"
    records = [
        DirectoryRecord(tmp_path / "b.png", False, 20, 2.0),
        DirectoryRecord(tmp_path / "a.jpg", False, 10, 3.0),
        DirectoryRecord(tmp_path / "folder", True, 0, 1.0),
    ]
    assert [item.path.name for item in support.sort_directory_records(records, "name", False)] == ["folder", "a.jpg", "b.png"]
    assert [item.path.name for item in support.sort_directory_records(records, "size", False)] == ["folder", "a.jpg", "b.png"]
    assert [item.path.name for item in support.sort_directory_records(records, "modified", True)][0] == "folder"
    assert len(support.sort_directory_records(records, "kind", False)) == 3
    assert all(support.media_filter_matches(record, "Alle Dateien") for record in records)
    assert support.media_filter_matches(records[2], "Bilder")
    assert support.media_filter_matches(records[2], "Videos")
    assert support.media_filter_matches(records[1], "Bilder")
    assert not support.media_filter_matches(records[1], "Videos")
    audio = DirectoryRecord(tmp_path / "sound.wav", False, 30, 4.0)
    assert support.media_filter_matches(audio, "Audio")


def test_virtual_thumbnail_grid_interactions_cover_multiselect_and_navigation(tmp_path: Path) -> None:
    from tkinter import PhotoImage, Tk, ttk

    from videobatch_fast.incremental_directory import DirectoryRecord
    from videobatch_fast.theme import apply_theme
    from videobatch_fast.thumbnail_grid import VirtualThumbnailGrid, compact_filename

    paths = [tmp_path / "folder", tmp_path / "one.png", tmp_path / "two.mp4", tmp_path / "sound.wav"]
    paths[0].mkdir()
    Image.new("RGB", (32, 24), (80, 20, 160)).save(paths[1])
    paths[2].write_bytes(b"video")
    paths[3].write_bytes(b"audio")
    records = [
        DirectoryRecord(paths[0], True, 0, 1.0),
        DirectoryRecord(paths[1], False, paths[1].stat().st_size, 2.0),
        DirectoryRecord(paths[2], False, 5, 3.0),
        DirectoryRecord(paths[3], False, 5, 4.0),
    ]
    assert compact_filename("kurz.png") == ("kurz.png", False)
    compact, truncated = compact_filename("sehr_langer_dateiname_fuer_vorschau.mp4")
    assert truncated and compact.endswith("….mp4") and len(compact) <= 18
    selections: list[tuple[tuple[Path, ...], Path | None]] = []
    activated: list[Path] = []
    requested: list[Path] = []

    root = Tk()
    root.geometry("760x520+0+0")
    apply_theme(root, 100, "neon_gravity")
    host = ttk.Frame(root)
    host.pack(fill="both", expand=True)
    grid = VirtualThumbnailGrid(
        host,
        on_selection=lambda selected, focus: selections.append((selected, focus)),
        on_activate=activated.append,
        request_thumbnail=requested.append,
        audio=False,
    )
    grid.pack(fill="both", expand=True)
    grid.set_records(records, collected=[paths[1]])
    root.update_idletasks()
    root.update()
    grid._redraw()
    assert paths[1] in requested

    event = SimpleNamespace(x=20, y=20, state=0)
    assert grid._click(event) == "break"
    assert grid.focus_path == paths[0]
    long_path = tmp_path / "sehr_langer_dateiname_fuer_vorschau.mp4"
    grid.set_records([*records, DirectoryRecord(long_path, False, 5, 5.0)])
    grid._hover(SimpleNamespace(x=20, y=196))
    assert grid.name_tooltip.message == long_path.name
    deadline = time.monotonic() + 0.6
    while grid.name_tooltip.window is None and time.monotonic() < deadline:
        root.update()
        time.sleep(0.01)
    assert grid.name_tooltip.window.winfo_children()[0].cget("text") == long_path.name
    grid._leave()
    grid.focus_path = long_path
    grid.canvas.event_generate("<FocusIn>")
    assert grid.name_tooltip.message == long_path.name
    grid.name_tooltip.update_message("")
    event = SimpleNamespace(x=190, y=20, state=0x4)
    grid._click(event)
    assert set(grid.selected_paths()) == {paths[0], paths[1]}
    event = SimpleNamespace(x=370, y=20, state=0x1)
    grid._click(event)
    assert paths[2] in grid.selected
    grid._double_click(SimpleNamespace(x=370, y=20, state=0))
    assert activated[-1] == paths[2]
    assert grid._toggle_focus() == "break"
    grid.focus_path = paths[1]
    assert grid._activate_focus() == "break"
    assert activated[-1] == paths[1]
    assert grid._wheel(SimpleNamespace(num=4, delta=0)) == "break"
    assert grid._wheel(SimpleNamespace(num=5, delta=0)) == "break"
    assert grid._wheel(SimpleNamespace(num=None, delta=120)) == "break"

    photo = PhotoImage(width=8, height=8)
    grid.install_thumbnail(paths[1], photo)
    grid.mark_thumbnail_failed(paths[2])
    grid.set_collected([paths[2]])
    grid.clear_selection()
    assert selections[-1] == ((), None)
    grid._click(SimpleNamespace(x=9999, y=9999, state=0))
    grid._yview("moveto", 0.0)
    grid.destroy()
    root.destroy()


def test_virtual_thumbnail_grid_only_renders_visible_tiles_for_huge_folder(tmp_path: Path) -> None:
    from tkinter import Tk, ttk

    from videobatch_fast.incremental_directory import DirectoryRecord
    from videobatch_fast.theme import apply_theme
    from videobatch_fast.thumbnail_grid import VirtualThumbnailGrid

    records = [
        DirectoryRecord(tmp_path / f"image-{index:05d}.png", False, 1024 + index, float(index))
        for index in range(20_000)
    ]
    requested: list[Path] = []
    root = Tk()
    root.geometry("900x640+0+0")
    apply_theme(root, 100, "toxic_candy")
    host = ttk.Frame(root)
    host.pack(fill="both", expand=True)
    grid = VirtualThumbnailGrid(
        host,
        on_selection=lambda _selected, _focus: None,
        on_activate=lambda _path: None,
        request_thumbnail=requested.append,
        audio=False,
    )
    grid.pack(fill="both", expand=True)
    grid.set_records(records)
    root.update_idletasks()
    root.update()
    grid._redraw()

    assert len(grid.records) == 20_000
    assert len(requested) < 100
    assert len(grid.canvas.find_all()) < 800

    grid.destroy()
    root.destroy()
