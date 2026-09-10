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


def test_supported_wayland_bootstrap_contains_no_tk_dependency() -> None:
    bootstrap = (ROOT / "scripts" / "bootstrap.py").read_text(encoding="utf-8")
    toolchain = (ROOT / "scripts" / "toolchain.py").read_text(encoding="utf-8")
    downloader = (ROOT / "scripts" / "build_toolchain_wheelhouse.py").read_text(encoding="utf-8")

    for name, source in (
        ("bootstrap.py", bootstrap),
        ("toolchain.py", toolchain),
        ("build_toolchain_wheelhouse.py", downloader),
    ):
        assert "tkinter" not in source.lower(), f"{name} enthält noch Tkinter im unterstützten Startpfad"

    assert '"videobatch_fast.qt_phase3"' in bootstrap
    assert '"QT_QPA_PLATFORM": "wayland"' in bootstrap
    assert "KDialogProgress" in bootstrap
    assert "kdialog" in bootstrap
    assert "from PySide6 import QtCore,QtGui,QtWidgets" in toolchain
    assert '"--yesno"' in downloader
    assert "kdialog" in downloader


def test_qt_phase3_owns_ready_lock_and_clean_shutdown_contract() -> None:
    source = (SRC / "videobatch_fast" / "qt_phase3.py").read_text(encoding="utf-8")
    required = (
        'os.environ.setdefault("QT_QPA_PLATFORM", "wayland")',
        "prepare_gui_environment()",
        "ApplicationLock().acquire()",
        "request_existing_instance_focus()",
        "signal_ui_ready()",
        "app.platformName()",
        "RUNTIME.mark_clean_shutdown()",
        "VIDEOBATCH_SAFE_MODE",
    )
    for token in required:
        assert token in source, f"Qt-Startvertrag fehlt: {token}"


def test_wayland_startup_sources_compile() -> None:
    sources = (
        ROOT / "scripts" / "bootstrap.py",
        ROOT / "scripts" / "toolchain.py",
        ROOT / "scripts" / "build_toolchain_wheelhouse.py",
        SRC / "videobatch_fast" / "qt_phase3.py",
    )
    for source in sources:
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(source)],
            cwd=ROOT,
            env={"PYTHONPYCACHEPREFIX": "/tmp/videobatch-tk-free-pycache"},
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, f"{source}: {result.stderr}"
