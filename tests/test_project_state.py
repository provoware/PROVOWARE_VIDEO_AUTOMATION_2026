

def test_invalid_slideshow_order_mode_is_normalized() -> None:
    from videobatch_fast.project_state import normalize_project_state

    state = normalize_project_state({"slideshow_order_mode": "unbekannt"})
    assert state["slideshow_order_mode"] == "manual"
