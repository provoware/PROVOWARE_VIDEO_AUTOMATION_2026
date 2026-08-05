#!/usr/bin/env python3
"""Generate a read-only, fail-closed release readiness dashboard."""
from __future__ import annotations

import argparse
import html
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from engine import (
    EvidenceError,
    analyze,
    fetch_github_ci,
    load_ci_snapshot,
    load_evidence,
    result_document,
    unchanged_findings,
)

OUTPUTS = (
    "RELEASE_READINESS_STATUS.json",
    "RELEASE_READINESS_DASHBOARD.md",
    "RELEASE_READINESS_DASHBOARD.html",
)


def label(status: str) -> str:
    return {"green": "GRÜN", "yellow": "GELB", "red": "ROT", "pass": "PASS", "open": "OFFEN", "fail": "FEHLER", "unknown": "UNBEKANNT", "running": "LÄUFT"}.get(status, status.upper())


def markdown(result: Mapping[str, Any]) -> str:
    release, summary = result["release"], result["summary"]
    lines = [
        "# Release-Bereitschafts-Dashboard", "",
        f"**Status:** {label(str(result['overall_status']))}",
        f"**Bereitschaft:** {result['readiness_percent']} %",
        f"**Release:** {release.get('name') or '—'} {release.get('version') or '—'} · Kanal `{release.get('channel') or '—'}`",
        f"**Quellcommit:** `{release.get('source_sha') or 'nicht angegeben'}`",
        f"**Erzeugt:** {result['generated_at']}", "",
        f"Gates: {summary['gates_passed']}/{summary['gates_total']} bestanden · Fehler: {summary['errors']} · Warnungen: {summary['warnings']}", "",
        "## Stable-Gates", "", "| Status | Gate | Begründung | Quelle |", "|---|---|---|---|",
    ]
    for gate in result["gates"]:
        lines.append(f"| {label(gate['status'])} | {gate['label']} | {gate['detail']} | `{gate['source']}` |")
    lines.extend(["", "## Widersprüche und Hinweise", ""])
    if result["findings"]:
        lines.extend(f"- **{item['severity'].upper()} · {item['code']}** — {item['message']}" for item in result["findings"])
    else:
        lines.append("Keine Widersprüche erkannt.")
    lines.extend(["", "## Fail-closed-Regel", "", "`GRÜN` wird nur ausgegeben, wenn alle Pflicht-Gates PASS sind, keine widersprüchlichen Quellen existieren und die Eingabedateien unverändert geblieben sind."])
    return "\n".join(lines) + "\n"


