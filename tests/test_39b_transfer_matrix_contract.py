from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "A33_PYSIDE6_TRANSFER_MATRIX.json"
SOURCE_SHA = "121211244d90932775348ac26039b3d7315e60b2"
VALID_CLASSES = {"A_DIRECT", "B_ADAPTER", "C_REIMPLEMENT"}


def _matrix() -> dict:
    return json.loads(MATRIX_PATH.read_text(encoding="utf-8"))


def _component_by_path(matrix: dict, path: str) -> dict | None:
    for component in matrix["components"]:
        if path in component["paths"]:
            return component
    return None


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names.add(module)
    return names


def test_matrix_schema_lineage_and_classes_are_fail_closed() -> None:
    matrix = _matrix()
    assert matrix["schema_version"] == 1
    assert matrix["iteration"] == "39B"
    assert matrix["source_lineage_sha"] == SOURCE_SHA
    assert matrix["target_architecture"] == "PySide6/QML"
    assert matrix["components"]

    ids = [item["id"] for item in matrix["components"]]
    assert len(ids) == len(set(ids))
    for component in matrix["components"]:
        assert component["classification"] in VALID_CLASSES
        assert component["paths"]
        assert component["rationale"].strip()
        assert component["transfer_action"].strip()
        assert component["test_gate"].strip()
        assert component["transfer_status"].strip()


def test_all_required_a33_process_paths_are_classified_exactly_once() -> None:
    matrix = _matrix()
    seen: dict[str, int] = {}
    for component in matrix["components"]:
        for path in component["paths"]:
            seen[path] = seen.get(path, 0) + 1

    for path in matrix["required_a33_process_paths"]:
        assert seen.get(path) == 1, path


def test_direct_python_components_have_no_gui_toolkit_imports() -> None:
    matrix = _matrix()
    forbidden = ("tkinter", "PySide6", "PyQt6", "ui_components")
    for component in matrix["components"]:
        if component["classification"] != "A_DIRECT":
            continue
        for relative in component["paths"]:
            if not relative.endswith(".py"):
                continue
            path = ROOT / relative
            assert path.is_file(), relative
            imports = _imports(path)
            bad = sorted(
                name
                for name in imports
                if any(
                    name == token
                    or name.startswith(token + ".")
                    or name.endswith("." + token)
                    for token in forbidden
                )
            )
            assert not bad, f"{relative}: GUI-Import in A_DIRECT: {bad}"


def test_known_tk_coupled_files_can_never_be_direct_transfer() -> None:
    matrix = _matrix()
    for relative in (
        "src/videobatch_fast/runtime_error_hooks.py",
        "src/videobatch_fast/debug_runtime.py",
        "src/videobatch_fast/theme.py",
    ):
        component = _component_by_path(matrix, relative)
        assert component is not None, relative
        assert component["classification"] == "B_ADAPTER", relative


def test_tk_shell_root_and_workspace_must_be_reimplemented() -> None:
    matrix = _matrix()
    for relative in (
        "src/videobatch_fast/canonical_ui.py",
        "src/videobatch_fast/canonical_shell_workspace.py",
    ):
        component = _component_by_path(matrix, relative)
        assert component is not None, relative
        assert component["classification"] == "C_REIMPLEMENT", relative
        assert component["transfer_status"] == "DO_NOT_COPY", relative


def test_long_render_target_remains_blocked_until_real_evidence_exists() -> None:
    matrix = _matrix()
    component = _component_by_path(
        matrix, "src/videobatch_fast/long_render_target.py"
    )
    assert component is not None
    assert component["classification"] == "A_DIRECT"
    assert component["transfer_status"] == "BLOCKED_TEST_GAP"
    assert "Slow-Target" in component["test_gate"]


def test_selection_preview_is_not_wholesale_direct_transfer() -> None:
    matrix = _matrix()
    component = _component_by_path(
        matrix, "src/videobatch_fast/selection_preview_controller.py"
    )
    assert component is not None
    assert component["classification"] == "B_ADAPTER"
    assert component["transfer_status"] == "EXTRACT_SMALL_UI_HELPER"


def test_recommended_first_candidate_is_direct_and_not_test_blocked() -> None:
    matrix = _matrix()
    recommendation = matrix["recommended_first_candidate_after_39B"]
    selected = next(
        item
        for item in matrix["components"]
        if item["id"] == recommendation["component_id"]
    )
    assert selected["classification"] == "A_DIRECT"
    assert selected["transfer_status"] != "BLOCKED_TEST_GAP"


def test_stable_release_blockers_are_not_erased_by_transfer_governance() -> None:
    matrix = _matrix()
    blockers = "\n".join(matrix["stable_blockers_unchanged"])
    assert "80" in blockers and "65" in blockers
    assert "X11" in blockers and "Wayland" in blockers
    assert "Slow" in blockers or "slow" in blockers
