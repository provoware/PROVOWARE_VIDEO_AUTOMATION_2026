from __future__ import annotations

import json
import platform
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .os_sandbox import probe_sandbox_support
from .registry import PROJECT_ROOT

HOST_DIR = Path(__file__).resolve().parent
LAUNCHER = PROJECT_ROOT / "scripts" / "plugin_sandbox_launcher.sh"
IMPLEMENTED_CAPABILITIES = frozenset({"validator"})


@dataclass(frozen=True, slots=True)
class PluginRunResult:
    success: bool
    message: str
    result: bool | None = None
    isolated: bool = False


def sandbox_command(plugin_dir: Path, capability: str, payload: dict, root: Path) -> list[str]:
    if capability not in IMPLEMENTED_CAPABILITIES:
        raise ValueError(f"Nicht implementierte Plugin-Fähigkeit ist gesperrt: {capability}")
    if platform.system() != "Linux":
        raise RuntimeError("Echte Plugin-Isolierung steht nur unter Linux zur Verfügung.")
    unshare = shutil.which("unshare")
    if not unshare:
        raise RuntimeError("unshare fehlt; Plugin-Ausführung bleibt sicher deaktiviert.")
    if not LAUNCHER.is_file():
        raise RuntimeError("Sandbox-Launcher fehlt; Plugin-Ausführung bleibt sicher deaktiviert.")
    status = probe_sandbox_support()
    if not status.available:
        raise RuntimeError(status.message)
    python_path = Path(sys.executable).resolve()
    return [
        unshare,
        "--user",
        "--map-root-user",
        "--net",
        "--pid",
        "--mount",
        "--fork",
        "bash",
        str(LAUNCHER),
        str(root),
        str(python_path),
        str(HOST_DIR),
        str(Path(plugin_dir).resolve()),
        capability,
        json.dumps(payload, ensure_ascii=False),
    ]


def run_plugin_in_sandbox(plugin_dir: Path, capability: str, payload: dict, timeout: int = 5) -> PluginRunResult:
    with tempfile.TemporaryDirectory(prefix="videobatch_plugin_root_") as temp_root:
        try:
            command = sandbox_command(plugin_dir, capability, payload, Path(temp_root))
        except (RuntimeError, ValueError) as exc:
            return PluginRunResult(False, str(exc), isolated=False)
        try:
            completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
        except subprocess.TimeoutExpired:
            return PluginRunResult(False, "Plugin-Sandbox hat das Zeitlimit überschritten.", isolated=True)
    try:
        response = json.loads(completed.stdout.strip() or "{}")
    except json.JSONDecodeError:
        return PluginRunResult(
            False,
            completed.stderr.strip() or "Plugin-Sandbox lieferte keine gültige Antwort.",
            isolated=True,
        )
    if not response.get("ok"):
        message = str(response.get("error", "Plugin-Sandbox fehlgeschlagen."))
        if completed.stderr.strip():
            message = f"{message} · {completed.stderr.strip()[-1000:]}"
        return PluginRunResult(False, message, isolated=True)
    return PluginRunResult(
        True,
        "Plugin wurde in User-, Netzwerk-, PID- und Mount-Namespace mit Chroot und Seccomp ausgeführt.",
        bool(response.get("result")),
        True,
    )