def html_report(result: Mapping[str, Any]) -> str:
    release, summary = result["release"], result["summary"]
    status = str(result["overall_status"])
    css_status = {"green": "ok", "yellow": "warn", "red": "bad"}.get(status, "unknown")
    rows = "".join(
        "<tr>"
        f"<td><span class='pill {html.escape(gate['status'])}'>{html.escape(label(gate['status']))}</span></td>"
        f"<th scope='row'>{html.escape(gate['label'])}</th>"
        f"<td>{html.escape(gate['detail'])}</td>"
        f"<td><code>{html.escape(gate['source'])}</code></td></tr>"
        for gate in result["gates"]
    )
    findings = result["findings"]
    finding_html = "<p>Keine Widersprüche erkannt.</p>" if not findings else "<ul>" + "".join(
        f"<li class='{html.escape(item['severity'])}'><strong>{html.escape(item['code'])}</strong> — {html.escape(item['message'])}</li>" for item in findings
    ) + "</ul>"
    return f"""<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Release-Bereitschaft · {html.escape(str(release.get('version') or 'unbekannt'))}</title>
<style>
:root{{color-scheme:light dark;font-family:system-ui,sans-serif}}body{{margin:0;background:#11151b;color:#f4f6f8;line-height:1.45}}main{{width:min(1180px,calc(100% - 2rem));margin:1rem auto 3rem}}header,section{{background:#1b222c;border:1px solid #3a4656;border-radius:14px;padding:1rem 1.2rem;margin-bottom:1rem}}h1,h2{{margin-top:0}}.summary{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:.8rem}}.card{{background:#111821;border:1px solid #3a4656;border-radius:10px;padding:.8rem}}.status{{border-left:10px solid #8291a6}}.status.ok{{border-left-color:#32d583}}.status.warn{{border-left-color:#fdb022}}.status.bad{{border-left-color:#f97066}}.value{{font-size:1.55rem;font-weight:800}}table{{width:100%;border-collapse:collapse}}th,td{{border-bottom:1px solid #3a4656;padding:.65rem;text-align:left;vertical-align:top}}.pill{{display:inline-block;border-radius:999px;padding:.2rem .55rem;font-weight:800;background:#566477}}.pill.pass{{background:#067647}}.pill.open,.pill.running{{background:#8a5b00}}.pill.fail{{background:#b42318}}.error{{color:#fda29b}}.warning{{color:#fec84b}}code{{overflow-wrap:anywhere}}@media(max-width:760px){{table,thead,tbody,tr,th,td{{display:block}}thead{{position:absolute;left:-9999px}}tr{{border-bottom:2px solid #566477;padding:.5rem 0}}td,th{{border:0}}}}@media print{{body,header,section,.card{{background:white;color:black;border-color:#555}}}}
</style></head><body><main>
<header class="status {css_status}"><h1>Release-Bereitschafts-Dashboard</h1><p class="value">{html.escape(label(status))} · {result['readiness_percent']} %</p><p>{html.escape(str(release.get('name') or '—'))} {html.escape(str(release.get('version') or '—'))} · Kanal <code>{html.escape(str(release.get('channel') or '—'))}</code></p><p>Quellcommit: <code>{html.escape(str(release.get('source_sha') or 'nicht angegeben'))}</code> · Erzeugt: {html.escape(result['generated_at'])}</p></header>
<section class="summary" aria-label="Zusammenfassung"><div class="card"><div>Bestandene Gates</div><div class="value">{summary['gates_passed']}/{summary['gates_total']}</div></div><div class="card"><div>Fehler</div><div class="value">{summary['errors']}</div></div><div class="card"><div>Warnungen</div><div class="value">{summary['warnings']}</div></div><div class="card"><div>Eingaben unverändert</div><div class="value">{'JA' if result['read_only_inputs_verified'] else 'NEIN'}</div></div></section>
<section><h2>Stable-Gates</h2><div style="overflow-x:auto"><table><thead><tr><th>Status</th><th>Gate</th><th>Begründung</th><th>Quelle</th></tr></thead><tbody>{rows}</tbody></table></div></section>
<section><h2>Widersprüche und Hinweise</h2>{finding_html}</section><section><h2>Fail-closed-Regel</h2><p>GRÜN wird nur bei vollständigen PASS-Gates, widerspruchsfreien Quellen und unveränderten Eingaben ausgegeben.</p></section>
</main></body></html>"""


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def generate(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    output = args.output_dir.resolve() if args.output_dir.is_absolute() else (root / args.output_dir).resolve()
    documents, paths, hashes = load_evidence(root)
    if args.ci_file:
        ci_path = args.ci_file if args.ci_file.is_absolute() else root / args.ci_file
        ci = load_ci_snapshot(ci_path)
    elif args.github_repository and args.github_sha:
        ci = fetch_github_ci(args.github_repository, args.github_sha, os.environ.get(args.github_token_env))
    else:
        ci = load_ci_snapshot(None)
    findings, gates = analyze(root, documents, ci)
    findings.extend(unchanged_findings(paths, hashes))
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    result = result_document(documents, ci, findings, gates, hashes, args.github_sha or os.environ.get("GITHUB_SHA"), generated_at)
    if not args.no_write:
        atomic_write(output / OUTPUTS[0], json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
        atomic_write(output / OUTPUTS[1], markdown(result))
        atomic_write(output / OUTPUTS[2], html_report(result))
        changed = unchanged_findings(paths, hashes)
        if changed:
            findings.extend(changed)
            result = result_document(documents, ci, findings, gates, hashes, args.github_sha or os.environ.get("GITHUB_SHA"), generated_at)
            atomic_write(output / OUTPUTS[0], json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
            atomic_write(output / OUTPUTS[1], markdown(result))
            atomic_write(output / OUTPUTS[2], html_report(result))
    print(f"RELEASE-BEREITSCHAFT {label(result['overall_status'])} · {result['readiness_percent']} % · {result['summary']['errors']} Fehler · {result['summary']['warnings']} Warnungen")
    if not args.no_write:
        print(f"Dashboard: {output}")
    return 2 if result["overall_status"] == "red" else 1 if result["overall_status"] == "yellow" else 0


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description="Erzeugt ein rein lesendes, fail-closed Release-Bereitschafts-Dashboard.")
    value.add_argument("--root", type=Path, default=Path.cwd())
    value.add_argument("--output-dir", type=Path, default=Path("build/release-readiness"))
    value.add_argument("--ci-file", type=Path)
    value.add_argument("--github-repository")
    value.add_argument("--github-sha")
    value.add_argument("--github-token-env", default="GITHUB_TOKEN")
    value.add_argument("--no-write", action="store_true")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    try:
        return generate(parser().parse_args(argv))
    except (EvidenceError, OSError) as exc:
        print(f"RELEASE-BEREITSCHAFT ROT · {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
