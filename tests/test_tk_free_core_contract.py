from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def _run_import_probe(module: str) -> subprocess.CompletedProcess[str]:
    code = (
        "import sys; "
        f"import {module}; "
        "assert 'tkinter' not in sys.modules, sorted(name for name in sys.modules if name.startswith('tkinter')); "
        "print('TK_FREE_IMPORT_OK')"
    )
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env={"PYTHONPATH": str(SRC)},
        text=True,
        capture_output=True,
        check=False,
    )


def test_config_import_does_not_load_tkinter() -> None:
    result = _run_import_probe("videobatch_fast.config")
    assert result.returncode == 0, result.stderr
    assert "TK_FREE_IMPORT_OK" in result.stdout


def test_assurance_import_does_not_load_tkinter() -> None:
    result = _run_import_probe("videobatch_fast.assurance")
    assert result.returncode == 0, result.stderr
    assert "TK_FREE_IMPORT_OK" in result.stdout
