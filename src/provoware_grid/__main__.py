"""Check the reusable layout contract without Qt, a browser or network."""
from __future__ import annotations

import argparse
import json
from .core import evaluate_matrix

SIZES = [(800, 600), (1024, 768), (1280, 720), (1366, 768),
         (1920, 1080), (2560, 1440)]


def main() -> int:
    parser = argparse.ArgumentParser(description="PROVOWARE-Raster: Layoutmatrix prüfen")
    parser.add_argument("--width", type=int, help="Fenster-Inhaltsbreite in Pixeln")
    parser.add_argument("--height", type=int, help="Fenster-Inhaltshöhe in Pixeln")
    parser.add_argument("--zoom", type=int, action="append", help="Schriftgröße in Prozent")
    args = parser.parse_args()
    if (args.width is None) != (args.height is None):
        parser.error("--width und --height müssen gemeinsam angegeben werden")
    sizes = [(args.width, args.height)] if args.width is not None else SIZES
    results = evaluate_matrix(sizes, args.zoom or (80, 100, 110, 125, 150, 175, 200))
    payload = {
        "reference": {"width": 800, "height": 600, "columns": 120, "rows": 80},
        "sample_count": len(results),
        "type": "layout_rule_matrix_not_browser_visual_proof",
        "all_readable": all(item["minimum_width_preserved"] for item in results),
        "samples": results,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["all_readable"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
