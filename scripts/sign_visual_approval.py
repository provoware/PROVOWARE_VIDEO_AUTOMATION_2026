#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from videobatch_fast.registry import PROJECT_ROOT
from videobatch_fast.versioning import build_label
from videobatch_fast.visual_approval import sign_visual_approval, verify_visual_approval
from videobatch_fast.visual_inspection import write_inspection_html


def main() -> int:
    parser = argparse.ArgumentParser(description="Signiert oder prüft die manuelle visuelle Desktop-Abnahme.")
    parser.add_argument("--manifest", type=Path, default=PROJECT_ROOT / "VISUAL_INSPECTION_MANIFEST.json")
    parser.add_argument("--reviewer", default="")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if args.verify:
        result = verify_visual_approval(manifest, PROJECT_ROOT)
        print(f"VISUELLE FREIGABE: {result.status} · {result.message}")
        return 0 if result.valid else 1
    if not args.reviewer.strip():
        parser.error("--reviewer ist zum Signieren erforderlich")
    approval = sign_visual_approval(
        args.manifest,
        reviewer=args.reviewer,
        build_id=build_label(),
        project_root=PROJECT_ROOT,
    )
    updated = json.loads(args.manifest.read_text(encoding="utf-8"))
    write_inspection_html(PROJECT_ROOT / "visual_inspection" / "index.html", updated)
    payload = approval["payload"]
    print(f"VISUELLE FREIGABE SIGNIERT · {payload['build_id']} · {payload['reviewer']} · {payload['approved_at']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
