from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_tooltip_is_delayed_keyboard_accessible_and_screen_bound() -> None:
    source = (ROOT / "src/videobatch_fast/ui_components.py").read_text(encoding="utf-8")
    assert "delay_ms: int = 350" in source
    assert 'widget.bind("<FocusIn>"' in source
    assert 'widget.bind("<Destroy>"' in source
    assert "winfo_screenwidth" in source
    assert "after_cancel" in source
    assert "except TclError" in source


def test_cache_and_help_actions_have_tooltips() -> None:
    media = (ROOT / "src/videobatch_fast/media_dialog_layout.py").read_text(encoding="utf-8")
    components = (ROOT / "src/videobatch_fast/ui_components.py").read_text(encoding="utf-8")
    assert media.count("Tooltip(") >= 9
    assert components.count("help_center.tooltip.") >= 6
