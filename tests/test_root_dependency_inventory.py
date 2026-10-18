from __future__ import annotations

import importlib.util
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "scripts" / "root_dependency_inventory.py"
spec = importlib.util.spec_from_file_location("root_dependency_inventory", PATH)
assert spec and spec.loader
inv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inv)


def test_root_index_preserves_start_scripts_and_flags_frozen(tmp_path) -> None:
    (tmp_path / "STARTEN.sh").write_text("#!/bin/sh\n")
    (tmp_path / "FINAL_AUDIT_rc24_save_.md").write_text("frozen\n")
    (tmp_path / "README.md").write_text("Run STARTEN.sh\n")
    report = inv.root_report(tmp_path)
    entries = {x["path"]: x for x in report["items"]}
    assert entries["STARTEN.sh"]["role"] == "entrypoint_keep"
    assert entries["FINAL_AUDIT_rc24_save_.md"]["role"] == "frozen_or_contract"
    assert any(x["path"] == "README.md" for x in entries["STARTEN.sh"]["references"])
    assert report["release_authorized"] is False
