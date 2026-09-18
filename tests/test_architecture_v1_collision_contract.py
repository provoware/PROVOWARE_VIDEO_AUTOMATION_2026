from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "ARCHITECTURE_V1.json"


def _source(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _rules() -> dict[str, object]:
    payload = json.loads(RULES.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["checkpoint"] == "CP-02"
    return payload


def test_cp02_rules_are_machine_readable_and_product_logic_is_out_of_scope() -> None:
    rules = _rules()
    policy = rules["change_policy"]
    assert isinstance(policy, dict)
    assert policy["single_writer"] is True
    assert policy["smallest_meaningful_patch"] is True
    assert policy["big_bang_rewrite"] is False
    assert policy["product_logic_changes_in_cp02"] is False


def test_canonical_entrypoint_routes_only_to_qt_phase3() -> None:
    source = _source("src/videobatch_fast/__main__.py")
    assert "from .qt_phase3 import main" in source
    assert "raise SystemExit(main())" in source
    assert "from .app import main" not in source
    assert "canonical_ui" not in source
    assert "tkinter" not in source.lower()


def test_active_gui_modules_are_pyside6_only() -> None:
    rules = _rules()
    modules = rules["active_gui_modules"]
    forbidden = rules["forbidden_in_active_gui"]
    assert isinstance(modules, list)
    assert isinstance(forbidden, list)

    for relative in modules:
        source = _source(str(relative))
        for token in forbidden:
            assert str(token).casefold() not in source.casefold(), (
                f"{relative} enthält im aktiven Qt6-Pfad verbotenen GUI-Verweis: {token}"
            )


def test_legacy_gui_is_explicitly_noncanonical() -> None:
    rules = _rules()
    legacy = rules["legacy_noncanonical_gui"]
    assert isinstance(legacy, list)
    assert "src/videobatch_fast/canonical_ui.py" in legacy
    assert "src/videobatch_fast/app.py" in legacy

    entrypoint = _source("src/videobatch_fast/__main__.py")
    for relative in legacy:
        module_name = Path(str(relative)).stem
        assert module_name not in entrypoint


def test_qt_ui_delegates_production_to_batch_runner() -> None:
    qt_ui = _source("src/videobatch_fast/qt_ui.py")
    assert "from .runner import BatchRunner" in qt_ui
    assert "self.runner = BatchRunner(" in qt_ui


def test_batch_runner_owns_production_process_execution_boundary() -> None:
    runner = _source("src/videobatch_fast/runner.py")
    executor = _source("src/videobatch_fast/runner_process.py")

    assert "ProcessExecution(" in runner
    assert "execution.run(" in runner
    assert "subprocess.Popen" in executor


def test_canonical_persistence_stores_use_atomic_json_writer() -> None:
    rules = _rules()
    persistence = rules["persistence"]
    assert isinstance(persistence, dict)
    writer = str(persistence["atomic_writer"])

    for key in ("project_store", "config_store", "retry_store"):
        relative = str(persistence[key])
        source = _source(relative)
        assert writer in source, f"{relative} nutzt den kanonischen Atomic-Writer nicht."


def test_cp02_does_not_introduce_sqlite_as_parallel_store() -> None:
    rules = _rules()
    persistence = rules["persistence"]
    assert isinstance(persistence, dict)
    assert persistence["sqlite_status"] == "not_required_without_proven_relational_need"

    canonical_stores = (
        "src/videobatch_fast/project_state.py",
        "src/videobatch_fast/config.py",
        "src/videobatch_fast/retry_queue.py",
    )
    for relative in canonical_stores:
        source = _source(relative)
        assert "sqlite3" not in source
        assert "sqlite3.connect" not in source


def test_collision_contract_has_no_duplicate_canonical_owners() -> None:
    rules = _rules()
    entrypoint = rules["canonical_entrypoint"]
    ffmpeg = rules["ffmpeg"]
    persistence = rules["persistence"]

    assert isinstance(entrypoint, dict)
    assert isinstance(ffmpeg, dict)
    assert isinstance(persistence, dict)

    owners = [
        entrypoint["module_file"],
        ffmpeg["production_runner"],
        ffmpeg["process_executor"],
        persistence["project_store"],
        persistence["config_store"],
        persistence["retry_store"],
    ]
    assert len(owners) == len(set(owners))
