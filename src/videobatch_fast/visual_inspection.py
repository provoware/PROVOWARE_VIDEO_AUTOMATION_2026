from __future__ import annotations

import html
import json
import shutil
import time
from pathlib import Path
from typing import Any

from .registry import PROJECT_ROOT, load_json
from .visual_approval import inspection_manifest_hash, verify_visual_approval, visual_report_contract_hash


def build_inspection_manifest(project_root: Path | None = None) -> dict[str, Any]:
    root = Path(project_root) if project_root else PROJECT_ROOT
    config = load_json("registries/VISUAL_INSPECTION_REGISTRY.json")
    visual = load_json("registries/VISUAL_REGRESSION_REGISTRY.json")
    report_path = root / str(config.get("visual_report", "diagnostics/visual_regression_latest.json"))
    try:
        report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else {}
    except (OSError, json.JSONDecodeError):
        report = {}
    by_id = {str(item.get("scenario_id")): item for item in report.get("results", []) if isinstance(item, dict)}
    scenarios: list[dict[str, Any]] = []
    for scenario in visual.get("scenarios", []):
        scenario_id = str(scenario.get("id", ""))
        result = by_id.get(scenario_id, {})
        baseline_rel = f"tests/baselines/{scenario_id}.png"
        actual_source_rel = f"tests/visual_actual/{scenario_id}.png"
        diff_source_rel = f"diagnostics/visual_diff/{scenario_id}.png"
        actual_rel = f"visual_inspection/actual/{scenario_id}.png"
        diff_rel = f"visual_inspection/diff/{scenario_id}.png"
        scenarios.append({
            "id": scenario_id,
            "group": str(scenario.get("group", scenario.get("page", "other"))),
            "page": str(scenario.get("page", "dashboard")),
            "state": str(scenario.get("state", "")),
            "width": int(scenario.get("width", 0) or 0),
            "height": int(scenario.get("height", 0) or 0),
            "font_scale": int(scenario.get("font_scale", 100) or 100),
            "required_visible_texts": list(scenario.get("required_visible_texts", [])),
            "required_semantic_colors": list(scenario.get("required_semantic_colors", [])),
            "passed": bool(result.get("passed", False)),
            "artifacts": {
                "baseline": baseline_rel,
                "actual": actual_rel if (root / actual_source_rel).is_file() else "",
                "difference": diff_rel if (root / diff_source_rel).is_file() else "",
            },
            "measurements": {
                "mean_difference": result.get("mean_difference"),
                "dhash_distance": result.get("dhash_distance"),
                "message": str(result.get("message", "Noch keine aktuelle Prüfung ausgeführt.")),
            },
        })
    passed = sum(bool(item["passed"]) for item in scenarios)
    payload = {
        "schema_version": 2,
        "id": str(config.get("id", "videobatch-fast-visual-inspection")),
        "title": str(config.get("title", "Visuelle Prüfung")),
        "version": str(config.get("version", "")),
        "passed": bool(scenarios) and passed == len(scenarios) and not report.get("contract_errors", []),
        "summary": {
            "scenario_count": len(scenarios),
            "passed_count": passed,
            "failed_count": len(scenarios) - passed,
            "contract_error_count": len(report.get("contract_errors", [])),
        },
        "contract_errors": list(report.get("contract_errors", [])),
        "links": {
            "visual_registry": str(config.get("visual_registry")),
            "inspection_registry": "registries/VISUAL_INSPECTION_REGISTRY.json",
            "visual_report": str(config.get("visual_report")),
            "html": str(config.get("html_output")),
        },
        "policy": visual.get("policy", {}),
        "scenarios": scenarios,
        "runtime": {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "visual_report_path": str(config.get("visual_report")),
            "note": "Pfade, Zeitstempel und Pixelmesswerte sind informativ und werden nicht in den Freigabehash aufgenommen.",
        },
    }
    payload["approval_contract"] = {
        "schema_version": 2,
        "volatile_fields_excluded": [
            "runtime.generated_at",
            "runtime.visual_report_path",
            "scenarios[].artifacts.actual",
            "scenarios[].artifacts.difference",
            "scenarios[].measurements.mean_difference",
            "scenarios[].measurements.dhash_distance",
            "scenarios[].measurements.message",
        ],
        "visual_contract_sha256": inspection_manifest_hash(payload),
        "visual_report_contract_sha256": visual_report_contract_hash(payload, root),
    }
    return payload


