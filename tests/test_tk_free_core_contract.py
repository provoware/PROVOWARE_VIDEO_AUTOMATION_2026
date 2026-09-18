from __future__ import annotations

import importlib.util
import queue
import subprocess
import sys
from pathlib import Path
from unittest import mock


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


def _load_bootstrap_module():
    path = ROOT / "scripts" / "bootstrap.py"
    spec = importlib.util.spec_from_file_location("videobatch_test_bootstrap", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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

    assert '[str(python), "-m", "videobatch_fast"]' in bootstrap
    assert '"videobatch_fast.qt_phase3"' not in bootstrap
    assert '"QT_QPA_PLATFORM": "wayland"' in bootstrap
    assert "KDialogProgress" in bootstrap
    assert "kdialog" in bootstrap
    assert "from PySide6 import QtCore" in toolchain
    assert "QtCore.qVersion()" in toolchain
    assert '"--yesno"' in downloader
    assert "kdialog" in downloader


def test_canonical_module_entrypoint_routes_to_qt_wayland() -> None:
    source = (SRC / "videobatch_fast" / "__main__.py").read_text(encoding="utf-8")
    assert "from .qt_phase3 import main" in source
    assert "from .app import main" not in source


def test_supported_launchers_converge_on_one_canonical_entrypoint() -> None:
    starten = (ROOT / "STARTEN.sh").read_text(encoding="utf-8")
    start = (ROOT / "start.sh").read_text(encoding="utf-8")
    videobatch = (ROOT / "videobatch.sh").read_text(encoding="utf-8")
    debug_launcher = (ROOT / "scripts" / "debug_launcher.py").read_text(encoding="utf-8")
    bootstrap = (ROOT / "scripts" / "bootstrap.py").read_text(encoding="utf-8")

    assert 'exec "$BOOTSTRAP_PYTHON" "$DEBUG_LAUNCHER" "$@"' in starten
    assert 'exec "$ROOT_DIR/STARTEN.sh"' in start
    assert 'start_application() {\n  exec "$ROOT_DIR/STARTEN.sh"\n}' in videobatch
    assert 'str(ROOT / "scripts" / "bootstrap.py")' in debug_launcher
    assert '[str(python), "-m", "videobatch_fast"]' in bootstrap

    supported_sources = "\n".join((starten, start, debug_launcher, bootstrap))
    assert "canonical_ui" not in supported_sources
    assert "videobatch_fast.app" not in supported_sources
    assert "videobatch_fast.qt_phase3" not in bootstrap


def test_default_videobatch_start_has_no_tk_preflight() -> None:
    source = (ROOT / "videobatch.sh").read_text(encoding="utf-8")
    start_function = source.split("start_application() {", 1)[1].split("}", 1)[0]
    assert "require_system" not in start_function
    assert "tkinter" not in start_function
    assert "STARTEN.sh" in start_function


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


def test_bootstrap_retries_failed_normal_qt_start_in_safe_mode(tmp_path: Path) -> None:
    bootstrap = _load_bootstrap_module()
    events: queue.Queue[tuple[str, object]] = queue.Queue()
    sink = bootstrap.EventSink(events, tmp_path / "bootstrap.log")
    lock_handle = (tmp_path / "bootstrap.lock").open("a+", encoding="utf-8")
    attempts: list[bool] = []

    def fake_launch(_python, _environment, _sink, *, safe_mode: bool, timeout: float):
        attempts.append(safe_mode)
        assert timeout == 2.0
        if not safe_mode:
            raise bootstrap.BootstrapFailure("kontrollierter Normalstart-Fehler vor UI_READY")
        return 4321, True

    contract = {
        "policy": {
            "maximum_automatic_repair_attempts": 2,
            "application_ready_timeout_seconds": 2,
        }
    }
    with (
        mock.patch.object(bootstrap, "acquire_lock", return_value=lock_handle),
        mock.patch.object(bootstrap, "verify_project"),
        mock.patch.object(bootstrap, "load_startup_contract", return_value=contract),
        mock.patch.object(bootstrap, "install_user_launchers"),
        mock.patch.object(bootstrap, "ensure_runtime", return_value=(Path(sys.executable), False)),
        mock.patch.object(bootstrap, "run_startup_probe", return_value={"status": "ready"}),
        mock.patch.object(bootstrap, "launch_application", side_effect=fake_launch),
    ):
        bootstrap.worker(sink)

    assert attempts == [False, True]
    received = []
    while not events.empty():
        received.append(events.get_nowait())
    assert ("done", (4321, True)) in received
    log = (tmp_path / "bootstrap.log").read_text(encoding="utf-8")
    assert "NORMAL START FAILED" in log
    assert "kontrollierter Normalstart-Fehler vor UI_READY" in log


def test_wayland_startup_sources_compile() -> None:
    sources = (
        ROOT / "scripts" / "bootstrap.py",
        ROOT / "scripts" / "toolchain.py",
        ROOT / "scripts" / "build_toolchain_wheelhouse.py",
        SRC / "videobatch_fast" / "qt_phase3.py",
        SRC / "videobatch_fast" / "__main__.py",
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
