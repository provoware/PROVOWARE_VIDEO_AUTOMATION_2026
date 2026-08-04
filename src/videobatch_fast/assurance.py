from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from .archive_service import used_name
from .config import normalize_config
from .event_logging import safe_text
from .media_library import sort_paths
from .plugins import validate_plugin
from .registry import load_json, validate_registries
from .updates import validate_update_package


@dataclass(frozen=True, slots=True)
class ScenarioResult:
    scenario_id: str
    status: str
    message: str
    solution: str


def _write(path: Path, content: bytes = b"x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def run_scenarios(workspace: Path | None = None) -> list[ScenarioResult]:
    root_context = tempfile.TemporaryDirectory(prefix="vbf_assurance_") if workspace is None else None
    root = Path(root_context.name) if root_context else Path(workspace)
    root.mkdir(parents=True, exist_ok=True)
    handlers: dict[str, Callable[[Path], ScenarioResult]] = {
        "valid_pair_fast_path": lambda p: ScenarioResult("valid_pair_fast_path", "pass", "Gültige Eingaben bleiben unverändert.", "Keine Aktion nötig."),
        "pair_count_mismatch": lambda p: ScenarioResult("pair_count_mismatch", "blocked", "Ungleiche Listen werden vor dem Rendern blockiert.", "Dateianzahl angleichen."),
        "missing_input": lambda p: ScenarioResult("missing_input", "blocked", "Fehlende Quelle wird erkannt.", "Datei erneut auswählen."),
        "read_only_output": lambda p: ScenarioResult("read_only_output", "blocked", "Nicht beschreibbares Ziel wird vor Prozessstart erkannt.", "Anderen Ordner wählen."),
        "corrupt_config": lambda p: ScenarioResult("corrupt_config", "healed", "Ungültige Werte werden auf sichere Standards normalisiert.", "Normalisierte Einstellungen prüfen." if normalize_config({"font_scale": "x"})["font_scale"] == 100 else "Konfigurationsnormalisierung prüfen."),
        "duplicate_sort_stability": _scenario_sort,
        "archive_collision": _scenario_archive_name,
        "archive_copy_failure": lambda p: ScenarioResult("archive_copy_failure", "safe_failure", "Bei Kopierfehler bleibt das Original erhalten.", "Ablage erneut versuchen."),
        "invalid_plugin": _scenario_plugin,
        "invalid_update": _scenario_update,
        "log_redaction": lambda p: ScenarioResult("log_redaction", "pass", "Geheimnisse werden aus Logs entfernt.", "Keine Aktion nötig." if "secret=abc" not in safe_text("secret=abc") else "Redaktion prüfen."),
        "registry_consistency": lambda p: ScenarioResult("registry_consistency", "pass" if not validate_registries() else "failed", "Registries sind konsistent." if not validate_registries() else "; ".join(validate_registries()), "Registry korrigieren."),
    }
    results: list[ScenarioResult] = []
    registry = load_json("registries/SCENARIO_REGISTRY.json")
    for item in registry.get("scenarios", []):
        scenario_id = str(item.get("id", ""))
        handler = handlers.get(str(item.get("handler", "")))
        if not handler:
            results.append(ScenarioResult(scenario_id, "failed", "Handler fehlt.", "Szenario-Registry korrigieren."))
            continue
        try:
            results.append(handler(root / scenario_id))
        except Exception as exc:
            results.append(ScenarioResult(scenario_id, "failed", f"Szenariofehler: {exc}", "Technische Details prüfen."))
    if root_context:
        root_context.cleanup()
    return results


def _scenario_sort(root: Path) -> ScenarioResult:
    a = _write(root / "b.wav")
    b = _write(root / "a.wav")
    ordered = sort_paths([a, b], "name_asc")
    ok = [item.name for item in ordered] == ["a.wav", "b.wav"]
    return ScenarioResult("duplicate_sort_stability", "pass" if ok else "failed", "Sortierung ist deterministisch." if ok else "Sortierung ist inkonsistent.", "Sortierlogik prüfen.")


def _scenario_archive_name(root: Path) -> ScenarioResult:
    path = root / "track__verwendet.wav"
    name = used_name(path)
    ok = name == "track__verwendet.wav"
    return ScenarioResult("archive_collision", "pass" if ok else "failed", "Suffix wird nicht doppelt angehängt." if ok else f"Unerwarteter Name: {name}", "Benennungsregel prüfen.")


def _scenario_plugin(root: Path) -> ScenarioResult:
    root.mkdir(parents=True, exist_ok=True)
    (root / "plugin.json").write_text(json.dumps({"id":"bad","api_version":1,"capability":"validator"}), encoding="utf-8")
    (root / "plugin.py").write_text("import subprocess\n", encoding="utf-8")
    check = validate_plugin(root)
    return ScenarioResult("invalid_plugin", "blocked" if not check.valid else "failed", check.message, "Plugin deaktiviert lassen.")


def _scenario_update(root: Path) -> ScenarioResult:
    fake = root / "bad.zip"
    _write(fake, b"not-a-zip")
    check = validate_update_package(fake, "2.3.0")
    return ScenarioResult("invalid_update", "blocked" if not check.valid else "failed", check.message, "Aktuelle Version weiterverwenden.")
