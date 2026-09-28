from videobatch_fast.motion_planner import MotionRecipe, plan_motion, preset


def test_zoom_in_shrinks_target_and_keeps_aspect() -> None:
    plan = plan_motion(6000, 4000, preset("zoom_in"), aspect="16:9")
    assert plan.start.width == 6000
    assert plan.start.height == 3375
    assert plan.target.width < plan.start.width
    assert abs(plan.target.width / plan.target.height - 16 / 9) < 0.001
    assert plan.movement == 1


def test_zoom_out_is_inverse_size_direction() -> None:
    plan = plan_motion(6000, 4000, preset("zoom_out"), aspect="16:9")
    assert plan.start.width < plan.target.width
    assert plan.start.height < plan.target.height


def test_focus_is_clamped_inside_portrait_image() -> None:
    recipe = MotionRecipe(1.4, 1.4, (0.0, 0.0), (1.0, 1.0))
    plan = plan_motion(3000, 5000, recipe, aspect="16:9")
    for rect in (plan.start, plan.target):
        assert rect.left >= 0
        assert rect.top >= 0
        assert rect.left + rect.width <= 3000
        assert rect.top + rect.height <= 5000
