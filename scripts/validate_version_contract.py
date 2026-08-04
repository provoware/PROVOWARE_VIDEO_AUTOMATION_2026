#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CURRENT_JSON_FILES = (
    "TOOLCHAIN_CONTRACT.json",
    "registries/UI_BLUEPRINT.json",
    "registries/UI_COMPONENT_REGISTRY.json",
    "registries/VISUAL_INSPECTION_REGISTRY.json",
    "registries/PLUGIN_APPROVAL_REGISTRY.json",
    "registries/VISUAL_REGRESSION_REGISTRY.json",
    "registries/VISUAL_APPROVAL_REGISTRY.json",
    "VISUAL_INSPECTION_MANIFEST.json",
    "QUALITY_ENVIRONMENT_STATUS.json",
)


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON-Wurzel ist kein Objekt: {path.name}")
    return value


def _pep440(build: str) -> str:
    stable = re.fullmatch(r"\d+\.\d+\.\d+", build)
    if stable:
        return build
    candidate = re.fullmatch(r"(\d+\.\d+\.\d+)-rc(\d+)", build)
    if candidate:
        return f"{candidate.group(1)}rc{candidate.group(2)}"
    raise ValueError(f"Buildidentität ist ungültig: {build}")


def validate(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    try:
        version = _json(root / "VERSION.json")
        build = str(version.get("build", ""))
        if version.get("version") != build:
            errors.append("VERSION.json: version und build unterscheiden sich.")
        expected_pep440 = _pep440(build)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return [f"VERSION.json ist ungültig: {exc}"]

    try:
        pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append(f"pyproject.toml ist unlesbar: {exc}")
    else:
        match = re.search(r'(?m)^version\s*=\s*"([^"]+)"\s*$', pyproject)
        actual = match.group(1) if match else ""
        if actual != expected_pep440:
            errors.append(f"pyproject.toml: erwartet {expected_pep440}, gefunden {actual or 'fehlend'}.")

    for relative in CURRENT_JSON_FILES:
        path = root / relative
        try:
            data = _json(path)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"{relative} ist unlesbar: {exc}")
            continue
        candidates = [data.get("version"), data.get("build"), data.get("baseline_version"), data.get("release_target")]
        present = [str(value) for value in candidates if value not in {None, ""}]
        if present and any(value != build for value in present):
            errors.append(f"{relative}: Buildbezug weicht ab: {', '.join(present)}; erwartet {build}.")

    contract = root / "TOOLCHAIN_CONTRACT.json"
    try:
        contract_data = _json(contract)
        contract_id = str(contract_data.get("contract_id", ""))
        release_target = str(contract_data.get("release_target", ""))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        contract_id = ""
        release_target = ""
    if build not in contract_id:
        errors.append("TOOLCHAIN_CONTRACT.json: contract_id enthält die Buildidentität nicht.")
    if release_target != build:
        errors.append("TOOLCHAIN_CONTRACT.json: release_target weicht vom Build ab.")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("VERSIONSKONSISTENZ: BLOCKIERT")
        for error in errors:
            print(f"✕ {error}")
        return 1
    print("VERSIONSKONSISTENZ: BESTANDEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
