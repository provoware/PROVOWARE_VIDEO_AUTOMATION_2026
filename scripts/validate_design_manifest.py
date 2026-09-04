from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESIGN_DIR = ROOT / "docs" / "design"
TOKENS_PATH = DESIGN_DIR / "VIDEOBATCH_DESIGN_TOKENS.json"
MANIFEST_PATH = DESIGN_DIR / "VIDEOBATCH_GRAPHICS_MANIFEST.md"
PLAN_PATH = DESIGN_DIR / "VIDEOBATCH_DESIGN_IMPLEMENTATION_PLAN.md"
REFERENCE_PATH = DESIGN_DIR / "VIDEOBATCH_CANONICAL_UI_REFERENCE.svg"
POSTER_PATH = DESIGN_DIR / "VIDEOBATCH_GRAPHICS_MANIFEST_POSTER.svg"
SHELL_PATHS = (
    ROOT / "src" / "videobatch_fast" / "canonical_ui.py",
    ROOT / "src" / "videobatch_fast" / "canonical_kpi.py",
    ROOT / "src" / "videobatch_fast" / "canonical_kpi_detail_mixin.py",
    ROOT / "src" / "videobatch_fast" / "canonical_kpi_compact_mixin.py",
    ROOT / "src" / "videobatch_fast" / "canonical_shell_contract.py",
    ROOT / "src" / "videobatch_fast" / "canonical_shell_chrome.py",
    ROOT / "src" / "videobatch_fast" / "canonical_shell_workspace.py",
    ROOT / "src" / "videobatch_fast" / "canonical_dashboard_mixin.py",
    ROOT / "src" / "videobatch_fast" / "canonical_help_status_mixin.py",
    ROOT / "src" / "videobatch_fast" / "canonical_window_mixin.py",
    ROOT / "src" / "videobatch_fast" / "canonical_resource_control_mixin.py",
    ROOT / "src" / "videobatch_fast" / "ui_resource_controls_mixin.py",
    ROOT / "src" / "videobatch_fast" / "controlled_runner.py",
    ROOT / "src" / "videobatch_fast" / "execution_control.py",
    ROOT / "src" / "videobatch_fast" / "system_resources.py",
    ROOT / "src" / "videobatch_fast" / "resource_process.py",
    ROOT / "src" / "videobatch_fast" / "window_geometry.py",
)
APP_PATH = ROOT / "src" / "videobatch_fast" / "app.py"

EXPECTED_THEMES = {
    "neon_gravity": "Midnight Blue",
    "acid_paper": "Emerald Tech",
    "toxic_candy": "Violet Pulse",
    "ultraviolet": "Amber Graphite",
}
EXPECTED_FONT_PROFILES = {"compact": 90, "standard": 105, "large": 125}
REQUIRED_CHECKPOINTS = tuple(range(0, 11))
REQUIRED_SHELL_LABELS = (
    "Dashboard",
    "Medien",
    "Queue",
    "Effekte",
    "Scheduler",
    "Vorschau",
    "Diagnose",
    "Einstellungen",
)
REQUIRED_DASHBOARD_ZONES = (
    "Quellen & Projekt",
    "Render Queue",
    "Jobdetails & Vorschau",
    "Startzeituhr",
    "Darstellung",
)
REQUIRED_RESPONSIVE_TOKENS = (
    "dashboard_layout_mode",
    "responsive_column_count",
    "normalize_window_geometry",
    "yscrollcommand",
    "scrollregion",
    "three_columns",
    "two_columns",
    "stacked",
)
REQUIRED_RESOURCE_TOKENS = (
    "PROZESS & FORTSCHRITT",
    "SYSTEMLAST",
    "RESSOURCENLIMITS",
    "CPU auf 50 % begrenzen",
    "RAM_LIMIT_PRESETS_GB",
    "ZRAM",
    "Pausieren",
    "Fortsetzen",
    "total_progress",
    "job_progress",
    "SIGSTOP",
    "SIGCONT",
    "prlimit",
)
REQUIRED_HELP_INTENTS = (
    "Ich möchte …",
    "Erstes Video erstellen",
    "Fehlende Datei beheben",
    "Queuefehler wiederholen",
    "Cache leeren",
    "Update rückgängig machen",
)
REQUIRED_PAGE_BUILDERS = (
    "_build_start_page",
    "_build_media_page",
    "_build_preview_page",
    "_build_modes_page",
    "_build_production_page",
    "_build_help_page",
)
REQUIRED_KPI_STATES = (
    "empty",
    "ready",
    "loading",
    "success",
    "warning",
    "error",
    "disabled",
)
REQUIRED_KPI_ACTIONS = (
    "Medien öffnen",
    "Queue öffnen",
    "Effekte öffnen",
    "Checkpoint 5",
)


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require_values(text: str, values, errors: list[str], message: str) -> None:
    for value in values:
        if value not in text:
            errors.append(message.format(value=value))


