#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

CANDIDATE = "934688e8a2f9e1344a91a959396aaef361ee9b67"
RUN_ID = 33804721216
ARTIFACT_ID = 9912461944
ARTIFACT_NAME = "a32-pinned-offline-quality-evidence-934688e8"
ARTIFACT_SHA256 = "7574b309911b3c067583510b7e418af1ceec999e59008ea1c07c1d12525a4c7c"
VERIFIED_AT = "2026-09-03T20:52:37Z"

p = Path("diagnostics/release_readiness/RELEASE_EVIDENCE.json")
data = json.loads(p.read_text(encoding="utf-8"))
prov = data.setdefault("provenance", {})
prov["offline_quality_report"] = "QUALITY_GATE_REPORT_2.8.3-rc24_save_.md"
prov["offline_quality_run_id"] = RUN_ID
prov["offline_quality_verified_commit"] = CANDIDATE
prov["offline_quality_artifact_id"] = ARTIFACT_ID
prov["offline_quality_artifact_name"] = ARTIFACT_NAME
prov["offline_quality_artifact_sha256"] = ARTIFACT_SHA256
prov["offline_quality_verified_at"] = VERIFIED_AT
prov.pop("offline_quality_probe_pr", None)
for gate in data.get("stable_gates", []):
    if gate.get("id") in {"ruff_0_16_1", "mypy_2_3_0", "bandit_1_9_4", "pip_audit_2_10_1"}:
        gate["status"] = "passed"
        gate["reason"] = f"QUALITY_GATE_REPORT_2.8.3-rc24_save_.md · Workflow {RUN_ID} · Commit {CANDIDATE} · Rückgabecode 0"
data.setdefault("progress", {})["current_todo"] = "Quality-Evidence auf aktuellem A32.2-Head bestätigt; physische KDE-Abnahme und Large-Media-Soak bleiben offen"
p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

report = f'''# Exakter Offline-Qualitätsbericht 2.8.3-rc24

## Ergebnis

Die exakt gepinnte Qualitätswerkzeugkette wurde am 3. September 2026 erneut vollständig auf dem aktuellen A32.2-Head `{CANDIDATE}` ausgeführt. Alle vier Pflichtwerkzeuge bestanden mit Rückgabecode 0; der finale Werkzeuglauf lief mit aktivierter Offline-Netzwerksperre.

| Werkzeug | Exakte Version | Ergebnis | Rückgabecode |
|---|---:|---|---:|
| Ruff | 0.16.1 | bestanden | 0 |
| MyPy | 2.3.0 | bestanden | 0 |
| Bandit | 1.9.4 | bestanden | 0 |
| pip-audit | 2.10.1 | bestanden | 0 |

## Geprüfter Kandidat

- Produkt-Commit: `{CANDIDATE}`
- Workflow-Lauf: `{RUN_ID}`
- Trigger-Branch: `ci/a32-2-quality-evidence-934688e8`
- Evidence-Artefakt: `{ARTIFACT_NAME}`
- Artefakt-ID: `{ARTIFACT_ID}`
- Artefakt-SHA-256: `{ARTIFACT_SHA256}`
- Offline-Netzwerkguard während der vier Qualitätswerkzeuge: aktiv

Der Workflow-Trigger lief absichtlich auf einem isolierten Helper-Branch. Vor der Qualitätsprüfung wurde hart der oben genannte Produkt-Commit ausgecheckt und gegen den erwarteten SHA geprüft. Der Helper-Commit ist deshalb nicht der geprüfte Produktstand; der nachträgliche Evidence-Commit zertifiziert nicht sich selbst.

## Einzelbefunde

### Ruff 0.16.1
Rückgabecode 0; Umfang `src`, `scripts`, `tests` gemäß `pyproject.toml`.

### MyPy 2.3.0
Rückgabecode 0; zehn sicherheits- und laufzeitkritische Module des verbindlichen externen Qualitätsrunners ohne Befund.

### Bandit 1.9.4
Rückgabecode 0; keine Sicherheitsbefunde.

### pip-audit 2.10.1
Rückgabecode 0; keine bekannte Schwachstelle in der exakt gepinnten Laufzeit-Lockdatei. Der finale Audit lief unter aktivem Offline-Netzwerkguard.

## Verbleibende Stable-Gates

Die externen Python-Qualitätswerkzeuge blockieren Stable nicht. Weiterhin offen bleiben:

1. physische KDE-Abnahme unter echten Zielbedingungen,
2. dokumentierter Langzeitrender mit großer Medienauswahl und langsamem externem Ziel.

Der Kandidat bleibt bis zu diesen Nachweisen `2.8.3-rc24` und wird nicht als Stable bezeichnet.
'''
Path("QUALITY_GATE_REPORT_2.8.3-rc24_save_.md").write_text(report, encoding="utf-8")
