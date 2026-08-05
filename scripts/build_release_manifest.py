#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from release_file_contract import included_release_file
from videobatch_fast.versioning import version_info
from videobatch_fast.visual_approval import (
    approval_fingerprint,
    inspection_manifest_hash,
    verify_visual_approval,
)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "RELEASE_MANIFEST.json"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    files = []
    for path in sorted(ROOT.rglob("*")):
        if not included_release_file(ROOT, path):
            continue
        data = path.read_bytes()
        files.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "size": len(data),
                "sha256": sha256_bytes(data),
                "mode": oct(path.stat().st_mode & 0o777),
            }
        )
    visual_path = ROOT / "VISUAL_INSPECTION_MANIFEST.json"
    visual = (
        json.loads(visual_path.read_text(encoding="utf-8"))
        if visual_path.is_file()
        else {}
    )
    approval = verify_visual_approval(visual, ROOT) if visual else None
    version = version_info()
    payload = {
        "schema_version": 2,
        "name": str(version.get("name", "provoware - videoautomation - 2026")),
        "version": str(version.get("version", "0.0.0")),
        "build": str(version.get("build", version.get("version", "0.0.0"))),
        "channel": str(version.get("channel", "development")),
        "visual_approval": {
            "valid": bool(approval and approval.valid),
            "visual_contract_sha256": (
                inspection_manifest_hash(visual) if visual else ""
            ),
            "approval_sha256": approval_fingerprint(visual) if visual else "",
            "key_id": approval.key_id if approval else "",
        },
        "file_count": len(files),
        "files": files,
    }
    MANIFEST.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        f"RELEASE-MANIFEST ERZEUGT · {len(files)} Dateien · "
        f"{payload['channel']} · visuelle Freigabe "
        f"{payload['visual_approval']['valid']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
