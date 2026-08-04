#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from videobatch_fast.registry import PROJECT_ROOT, load_json
from videobatch_fast.visual_inspection import copy_visual_assets, write_inspection_html, write_inspection_manifest


def main() -> int:
    config = load_json("registries/VISUAL_INSPECTION_REGISTRY.json")
    manifest_path = PROJECT_ROOT / str(config["manifest_output"])
    html_path = PROJECT_ROOT / str(config["html_output"])
    copy_visual_assets(PROJECT_ROOT, html_path.parent)
    write_inspection_manifest(manifest_path, PROJECT_ROOT)
    import json
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    write_inspection_html(html_path, manifest)
    print(f"VISUELLE HTML-PRÜFUNG ERZEUGT · {html_path}")
    print(f"VISUELLES MANIFEST ERZEUGT · {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
