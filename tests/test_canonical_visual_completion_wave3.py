from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "videobatch_fast"


def test_packaged_icon_set_is_local_png_and_complete() -> None:
    icon_dir = ROOT / "assets" / "icons" / "ui"
    required = {
        "brand",
        "dashboard",
        "media",
        "queue",
        "effects",
        "scheduler",
        "preview",
        "diagnostics",
        "settings",
        "new",
        "import",
        "start",
        "backup",
    }
    for name in required:
        for size in (20, 32, 40):
            path = icon_dir / f"{name}-{size}.png"
            assert path.is_file(), path
            with Image.open(path) as image:
                assert image.format == "PNG"
                assert image.size == (size, size)


def test_canonical_shell_uses_packaged_icons_instead_of_font_symbols() -> None:
    source = (SRC / "canonical_shell_chrome.py").read_text(encoding="utf-8")
    contract = (SRC / "canonical_shell_contract.py").read_text(encoding="utf-8")
    assert "load_ui_icon" in source
    assert 'compound="left"' in source
    for symbol in ("⌂", "▧", "☷", "✦", "◷", "▣", "◎", "⚙"):
        assert symbol not in contract


def test_queue_thumbnail_mixin_reuses_persistent_preview_service() -> None:
    source = (SRC / "canonical_queue_thumbnail_mixin.py").read_text(encoding="utf-8")
    ast.parse(source)
    assert "build_preview" in source
    assert "load_preview_bitmap" in source
    assert "threading.Thread" in source
    assert "daemon=True" in source
    assert "preview_cache" not in source.lower() or "persistent preview cache" in source.lower()


def test_queue_table_exposes_thumbnail_tree_column_and_selected_job_requests_preview() -> None:
    source = (SRC / "canonical_dashboard_mixin.py").read_text(encoding="utf-8")
    assert 'show=("tree", "headings")' in source
    assert 'tree.column("#0", width=62' in source
    assert "_request_queue_thumbnail(item_id, job)" in source
    assert "_set_dashboard_transport_source(preview_source)" in source
    assert "self._request_preview(preview_source)" in source


def test_preview_transport_is_single_ffplay_backed_state_machine() -> None:
    player_source = (SRC / "preview_player.py").read_text(encoding="utf-8")
    transport_source = (SRC / "canonical_preview_transport_mixin.py").read_text(encoding="utf-8")
    ast.parse(player_source)
    ast.parse(transport_source)
    assert 'shutil.which("ffplay")' in player_source
    assert "SIGSTOP" in player_source and "SIGCONT" in player_source
    assert "def seek(" in player_source
    assert "PreviewPlayer()" in transport_source
    assert "_dashboard_transport_seek" in transport_source
    assert "_dashboard_preview_player" in transport_source


def test_queue_thumbnail_source_prefers_real_source_media(tmp_path: Path) -> None:
    from videobatch_fast.canonical_queue_thumbnail_mixin import CanonicalQueueThumbnailMixin

    source = tmp_path / "frame.png"
    source.write_bytes(b"x")
    job = SimpleNamespace(source_media=(source,), output=tmp_path / "missing.mp4")
    mixin = CanonicalQueueThumbnailMixin()
    assert mixin._queue_thumbnail_source(job) == source
