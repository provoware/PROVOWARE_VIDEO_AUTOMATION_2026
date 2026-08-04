#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
README_START = "<!-- release-status:start -->"
README_END = "<!-- release-status:end -->"


def _object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name}: JSON-Wurzel ist kein Objekt")
    return value


def _sources(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    version = _object(root / "VERSION.json")
    status = _object(root / "DEVELOPMENT_STATUS.json")
    report_name = str(status.get("approved_quality_report", ""))
    report = _object(root / report_name)
    build = str(version.get("build", ""))
    if status.get("version") != build or report.get("version") != build:
        raise ValueError("Versionsbezug von Status oder Qualitätsbericht weicht von VERSION.json ab")
    if report.get("status") != "passed":
        raise ValueError("Der benannte Qualitätsbericht ist nicht freigegeben")
    return version, status, report


def _release_block(version: dict[str, Any], status: dict[str, Any], report: dict[str, Any]) -> str:
    tests = report["tests"]
    blockers = status.get("stable_blockers", [])
    gate_lines = "\n".join(f"- {item}" for item in blockers) or "- keine"
    line_coverage = f"{tests['line_coverage_percent']:.2f}".replace(".", ",")
    branch_coverage = f"{tests['branch_coverage_percent']:.2f}".replace(".", ",")
    return f"""{README_START}
# {version['name']} · {version['build']}

**Kanal:** {version['channel']}
**Freigegebener Qualitätsbericht:** `{status['approved_quality_report']}`

- {tests['passed']}/{tests['passed']} automatisierte Tests bestanden
- {line_coverage} % Zeilenabdeckung
- {branch_coverage} % Zweigabdeckung
- {tests['visual_scenarios']} visuelle Szenarien bestanden

### Offene Stable-Gates

{gate_lines}
{README_END}"""


def _replace_block(text: str, block: str) -> str:
    start, end = text.find(README_START), text.find(README_END)
    if start < 0 or end < start:
        raise ValueError("README-Markierungen fehlen oder sind vertauscht")
    return text[:start] + block + text[end + len(README_END) :]


def render(root: Path = ROOT) -> dict[Path, str]:
    version, status, report = _sources(root)
    block = _release_block(version, status, report)
    readme = _replace_block((root / "README.md").read_text(encoding="utf-8"), block)
    return {root / "README.md": readme, root / "STATUS.md": block + "\n"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Leitet README und Status aus freigegebenen Daten ab.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        rendered = render()
        stale = [path for path, text in rendered.items() if path.read_text(encoding="utf-8") != text]
        if args.check and stale:
            raise ValueError("abgeleitete Datei ist veraltet: " + ", ".join(path.name for path in stale))
        if args.write:
            for path, text in rendered.items():
                path.write_text(text, encoding="utf-8")
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"DOKUMENTSTATUS BLOCKIERT\nUrsache: {exc}\nAuswirkung: README und Status sind nicht freigabefähig.\nSchutz: Dateien bleiben unverändert.\nLösung: Statusquelle und Bericht korrigieren.\nAlternative: Kandidat als nicht freigegeben belassen.")
        return 1
    print("DOKUMENTSTATUS GESCHRIEBEN" if args.write else "DOKUMENTSTATUS BESTANDEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
