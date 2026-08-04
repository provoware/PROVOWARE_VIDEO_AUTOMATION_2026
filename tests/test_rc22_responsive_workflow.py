from __future__ import annotations

import json
import threading
from pathlib import Path

from videobatch_fast.config import normalize_config
from videobatch_fast.incremental_directory import scan_directory_batches
from videobatch_fast.preparation_assistant import build_preparation_checks, preparation_ready
from videobatch_fast.theme import available_themes

ROOT = Path(__file__).resolve().parents[1]


def test_incremental_scan_yields_early_batches_and_skips_links(tmp_path: Path) -> None:
    for index in range(11):
        (tmp_path / f"image-{index:02d}.jpg").write_bytes(b"x" * (index + 1))
    (tmp_path / "ignore.txt").write_text("ignore", encoding="utf-8")
    (tmp_path / "subfolder").mkdir()
    try:
        (tmp_path / "linked.jpg").symlink_to(tmp_path / "image-00.jpg")
    except OSError:
        pass
    batches = list(scan_directory_batches(tmp_path, {".jpg"}, batch_size=4))
    assert [len(batch) for batch in batches] == [4, 4, 4]
    records = [record for batch in batches for record in batch]
    assert records[0].path.parent == tmp_path
    assert any(record.is_dir and record.path.name == "subfolder" for record in records)
    assert all(record.path.name != "linked.jpg" for record in records)
    assert all(record.path.suffix == ".jpg" or record.is_dir for record in records)


def test_incremental_scan_can_be_cancelled_after_first_batch(tmp_path: Path) -> None:
    for index in range(30):
        (tmp_path / f"audio-{index:02d}.wav").write_bytes(b"wave")
    cancel = threading.Event()
    iterator = scan_directory_batches(tmp_path, {".wav"}, cancel=cancel, batch_size=5)
    first = next(iterator)
    cancel.set()
    remaining = list(iterator)
    assert len(first) == 5
    assert remaining == []


def test_preparation_assistant_collects_all_missing_decisions(tmp_path: Path) -> None:
    missing = tmp_path / "missing-output"
    checks = build_preparation_checks(
        audios=[],
        media=[],
        output_dir=missing,
        quick_mode="invalid",
        assignment_mode="pairwise",
        archive_enabled=True,
        archive_dir="",
        analysis_pending=True,
        job_count=0,
    )
    assert not preparation_ready(checks)
    actions = {item.action for item in checks if item.action}
    assert {"add_audio", "add_media", "choose_output", "repair_settings", "show_pairing", "create_project_folder", "focus_waveform"} <= actions


def test_rc22_config_preserves_themes_zoom_and_auto_open() -> None:
    result = normalize_config(
        {
            "theme": "toxic_candy",
            "font_scale": 150,
            "area_zoom": {"start": 180, "media": 70},
            "auto_open_output": False,
            "workflow_layout_mode": "wide",
            "workspace_layout_profiles": {"root_vertical": 0.5},
        }
    )
    assert result["theme"] == "toxic_candy"
    assert result["font_scale"] == 150
    assert result["area_zoom"]["start"] == 180
    assert result["area_zoom"]["media"] == 70
    assert result["auto_open_output"] is False
    assert result["workflow_layout_mode"] == "wide"
    assert "workspace_layout_profiles" not in result
    assert normalize_config({"workflow_layout_mode": "splitter"})["workflow_layout_mode"] == "two_columns"


def test_four_complete_theme_contracts_exist() -> None:
    themes = available_themes()
    assert set(themes) == {"neon_gravity", "acid_paper", "toxic_candy", "ultraviolet"}
    required = {"background_main", "background_surface", "text_primary", "text_secondary", "action_primary", "status_success", "status_error"}
    for name in themes:
        data = json.loads((ROOT / "resources" / "themes" / f"{name}.json").read_text(encoding="utf-8"))
        assert required <= set(data["colors"])
        assert int(data["metrics"]["base_font"]) >= 12


def test_workspace_source_binds_requested_user_flows() -> None:
    source = (ROOT / "src" / "videobatch_fast" / "ui_workspace_grid_mixin.py").read_text(encoding="utf-8")
    events = (ROOT / "src" / "videobatch_fast" / "ui_event_handlers_mixin.py").read_text(encoding="utf-8")
    assert "ScrollableWorkflowGrid" in source
    assert "_scrollable_dashboard_body" in source
    assert "self.header_output_entry" in source
    assert "self._open_settings" in source
    assert "grid.scroll_to_widget(self.settings_card)" in source
    assert "_focus_preparation_assistant" in source
    assert "_open_result_folders" in events
    assert "auto_open_output" in events
    assert "workflow_layout_mode" in source
    assert "_set_workflow_layout_mode" in source
    save_block = (ROOT / "src" / "videobatch_fast" / "ui_services_mixin.py").read_text(encoding="utf-8")
    assert "workflow_layout_mode" in save_block
    assert "workspace_layout_profiles" not in save_block


def test_scrollable_workflow_grid_grows_and_scrolls() -> None:
    from types import SimpleNamespace
    from tkinter import Tk, ttk
    from videobatch_fast.workflow_grid import ScrollableWorkflowGrid

    root = Tk()
    root.geometry("760x520+0+0")
    host = ttk.Frame(root)
    host.pack(fill="both", expand=True)
    grid = ScrollableWorkflowGrid(host, background="#111111", min_cell_height=180)

    def builder(parent):
        frame = ttk.Frame(parent)
        ttk.Label(frame, text="Inhalt").pack()
        return frame

    cards = []
    for index in range(6):
        cards.append(
            grid.add_card(
                title=f"Karte {index}",
                subtitle="Dynamischer Inhalt" if index % 2 else "",
                builder=builder if index % 2 else None,
                row=index // 2,
                column=index % 2,
            )
        )
    root.update_idletasks()
    assert grid._rows == 3
    assert len(grid.cards) == 6
    grid.set_layout_mode("wide")
    root.update_idletasks()
    assert grid.layout_mode == "wide"
    assert grid._rows == 6
    assert cards[1].grid_info()["row"] == 1
    assert cards[1].grid_info()["column"] == 0
    grid.set_layout_mode("compact")
    root.update_idletasks()
    assert grid.layout_mode == "compact"
    assert grid._rows == 3
    assert cards[1].grid_info()["row"] == 0
    assert cards[1].grid_info()["column"] == 1
    assert grid.body.winfo_reqheight() > grid.canvas.winfo_height()
    grid.scroll_to_widget(cards[-1])
    root.update_idletasks()
    assert grid.canvas.yview()[0] > 0
    assert grid._wheel(SimpleNamespace(state=0x4, delta=120)) is None
    assert grid._wheel(SimpleNamespace(state=0, delta=120)) == "break"
    assert grid._wheel(SimpleNamespace(state=0, delta=0)) is None
    root.destroy()


def test_scrollable_workflow_grid_survives_destroyed_widgets() -> None:
    from tkinter import Tk, ttk
    from videobatch_fast.workflow_grid import ScrollableWorkflowGrid

    root = Tk()
    host = ttk.Frame(root)
    host.pack(fill="both", expand=True)
    grid = ScrollableWorkflowGrid(host, background="#000000")
    card = grid.add_card(title="Test", builder=lambda parent: parent, row=0, column=0)
    root.update_idletasks()
    card.destroy()
    grid.refresh()
    grid.scroll_to_widget(card)
    grid._sync_scroll_region()
    grid._sync_width_and_rows()
    assert grid._scroll(1) == "break"
    root.destroy()
