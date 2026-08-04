from __future__ import annotations

import ast
import json
from dataclasses import dataclass
from pathlib import Path

from .plugin_signing import quarantine_plugin, verify_plugin_signature
from .registry import PROJECT_ROOT, load_json


@dataclass(frozen=True, slots=True)
class PluginCheck:
    path: Path
    valid: bool
    plugin_id: str
    message: str
    signed: bool = False
    key_id: str = ""
    capability: str = ""
    quarantined_to: str = ""
    version: str = "0.0.0"
    payload_sha256: str = ""


def validate_plugin(directory: Path) -> PluginCheck:
    directory = Path(directory)
    manifest_path = directory / "plugin.json"
    code_path = directory / "plugin.py"
    if not manifest_path.is_file() or not code_path.is_file():
        return PluginCheck(directory, False, "unknown", "plugin.json oder plugin.py fehlt.")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return PluginCheck(directory, False, "unknown", f"Manifest ist ungültig: {exc}")
    plugin_id = str(manifest.get("id", "unknown"))
    capability = str(manifest.get("capability", ""))
    version = str(manifest.get("version", "0.0.0") or "0.0.0")
    policy = load_json("registries/PLUGIN_REGISTRY.json")
    if int(manifest.get("api_version", 0) or 0) != int(policy.get("api_version", 1)):
        return PluginCheck(directory, False, plugin_id, "API-Version ist nicht kompatibel.", capability=capability, version=version)
    implemented = set(policy.get("implemented_capabilities", policy.get("allowed_capabilities", [])))
    if capability not in implemented:
        reason = policy.get("disabled_capabilities", {}).get(capability, "Plugin-Fähigkeit ist nicht implementiert oder nicht erlaubt.")
        return PluginCheck(directory, False, plugin_id, str(reason), capability=capability, version=version)
    try:
        tree = ast.parse(code_path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError) as exc:
        return PluginCheck(directory, False, plugin_id, f"Plugin-Code ist ungültig: {exc}", capability=capability, version=version)
    forbidden = set(policy.get("forbidden_imports", []))
    forbidden_calls = {"__import__", "eval", "exec", "compile", "open", "input", "breakpoint"}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import):
                names = {alias.name.split(".")[0] for alias in node.names}
            else:
                names = {str(node.module or "").split(".")[0]}
            name = sorted(names & forbidden)[0] if names & forbidden else sorted(names)[0] if names else "unbekannt"
            return PluginCheck(directory, False, plugin_id, f"Validator-Plugins dürfen keine Module importieren: {name}", capability=capability, version=version)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in forbidden_calls:
            return PluginCheck(directory, False, plugin_id, f"Verbotener dynamischer Aufruf: {node.func.id}", capability=capability, version=version)
    signature = verify_plugin_signature(directory)
    if not signature.valid:
        return PluginCheck(directory, False, plugin_id, signature.message, False, signature.key_id, capability, "", version, signature.payload_sha256)
    return PluginCheck(directory, True, plugin_id, "Plugin-Vertrag und Signatur bestanden. Aktivierung benötigt eine Bestätigung.", True, signature.key_id, capability, "", version, signature.payload_sha256)


def scan_plugins(root: Path | None = None, *, quarantine_invalid: bool = False) -> list[PluginCheck]:
    directory = Path(root) if root else PROJECT_ROOT / "plugins"
    if not directory.exists():
        return []
    checks: list[PluginCheck] = []
    for path in sorted(directory.iterdir()):
        if not path.is_dir() or path.name in {"quarantine", "keys"}:
            continue
        check = validate_plugin(path)
        if quarantine_invalid and not check.valid:
            try:
                target = quarantine_plugin(path, check.message, directory / "quarantine")
                check = PluginCheck(check.path, False, check.plugin_id, check.message, check.signed, check.key_id, check.capability, str(target), check.version, check.payload_sha256)
            except OSError as exc:
                check = PluginCheck(check.path, False, check.plugin_id, f"{check.message} Quarantäne fehlgeschlagen: {exc}", check.signed, check.key_id, check.capability, "", check.version, check.payload_sha256)
        checks.append(check)
    return checks