def _validate_python_syntax(paths: tuple[Path, ...], root: Path, errors: list[str]) -> None:
    for path in paths:
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            errors.append(f"PYTHON_SYNTAX_UNGUELTIG: {path.relative_to(root)}: {exc}")


def _validate_shell_labels(shell: str, errors: list[str]) -> None:
    _require_values(shell, REQUIRED_SHELL_LABELS, errors, "Shell-Navigation fehlt: {value}")
    _require_values(shell, REQUIRED_DASHBOARD_ZONES, errors, "Dashboard-Zone fehlt: {value}")
    _require_values(shell, REQUIRED_RESPONSIVE_TOKENS, errors, "Responsive Shell-Kopplung fehlt: {value}")
    _require_values(shell, REQUIRED_RESOURCE_TOKENS, errors, "Ressourcen-/Prozessvertrag fehlt: {value}")
    _require_values(shell, REQUIRED_HELP_INTENTS, errors, "Hilfeabsicht fehlt: {value}")
    _require_values(shell, EXPECTED_THEMES.values(), errors, "Shell-Theme fehlt: {value}")
    _require_values(shell, REQUIRED_KPI_ACTIONS, errors, "KPI-Aktion fehlt: {value}")


def _validate_shell_bindings(shell: str, app: str, errors: list[str]) -> None:
    for builder in REQUIRED_PAGE_BUILDERS:
        if f"self.{builder}(" not in shell:
            errors.append(f"Bestehende Funktionsseite nicht eingebunden: {builder}")
    callbacks = (
        "self._new_project",
        "self._add_audio",
        "self._add_media",
        "self._open_settings",
        "self._start",
        "self._choose_directory",
    )
    _require_values(shell, callbacks, errors, "Primäraktion fehlt: {value}")
    for label, value in (("Kompakt", 90), ("Standard", 105), ("Groß", 125)):
        if f'"{label}": {value}' not in shell:
            errors.append(f"Shell-Schriftprofil fehlt: {label}={value}")
    for state in REQUIRED_KPI_STATES:
        if f'"{state}"' not in shell:
            errors.append(f"KPI-Zustand fehlt: {state}")
    _validate_shell_contract_flags(shell, app, errors)


def _validate_shell_contract_flags(shell: str, app: str, errors: list[str]) -> None:
    checks = (
        ("build_kpi_snapshots(" in shell and "self._refresh_kpi_cards()" in shell, "KPI-Karten sind nicht an den realen Zustandsvertrag gebunden"),
        ("CanonicalKpiCompactMixin" in shell and "ShellKpiLink.TButton" in shell, "KPI-Detaildarstellung besitzt keine kompakte responsive Grenze"),
        ("CanonicalResourceControlMixin" in shell and "ControlledBatchRunner" in shell, "Ressourcensteuerung ist nicht an die kanonische Shell gebunden"),
        ("kein automatischer Start" in shell, "Startzeituhr ist nicht eindeutig als deaktiviert gekennzeichnet"),
        ("from .canonical_ui import run_app" in app, "App-Einstieg verwendet nicht die kanonische Shell"),
        ("from .ui import run_app" not in app, "App-Einstieg umgeht die kanonische Shell"),
    )
    for valid, message in checks:
        if not valid:
            errors.append(message)


