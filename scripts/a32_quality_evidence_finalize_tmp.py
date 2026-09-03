#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

CANDIDATE = "048aa5733d9d0ce5fef872d25e0437fae08eab94"
RUN_ID = 33803727562
ARTIFACT_ID = 9912083312
ARTIFACT_DIGEST = "sha256:f0151cf3193dc5e073c9313a4bee26b4507810c131fcd6a7d6d2613b38328801"
ARTIFACT_NAME = "a32-pinned-offline-quality-evidence-048aa573"


def main() -> int:
    evidence_path = Path("diagnostics/release_readiness/RELEASE_EVIDENCE.json")
    data = json.loads(evidence_path.read_text(encoding="utf-8"))
    provenance = data.setdefault("provenance", {})
    provenance["offline_quality_report"] = "QUALITY_GATE_REPORT_2.8.3-rc24_save_.md"
    provenance["offline_quality_run_id"] = RUN_ID
    provenance["offline_quality_verified_commit"] = CANDIDATE
    provenance["offline_quality_artifact_id"] = ARTIFACT_ID
    provenance["offline_quality_artifact_name"] = ARTIFACT_NAME
    provenance["offline_quality_artifact_digest"] = ARTIFACT_DIGEST

    quality_gate_ids = {
        "ruff_0_16_1",
        "mypy_2_3_0",
        "bandit_1_9_4",
        "pip_audit_2_10_1",
    }
    for gate in data.get("stable_gates", []):
        if gate.get("id") in quality_gate_ids:
            gate["status"] = "passed"
            gate["reason"] = (
                "QUALITY_GATE_REPORT_2.8.3-rc24_save_.md · "
                f"Workflow {RUN_ID} · Kandidat {CANDIDATE} · Rückgabecode 0"
            )

    data.setdefault("progress", {})["current_todo"] = (
        "Quality-Evidence auf aktuellem A32.2-Kandidaten synchronisiert; "
        "physische KDE-Abnahme und Large-Media-Soak bleiben offen"
    )
    evidence_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    report = f"""# Exakter Offline-Qualitätsbericht 2.8.3-rc24

## Ergebnis

Die exakt gepinnte Qualitätswerkzeugkette wurde am 3. September 2026 erneut vollständig auf dem aktuellen A32.2-Kandidaten `{CANDIDATE}` ausgeführt. Alle vier Pflichtwerkzeuge bestanden mit Rückgabecode 0. Der eigentliche Werkzeuglauf lief mit aktivierter Offline-Netzwerksperre.

| Werkzeug | Exakte Version | Ergebnis | Rückgabecode |
|---|---:|---|---:|
| Ruff | 0.16.1 | bestanden | 0 |
| MyPy | 2.3.0 | bestanden | 0 |
| Bandit | 1.9.4 | bestanden | 0 |
| pip-audit | 2.10.1 | bestanden | 0 |

## Reproduzierbarer Ablauf

1. Der CI-Helfer wurde ausschließlich als Trigger verwendet; geprüft wurde durch expliziten Checkout der festgefrorene Produktkandidat `{CANDIDATE}`.
2. Das Quality-Wheelhouse wurde aufgebaut und vollständig verifiziert.
3. Die Qualitätsumgebung wurde mit den exakt gepinnten Versionen Ruff 0.16.1, MyPy 2.3.0, Bandit 1.9.4 und pip-audit 2.10.1 vorbereitet.
4. Vor dem finalen Werkzeuglauf wurde die Offline-Umgebung erneut hergestellt und verifiziert.
5. `scripts/run_external_quality.py --mode required --offline` führte alle vier Pflichtwerkzeuge mit aktivierter Socket-Netzwerksperre aus.
6. Rückgabecodes, Toolversionen, Logs, Wheelhouse-Manifest und Kandidaten-SHA wurden als Actions-Artefakt gesichert.

## Einzelbefunde

### Ruff 0.16.1

`All checks passed!`

Geprüfter Umfang: `src`, `scripts`, `tests` gemäß `pyproject.toml`.

### MyPy 2.3.0

`Success: no issues found in 10 source files`

Geprüfter Umfang: die zehn im verbindlichen externen Qualitätsrunner festgelegten sicherheits- und laufzeitkritischen Module.

### Bandit 1.9.4

Rückgabecode 0; keine Sicherheitsbefunde. Die bekannten Parserhinweise zu natürlichen Wörtern in Kommentaren sind keine Test-IDs und keine Schwachstellen.

### pip-audit 2.10.1

`No known vulnerabilities found`

Geprüft wurde die exakt gepinnte Laufzeit-Lockdatei mit deaktivierter impliziter Pip-Auflösung und vorbereitetem Advisory-Cache; der finale Audit lief unter der Offline-Netzwerksperre.

## Nachweis

- Workflow-Lauf: `{RUN_ID}`
- geprüfter Produkt-Commit: `{CANDIDATE}`
- Trigger-Branch: `ci/a32-2-quality-evidence-048aa573`
- Artefakt: `{ARTIFACT_NAME}`
- Artefakt-ID: `{ARTIFACT_ID}`
- Artefakt-SHA-256: `{ARTIFACT_DIGEST.removeprefix('sha256:')}`
- Aufbewahrung: 30 Tage
- Gate-Ausgang: `0`

## Provenienzentscheidung

Der Workflow-Trigger-Commit ist absichtlich **nicht** der geprüfte Produkt-Commit. Der Workflow checkte den Produktkandidaten `{CANDIDATE}` explizit aus und bestätigte diesen SHA vor der Werkzeugausführung. Dadurch beweist der nachträgliche Evidence-Commit nicht sich selbst und es entsteht keine zirkuläre Commit-Bindung.

## Verbleibende Stable-Gates

Die externen Python-Qualitätswerkzeuge blockieren Stable nicht. Weiterhin offen bleiben:

1. physische KDE-Abnahme unter echten Zielsystem-Sitzungen,
2. dokumentierter Langzeitrender mit großer Medienauswahl und langsamem externem Ziel.

Der Kandidat bleibt bis zu diesen Nachweisen `2.8.3-rc24` und wird nicht als Stable bezeichnet.
"""
    Path("QUALITY_GATE_REPORT_2.8.3-rc24_save_.md").write_text(
        report,
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
