#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from videobatch_fast.command_builder import PROFILES  # noqa: E402
from videobatch_fast.effects import TRANSITIONS, VISUAL_EFFECTS  # noqa: E402
from videobatch_fast.quick_modes import QUICK_MODES, automatic_mode_keys, validate_quick_modes  # noqa: E402


def expected_manifest() -> dict:
    modes = []
    for key, spec in QUICK_MODES.items():
        modes.append({
            "id": key,
            "label": spec.label,
            "short_label": spec.short_label,
            "description": spec.description,
            "visual_effect": spec.visual_effect,
            "transition": spec.transition,
            "profile": spec.profile,
            "codec": spec.codec,
            "resolution": spec.resolution,
            "verification": spec.verification,
            "speed_class": spec.speed_class,
            "fallback_mode": spec.fallback_mode,
            "adaptive": spec.adaptive,
            "recommended": spec.recommended,
        })
    return {
        "schema_version": 1,
        "name": "VideoBatch Fast Quick Modes",
        "automatic_mode_count": len(automatic_mode_keys()),
        "safety_contract": {
            "ffmpeg_passes_per_attempt": 1,
            "automatic_retry_limit": 1,
            "source_files_unchanged": True,
            "default_fallback": "maximum_speed",
            "direct_copy_preserved": True,
            "output_verification_required": True,
            "strong_strobe_disabled": True,
        },
        "modes": modes,
    }


def main() -> int:
    errors = validate_quick_modes(VISUAL_EFFECTS, TRANSITIONS, PROFILES)
    manifest_path = ROOT / "QUICK_MODES_MANIFEST.json"
    expected = expected_manifest()
    try:
        actual = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"Schnellmodus-Manifest ist nicht lesbar: {exc}")
        actual = None
    if actual != expected:
        errors.append("QUICK_MODES_MANIFEST.json stimmt nicht mit dem aktiven Modusregister überein.")
    if errors:
        print("SCHNELLMODUS-PRÜFUNG FEHLGESCHLAGEN")
        for item in errors:
            print(f"- {item}")
        return 1
    print(f"SCHNELLMODUS-PRÜFUNG BESTANDEN · {len(automatic_mode_keys())} Automatikmodi · 1 Expertenmodus")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
