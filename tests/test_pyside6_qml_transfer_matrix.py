from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "docs/architecture/PYSIDE6_QML_TRANSFER_MATRIX.json"


def _matrix() -> dict:
    payload = json.loads(MATRIX.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_transfer_matrix_has_unique_complete_entries() -> None:
    payload = _matrix()
    assert payload["schema_version"] == 1
    assert payload["iteration"] == "39B"
    assert payload["target"] == "PySide6/QML"
    items = payload["items"]
    assert len(items) >= 15
    paths = [item["path"] for item in items]
    assert len(paths) == len(set(paths))
    for item in items:
        assert item["class"] in {"A", "B", "C"}
        assert item["reason"].strip()
        assert item["qt_action"].strip()
        assert item["gate"].strip()


def test_known_toolkit_neutral_core_is_class_a() -> None:
    classes = {item["path"]: item["class"] for item in _matrix()["items"]}
    required_a = {
        "start.sh",
        "STARTEN.sh",
        "scripts/architecture_audit.py",
        "scripts/release_file_contract.py",
        "scripts/package_release.py",
        "scripts/verify_release_zip.py",
        "src/videobatch_fast/error_handling.py",
        "src/videobatch_fast/runtime_error_guidance.py",
        "registries/RUNTIME_ERROR_REGISTRY.json",
    }
    assert {path for path in required_a if classes.get(path) != "A"} == set()


def test_mixed_runtime_and_shell_contracts_require_adapters() -> None:
    classes = {item["path"]: item["class"] for item in _matrix()["items"]}
    required_b = {
        "scripts/debug_launcher.py",
        "src/videobatch_fast/runtime_error_hooks.py",
        "src/videobatch_fast/canonical_shell_contract.py",
        ".github/workflows/a33-consolidated-package.yml",
    }
    assert {path for path in required_b if classes.get(path) != "B"} == set()


def test_tk_shell_is_never_marked_directly_transferable() -> None:
    classes = {item["path"]: item["class"] for item in _matrix()["items"]}
    required_c = {
        "src/videobatch_fast/canonical_ui.py",
        "src/videobatch_fast/canonical_shell_workspace.py",
        "src/videobatch_fast/canonical_shell_chrome.py",
    }
    assert {path for path in required_c if classes.get(path) != "C"} == set()


def test_class_a_python_sources_do_not_import_tkinter() -> None:
    payload = _matrix()
    for item in payload["items"]:
        path = item["path"]
        if item["class"] != "A" or not path.endswith(".py"):
            continue
        source = (ROOT / path).read_text(encoding="utf-8")
        assert "import tkinter" not in source, path
        assert "from tkinter" not in source, path


def test_qt_transfer_does_not_weaken_existing_stable_gates() -> None:
    gates = set(_matrix()["stable_gates_unchanged"])
    assert "coverage lines >= 80%" in gates
    assert "coverage branches >= 65%" in gates
    assert "physical Kubuntu KDE X11 acceptance" in gates
    assert "physical Kubuntu KDE Wayland acceptance" in gates
    assert "large-media long-render soak on slow external target" in gates
