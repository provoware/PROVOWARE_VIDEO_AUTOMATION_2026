from __future__ import annotations

import argparse
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

EXPECTED_THEMES = {
    "neon_gravity": "Midnight Blue",
    "acid_paper": "Emerald Tech",
    "toxic_candy": "Violet Pulse",
    "ultraviolet": "Amber Graphite",
}
EXPECTED_FONT_PROFILES = {"compact": 90, "standard": 105, "large": 125}
REQUIRED_CHECKPOINTS = tuple(range(0, 11))


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    design_dir = root / "docs" / "design"
    required = [
        design_dir / MANIFEST_PATH.name,
        design_dir / PLAN_PATH.name,
        design_dir / TOKENS_PATH.name,
        design_dir / REFERENCE_PATH.name,
        design_dir / POSTER_PATH.name,
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

    for key, file_name in (("canonical_reference", REFERENCE_PATH.name), ("manifest_poster", POSTER_PATH.name)):
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
        "Startzeituhr", "RenderProof", "Midnight Blue", "Emerald Tech",
        "Violet Pulse", "Amber Graphite", "Kompakt", "Standard", "Groß",
    ):
        if phrase not in manifest:
            errors.append(f"Manifestbegriff fehlt: {phrase}")

    plan = (design_dir / PLAN_PATH.name).read_text(encoding="utf-8")
    for number in REQUIRED_CHECKPOINTS:
        if f"Checkpoint {number}" not in plan:
            errors.append(f"Checkpoint fehlt: {number}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Prüft das verbindliche VideoBatch-Grafikmanifest.")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()
    errors = validate()
    result = {"status": "pass" if not errors else "fail", "errors": errors}
    if args.json_output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("DESIGN_MANIFEST_OK" if not errors else "DESIGN_MANIFEST_FAILED")
        for error in errors:
            print(f"- {error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
