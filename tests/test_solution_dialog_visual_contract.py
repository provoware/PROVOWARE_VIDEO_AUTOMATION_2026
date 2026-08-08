from __future__ import annotations

import inspect

from videobatch_fast.ui_components import SolutionDialog, _bounded_solution_dialog_size


def test_solution_dialog_keeps_reference_size_when_screen_has_room() -> None:
    assert _bounded_solution_dialog_size(1280, 820) == (760, 620)
    assert _bounded_solution_dialog_size(1024, 680) == (760, 620)


def test_solution_dialog_shrinks_fail_safe_on_small_screens() -> None:
    assert _bounded_solution_dialog_size(800, 600) == (752, 552)
    assert _bounded_solution_dialog_size(640, 480) == (592, 432)


def test_solution_dialog_keeps_actions_outside_scroll_body() -> None:
    source = inspect.getsource(SolutionDialog.__init__)
    assert 'action_box = ttk.Frame(outer, style="Card.TFrame"' in source
    assert 'button.grid(row=2, column=0, columnspan=2' in source
    assert 'style="Ghost.TButton"' in source
    assert 'viewer = Text(details, height=3' in source


def test_solution_dialog_primary_action_is_keyboard_first() -> None:
    source = inspect.getsource(SolutionDialog.__init__)
    assert 'self.window.bind("<Escape>"' in source
    assert 'self.primary_button.bind("<Return>"' in source
    assert 'self.primary_button.bind("<KP_Enter>"' in source
    assert 'self.window.after_idle(self.primary_button.focus_set)' in source


def test_solution_dialog_has_clear_visual_hierarchy() -> None:
    source = inspect.getsource(SolutionDialog.__init__)
    assert 'text="Direkte Lösungen"' in source
    assert 'Empfohlen: zuerst die hervorgehobene Aktion ausführen.' in source
    assert 'title_style = "SectionHeader.TLabel" if index == 3 else "Section.TLabel"' in source
    assert 'header = ttk.Frame(outer, style="Card.TFrame"' in source
