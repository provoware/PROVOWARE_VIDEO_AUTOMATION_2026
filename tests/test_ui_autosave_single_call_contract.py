"""Regression: Nutzeraktionen sollen den Projektstand nur einmal sichern."""
from __future__ import annotations

import ast
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "src" / "videobatch_fast" / "ui.py"


def test_user_actions_trigger_only_one_project_save() -> None:
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    ui_class = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "VideoBatchFastUI")
    for name in ("_apply_view_order", "_append_paths"):
        method = next(node for node in ui_class.body if isinstance(node, ast.FunctionDef) and node.name == name)
        saves = [
            node for node in ast.walk(method)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "_autosave_project"
        ]
        assert len(saves) == 1, f"{name}: erwartet genau einen Speichervorgang, gefunden {len(saves)}"
