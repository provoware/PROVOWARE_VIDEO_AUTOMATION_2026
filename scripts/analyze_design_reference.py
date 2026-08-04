#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "resources" / "reference" / "laienmodus_einfach_reference.png"
TARGET = ROOT / "resources" / "reference" / "laienmodus_einfach_analysis.json"


def main() -> int:
    image = Image.open(SOURCE).convert("RGB")
    reduced = image.resize((200, 160), Image.Resampling.LANCZOS).quantize(colors=20).convert("RGB")
    colors = Counter(reduced.get_flattened_data()).most_common(20)
    payload = {
        "schema_version": 1,
        "source": SOURCE.relative_to(ROOT).as_posix(),
        "dimensions": {"width": image.width, "height": image.height},
        "dominant_colors": [
            {"hex": "#%02x%02x%02x" % color, "rgb": list(color), "weight": count}
            for color, count in colors
        ],
        "requirements": {
            "background": "sehr dunkel, leicht oliv-grün",
            "frames": "warm-goldene Kontur",
            "primary_tiles": ["gold", "magenta", "grün", "blau"],
            "hierarchy": ["Titel", "Begrüßung", "Hauptkacheln", "Assistent/Tipps", "Schnellaktionen"],
            "interaction": "große Buttons, klare Hilfetexte, laienoptimierte Assistentenlogik"
        }
    }
    TARGET.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"DESIGNANALYSE ERZEUGT: {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