def _validate_shell(root: Path, errors: list[str]) -> None:
    shell_paths = tuple(root / path.relative_to(ROOT) for path in SHELL_PATHS)
    app_path = root / APP_PATH.relative_to(ROOT)
    shell = "\n".join(path.read_text(encoding="utf-8") for path in shell_paths)
    app = app_path.read_text(encoding="utf-8")
    _validate_python_syntax((*shell_paths, app_path), root, errors)
    _validate_shell_labels(shell, errors)
    _validate_shell_bindings(shell, app, errors)


def validate(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    design_dir = root / "docs" / "design"
    required = [
        design_dir / MANIFEST_PATH.name,
        design_dir / PLAN_PATH.name,
        design_dir / TOKENS_PATH.name,
        design_dir / REFERENCE_PATH.name,
        design_dir / POSTER_PATH.name,
        *(root / path.relative_to(ROOT) for path in SHELL_PATHS),
        root / APP_PATH.relative_to(ROOT),
    ]
    for path in required:
        if not path.is_file():
            errors.append(f"FEHLT: {path.relative_to(root)}")
    if errors:
        return errors

    try:
        tokens = json.loads((design_dir / TOKENS_PATH.name).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"TOKENS_UNGUELTIG: {exc}"]

    if tokens.get("manifest_id") != "VB-GFX-1.0":
        errors.append("Manifest-ID ist nicht VB-GFX-1.0")
    labels = {key: value.get("label") for key, value in tokens.get("themes", {}).items()}
    if labels != EXPECTED_THEMES:
        errors.append(f"Themevertrag weicht ab: {labels!r}")
    if tokens.get("font_profiles") != EXPECTED_FONT_PROFILES:
        errors.append("Schriftprofile müssen exakt 90/105/125 sein")

    for key, file_name in (
        ("canonical_reference", REFERENCE_PATH.name),
        ("manifest_poster", POSTER_PATH.name),
    ):
        expected = str(tokens.get(key, {}).get("sha256", ""))
        path = design_dir / file_name
        if _file_sha256(path) != expected:
            errors.append(f"Referenzintegrität verletzt: {file_name}")
        content = path.read_text(encoding="utf-8")
        if not content.startswith("<svg") or "<rect" not in content or "<text" not in content:
            errors.append(f"SVG-Referenz unvollständig: {file_name}")
        if 'href="http' in content or 'href="https' in content:
            errors.append(f"Externe Referenz unzulässig: {file_name}")

    manifest = (design_dir / MANIFEST_PATH.name).read_text(encoding="utf-8")
    for phrase in (
        "Startzeituhr",
        "RenderProof",
        "Midnight Blue",
        "Emerald Tech",
        "Violet Pulse",
        "Amber Graphite",
        "Kompakt",
        "Standard",
        "Groß",
    ):
        if phrase not in manifest:
            errors.append(f"Manifestbegriff fehlt: {phrase}")

    plan = (design_dir / PLAN_PATH.name).read_text(encoding="utf-8")
    for number in REQUIRED_CHECKPOINTS:
        if f"Checkpoint {number}" not in plan:
            errors.append(f"Checkpoint fehlt: {number}")

    _validate_shell(root, errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prüft das lokale VideoBatch-Designregelwerk für Oberfläche und Untermodule."
    )
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()
    errors = validate()
    result = {"status": "pass" if not errors else "fail", "errors": errors}
    if args.json_output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("DESIGN_REGELWERK_OK" if not errors else "DESIGN_REGELWERK_FEHLERHAFT")
        for error in errors:
            print(f"- {error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
