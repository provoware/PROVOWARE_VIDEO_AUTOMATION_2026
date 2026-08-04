#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Write one Kubuntu matrix status record.")
    parser.add_argument("--os", required=True, dest="os_name")
    parser.add_argument("--session", required=True)
    parser.add_argument("--status", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()

    result = {
        "schema_version": 3,
        "os": args.os_name,
        "session": args.session,
        "status": args.status,
        "run_id": os.environ.get("GITHUB_RUN_ID", "unknown"),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", "unknown"),
        "commit": os.environ.get("GITHUB_SHA", "unknown"),
        "workflow": os.environ.get("GITHUB_WORKFLOW", "unknown"),
        "media_toolchain": load_json(Path("FFMPEG_TOOLCHAIN.json")),
        "package_metrics": load_json(Path("CI_PACKAGE_METRICS.json")),
    }
    output = Path(
        args.output
        or f"matrix-status-{args.os_name}-{args.session}.json"
    )
    output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
