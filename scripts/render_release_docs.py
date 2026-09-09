#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from diagnostics.release_readiness.generate_from_evidence import (  # noqa: E402
    EvidenceContractError,
    release_files_block,
    release_status_block,
    render_readme,
    validate,
)

EVIDENCE_RELATIVE = Path("diagnostics/release_readiness/RELEASE_EVIDENCE.json")


def _object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name}: JSON-Wurzel ist kein Objekt")
    return value


def _evidence(root: Path) -> dict[str, Any]:
    value = _object(root / EVIDENCE_RELATIVE)
    validate(value)
    return value


def render(root: Path = ROOT) -> dict[Path, str]:
    value = _evidence(root)
    readme_path = root / "README.md"
    readme = render_readme(value, readme_path.read_text(encoding="utf-8"))
    status = release_status_block(value) + "\n\n" + release_files_block(value) + "\n"
    return {
        readme_path: readme,
        root / "STATUS.md": status,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Leitet README und STATUS aus der kanonischen Release-Evidenz ab."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        rendered = render()
        stale = [
            path
            for path, text in rendered.items()
            if path.read_text(encoding="utf-8") != text
        ]
        if args.check and stale:
            raise ValueError(
                "abgeleitete Datei ist veraltet: "
                + ", ".join(path.name for path in stale)
            )
        if args.write:
            for path, text in rendered.items():
                path.write_text(text, encoding="utf-8")
    except (
        OSError,
        KeyError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
        EvidenceContractError,
    ) as exc:
        print(
            "DOKUMENTSTATUS BLOCKIERT\n"
            f"Ursache: {exc}\n"
            "Auswirkung: README und Status sind nicht freigabefähig.\n"
            "Schutz: Dateien bleiben unverändert.\n"
            "Lösung: Kanonische Release-Evidenz korrigieren.\n"
            "Alternative: Kandidat als nicht freigegeben belassen."
        )
        return 1
    print("DOKUMENTSTATUS GESCHRIEBEN" if args.write else "DOKUMENTSTATUS BESTANDEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