def write_inspection_manifest(target: Path, project_root: Path | None = None) -> Path:
    root = Path(project_root) if project_root else PROJECT_ROOT
    payload = build_inspection_manifest(root)
    if target.is_file():
        try:
            previous = json.loads(target.read_text(encoding="utf-8"))
            approval = previous.get("manual_approval") if isinstance(previous, dict) else None
            if isinstance(approval, dict):
                candidate = dict(payload)
                candidate["manual_approval"] = approval
                if verify_visual_approval(candidate, root).valid:
                    payload["manual_approval"] = approval
        except (OSError, json.JSONDecodeError, UnicodeError):
            pass
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def _asset_link(path: str) -> str:
    return "../" + path if path else ""


def _artifact(item: dict[str, Any], key: str) -> str:
    artifacts = item.get("artifacts", {})
    return str(artifacts.get(key, "")) if isinstance(artifacts, dict) else str(item.get(key, ""))


def _measurement(item: dict[str, Any], key: str, fallback: Any = "–") -> Any:
    measurements = item.get("measurements", {})
    return measurements.get(key, fallback) if isinstance(measurements, dict) else item.get(key, fallback)


def write_inspection_html(target: Path, manifest: dict[str, Any]) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    embedded = json.dumps(manifest, ensure_ascii=False).replace("</", "<\\/")
    approval = verify_visual_approval(manifest, target.parent.parent)
    approval_class = "pass" if approval.valid else "fail"
    approval_title = "Desktop-Freigabe signiert" if approval.valid else "Desktop-Freigabe offen oder ungültig"
    approval_detail = approval.message
    if approval.reviewer:
        approval_detail += f" Prüfer: {approval.reviewer}. Datum: {approval.approved_at}. Schlüssel: {approval.key_id}."
    cards = []
    for item in manifest.get("scenarios", []):
        status = "bestanden" if item.get("passed") else "offen/fehlgeschlagen"
        baseline = _asset_link(_artifact(item, "baseline"))
        actual = _asset_link(_artifact(item, "actual"))
        difference = _asset_link(_artifact(item, "difference"))
        images = [f'<figure><figcaption>Referenz</figcaption><a href="{html.escape(baseline)}"><img loading="lazy" src="{html.escape(baseline)}" alt="Referenz {html.escape(item["id"])}"></a></figure>']
        if actual:
            images.append(f'<figure><figcaption>Aktuell</figcaption><a href="{html.escape(actual)}"><img loading="lazy" src="{html.escape(actual)}" alt="Aktuell {html.escape(item["id"])}"></a></figure>')
        if difference:
            images.append(f'<figure><figcaption>Differenz</figcaption><a href="{html.escape(difference)}"><img loading="lazy" src="{html.escape(difference)}" alt="Differenz {html.escape(item["id"])}"></a></figure>')
        required = "".join(f"<li>{html.escape(str(value))}</li>" for value in item.get("required_visible_texts", []))
        cards.append(f'''<article class="scenario" data-group="{html.escape(str(item.get('group','other')))}" data-status="{'pass' if item.get('passed') else 'fail'}">
<header><div><h2>{html.escape(str(item['id']))}</h2><p>{html.escape(str(item.get('group','')))} · {item.get('width')}×{item.get('height')} · {item.get('font_scale')} %</p></div><span class="badge {'pass' if item.get('passed') else 'fail'}">{status}</span></header>
<p class="message">{html.escape(str(_measurement(item, 'message', '')))}</p>
<div class="metrics"><span>Pixelmittel: {_measurement(item, 'mean_difference')}</span><span>dHash: {_measurement(item, 'dhash_distance')}</span><span class="volatile">volatile · nicht signaturrelevant</span></div>
<div class="images">{''.join(images)}</div>
<details><summary>Deterministischer Prüfvertrag</summary><ul>{required}</ul></details>
</article>''')
    summary = manifest.get("summary", {})
    runtime = manifest.get("runtime", {}) if isinstance(manifest.get("runtime"), dict) else {}
    contract = manifest.get("approval_contract", {}) if isinstance(manifest.get("approval_contract"), dict) else {}
    document = f'''<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(str(manifest.get('title','Visuelle Prüfung')))}</title>
<style>
:root{{--bg:#080d12;--surface:#111820;--surface2:#182330;--surface3:#202d3b;--text:#f5f7fa;--muted:#aab7c4;--gold:#e8bd4e;--cyan:#43c6d7;--green:#65d691;--red:#ee7180;--border:#304154;--shadow:0 14px 36px rgba(0,0,0,.28)}}
*{{box-sizing:border-box}} body{{margin:0;background:radial-gradient(circle at 15% 0%,#14202b 0,var(--bg) 38%);color:var(--text);font:15px/1.5 Inter,system-ui,sans-serif}} header.hero{{position:sticky;top:0;z-index:2;background:rgba(8,13,18,.94);backdrop-filter:blur(14px);border-bottom:1px solid var(--border);padding:20px 26px;box-shadow:0 8px 24px rgba(0,0,0,.18)}} h1{{margin:0 0 4px;font-size:1.7rem;letter-spacing:.01em}} .hero p{{margin:0;color:var(--muted)}} .summary{{display:flex;gap:10px;flex-wrap:wrap;margin-top:14px}} .summary span,.controls button,.controls a{{background:linear-gradient(180deg,var(--surface2),var(--surface));border:1px solid var(--border);color:var(--text);padding:9px 13px;border-radius:11px;text-decoration:none;box-shadow:0 4px 12px rgba(0,0,0,.12)}} .approval,.contract{{margin-top:12px;padding:12px 14px;border:1px solid var(--border);border-radius:12px;background:linear-gradient(135deg,var(--surface2),var(--surface));box-shadow:var(--shadow)}} .approval.pass{{border-color:color-mix(in srgb,var(--green) 70%,var(--border))}} .approval.fail{{border-color:var(--red)}} .approval strong,.contract strong{{display:block;margin-bottom:3px}} .contract code{{color:var(--cyan);word-break:break-all}} .controls{{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}} button{{cursor:pointer}} main{{padding:22px;display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:18px}} .scenario{{background:linear-gradient(145deg,var(--surface2),var(--surface));border:1px solid var(--border);border-radius:15px;padding:16px;box-shadow:var(--shadow)}} .scenario>header{{display:flex;justify-content:space-between;gap:12px;align-items:start}} h2{{margin:0;font-size:1.1rem}} .scenario header p,.message{{color:var(--muted);margin:.25rem 0}} .badge{{padding:5px 10px;border-radius:999px;font-weight:750}} .badge.pass{{background:var(--green);color:#07140b}} .badge.fail{{background:var(--red);color:#24070a}} .metrics{{display:flex;gap:10px;flex-wrap:wrap;margin:10px 0}} .metrics span{{background:var(--surface3);padding:5px 8px;border-radius:8px;color:var(--muted)}} .metrics .volatile{{color:var(--gold)}} .images{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px}} figure{{margin:0;background:#0b1117;padding:9px;border:1px solid #263746;border-radius:11px}} figcaption{{color:var(--muted);margin-bottom:6px}} img{{display:block;width:100%;max-height:420px;object-fit:contain;background:#05080c;border-radius:8px}} details{{margin-top:12px}} summary{{cursor:pointer;color:var(--cyan)}} .hidden{{display:none!important}} @media(max-width:700px){{header.hero{{position:static}} main{{padding:10px;grid-template-columns:1fr}}}}
</style></head>
<body><header class="hero"><h1>{html.escape(str(manifest.get('title','Visuelle Prüfung')))}</h1><p>Version {html.escape(str(manifest.get('version','')))} · erzeugt {html.escape(str(runtime.get('generated_at','')))}</p>
<div class="summary"><span>{summary.get('passed_count',0)}/{summary.get('scenario_count',0)} bestanden</span><span>{summary.get('failed_count',0)} offen</span><span>{summary.get('contract_error_count',0)} Vertragsfehler</span></div>
<div class="approval {approval_class}"><strong>{html.escape(approval_title)}</strong><span>{html.escape(approval_detail)}</span></div>
<div class="contract"><strong>Normalisierter Freigabevertrag</strong><span>Flüchtige Pfade und Pixelmesswerte sind ausgeschlossen.</span><br><code>{html.escape(str(contract.get('visual_contract_sha256','')))}</code></div>
<div class="controls"><button data-filter="all">Alle</button><button data-filter="dashboard">Dashboard</button><button data-filter="workspace">Arbeitsbereich</button><button data-filter="dialogs">Dialoge</button><button data-filter="fail">Nur offen</button><a href="../VISUAL_INSPECTION_MANIFEST.json">JSON-Manifest</a><a href="../registries/VISUAL_REGRESSION_REGISTRY.json">Prüfregistry</a></div></header>
<main>{''.join(cards)}</main><script id="manifest-data" type="application/json">{embedded}</script><script>
const cards=[...document.querySelectorAll('.scenario')];document.querySelectorAll('[data-filter]').forEach(b=>b.addEventListener('click',()=>{{const f=b.dataset.filter;cards.forEach(c=>c.classList.toggle('hidden',!(f==='all'||c.dataset.group===f||(f==='fail'&&c.dataset.status==='fail'))));}}));
</script></body></html>'''
    target.write_text(document, encoding="utf-8")
    return target


def copy_visual_assets(project_root: Path, html_dir: Path) -> None:
    for source_rel, target_name in (("tests/visual_actual", "actual"), ("diagnostics/visual_diff", "diff")):
        source = project_root / source_rel
        target = html_dir / target_name
        if target.exists():
            shutil.rmtree(target)
        if source.is_dir():
            shutil.copytree(source, target)
