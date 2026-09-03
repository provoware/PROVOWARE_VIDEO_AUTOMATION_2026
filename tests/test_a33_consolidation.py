from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_start_help_and_python_preflight_contract() -> None:
    start = (ROOT / "start.sh").read_text(encoding="utf-8")
    starten = (ROOT / "STARTEN.sh").read_text(encoding="utf-8")
    assert "--help" in start and "--hilfe" in start and "--diagnose" in start
    assert "command -v" in starten
    assert "exit 127" in starten
    assert "Originalmedien wurden nicht verändert" in starten


def test_current_watchdog_keeps_existing_instance_handoff_safe() -> None:
    source = (ROOT / "scripts" / "debug_launcher.py").read_text(encoding="utf-8")
    assert "_EXISTING_INSTANCE_RE" in source
    assert "_monitor_ready_application" in source
    assert "existing_instance" in source
    assert "nicht als Absturz überwacht" in source


def test_compact_shell_and_kde_scaling_contract() -> None:
    contract = (ROOT / "src" / "videobatch_fast" / "canonical_shell_contract.py").read_text(encoding="utf-8")
    workspace = (ROOT / "src" / "videobatch_fast" / "canonical_shell_workspace.py").read_text(encoding="utf-8")
    ui = (ROOT / "src" / "videobatch_fast" / "canonical_ui.py").read_text(encoding="utf-8")
    assert "SIDEBAR_WIDTH = 188" in contract
    assert "Hilfe & Diagnose" in contract
    assert "self.root.columnconfigure(0, weight=1)" in workspace
    assert 'sticky="nsew"' in workspace
    assert "VIDEOBATCH_TK_SCALING" in ui
    assert 'winfo_fpixels("1i") / 72.0' not in ui


def test_architecture_audit_survives_bad_python_file(tmp_path: Path) -> None:
    path = ROOT / "scripts" / "architecture_audit.py"
    spec = importlib.util.spec_from_file_location("a33_architecture_audit", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    (tmp_path / "gut.py").write_text("def ok():\n    return 1\n", encoding="utf-8")
    (tmp_path / "kaputt.py").write_text("def kaputt(:\n", encoding="utf-8")
    result = module.audit_source_tree(tmp_path)
    assert result["modules"] == 2
    assert result["functions"] == 1
    assert any("Syntaxfehler" in item for item in result["findings"])
