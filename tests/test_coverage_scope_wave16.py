from __future__ import annotations

import fnmatch
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _omit_patterns() -> list[str]:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return list(config["tool"]["coverage"]["run"]["omit"])


def test_refactored_presentation_modules_stay_in_ui_coverage_exclusion() -> None:
    patterns = _omit_patterns()
    presentation = (
        "src/videobatch_fast/canonical_dashboard_mixin.py",
        "src/videobatch_fast/canonical_shell_chrome.py",
        "src/videobatch_fast/canonical_shell_workspace.py",
        "src/videobatch_fast/canonical_ui.py",
        "src/videobatch_fast/project_backup_dialog.py",
        "src/videobatch_fast/media_dialog_layout.py",
        "src/videobatch_fast/scheduler_policy_dialog.py",
    )
    uncovered = [path for path in presentation if not any(fnmatch.fnmatch(path, pattern) for pattern in patterns)]
    assert not uncovered, f"UI-Präsentationsmodule fehlen im etablierten Coverage-Ausschluss: {uncovered}"


def test_canonical_business_logic_remains_covered() -> None:
    patterns = _omit_patterns()
    core = (
        "src/videobatch_fast/canonical_kpi.py",
        "src/videobatch_fast/canonical_kpi_state.py",
        "src/videobatch_fast/canonical_shell_contract.py",
    )
    wrongly_excluded = [path for path in core if any(fnmatch.fnmatch(path, pattern) for pattern in patterns)]
    assert not wrongly_excluded, f"Kernlogik darf nicht aus Coverage verschwinden: {wrongly_excluded}"
