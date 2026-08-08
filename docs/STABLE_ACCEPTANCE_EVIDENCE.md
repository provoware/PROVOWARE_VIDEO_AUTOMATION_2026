# Externe Stable-Abnahmen

## Zweck

Die Stable-Finalisierung akzeptiert externe Abnahmen ausschließlich als **kandidatengebundene Evidence Schema 2**. Ein Nachweis ist nur gültig, wenn Kandidat, `RELEASE_MANIFEST.json` und der separate ausführungsrelevante Source-Fingerprint unverändert sind. Alte oder kopierte Evidence wird damit nach jeder relevanten Quelländerung automatisch als `stale` blockiert.

## Evidence-Schema 2

Der Finalizer liest einen externen Nachweisordner über `--acceptance-evidence ORDNER`. Er erzeugt oder verändert darin keine Fremdnachweise. Für die Stable-Freigabe werden genau `kde_x11.json` und `long_render.json` benötigt.

```json
{
  "schema_version": 2,
  "evidence_type": "kde_x11",
  "candidate_id": "2.8.3-rc24",
  "manifest_sha256": "64-stelliger SHA-256 von RELEASE_MANIFEST.json",
  "source_sha256": "64-stelliger Source-Fingerprint des exakt geprüften Kandidaten",
  "environment": {"system": "Kubuntu 24.04", "session_or_target": "KDE Plasma X11"},
  "timestamp": "2026-08-07T15:00:00Z",
  "result": "passed",
  "checks": {
    "physical_session": true,
    "application_started": true,
    "preview_rendered": true,
    "window_scaling_checked": true
  }
}
```

`long_render.json` verwendet `evidence_type: long_render` und die Prüfpunkte `large_media_selection`, `slow_external_target`, `render_completed` und `output_hash_verified`.

Alle Pflichtprüfungen müssen `true` und `result` muss `passed` sein. Evidence älter als 30 Tage, mehr als fünf Minuten in der Zukunft, mit falschem Kandidat, Manifest-Hash oder Source-Fingerprint wird fail-closed abgewiesen.

## Physische KDE-X11-Abnahme

Der Lauf muss in einer **realen KDE-Plasma-X11-Sitzung** mit aktivem Display stattfinden. Ein CI-/Xvfb-Lauf darf diese Evidence nicht erzeugen.

```bash
mkdir -p /pfad/evidence-x11
VIDEOBATCH_PHYSICAL_ACCEPTANCE=1 \
PYTHONPATH=src:. \
python3 scripts/live_desktop_gate.py \
  --evidence-dir /pfad/evidence-x11
```

Der Harness prüft zusätzlich eine feste 3×3-Matrix aus drei Fenstergrößen und drei UI-Skalierungen, insgesamt **9 Profile**. Erst nach vollständig bestandenem physischen Lauf wird `kde_x11.json` exportiert.

## Physischer Large-Media-/Slow-Target-Lauf

Nach Erzeugung des unveränderlichen Langzeitrendervertrags wird der reale Lauf mit Evidence-Export gestartet:

```bash
PYTHONPATH=src:. python3 scripts/run_long_render_acceptance.py \
  --contract /pfad/rc24-long-render-contract.json \
  --evidence-dir /pfad/evidence-long-render
```

Bei kontrollierter Wiederaufnahme bleibt derselbe Evidence-Ordner gebunden:

```bash
PYTHONPATH=src:. python3 scripts/run_long_render_acceptance.py \
  --contract /pfad/rc24-long-render-contract.json \
  --resume \
  --evidence-dir /pfad/evidence-long-render
```

`long_render.json` wird nur nach einem realen, nicht als Rehearsal markierten 96-Aufträge-Lauf auf einem validierten langsamen externen USB-/ext4-Ziel erzeugt.

## Abschlussvalidierung

Die zwei realen Nachweise werden in einen gemeinsamen Ordner kopiert und gegen den **aktuellen** Kandidaten geprüft:

```bash
PYTHONPATH=src:. python3 scripts/validate_stable_acceptance.py \
  --evidence-dir /pfad/stable-evidence \
  --candidate-id 2.8.3-rc24
```

Die Finalisierung verwendet denselben Validator. Ein Quellcodewechsel nach einer Abnahme ändert `source_sha256` und sperrt die Evidence automatisch.

## Reproduzierbare externe Qualitäts-Evidence

Der Offline-Qualitätslauf erzeugt nach erfolgreichem exaktem Ruff-/MyPy-/Bandit-/pip-audit-Lauf einen indexierten Evidence-Satz und ein deterministisches Evidence-ZIP. Jede Evidence-Datei ist über Größe/SHA-256 geschützt und der Index an `candidate_id`, `manifest_sha256` und `source_sha256` gebunden.

Die Toolchain selbst wird ausschließlich aus dem geprüften Wheelhouse installiert. Der Installationsvertrag erzwingt `--no-index`, `--only-binary=:all:` und `--require-hashes`; ein unbemerkter Source-Distribution-Fallback ist damit ausgeschlossen.

## Stable-Regel

Keiner dieser Harnesses hebt ein Gate durch bloße Existenz einer Datei auf. Stable wird erst möglich, wenn alle externen Toolchain-Gates und beide realen physischen Evidence-Dateien für **denselben unveränderten Kandidaten** bestanden und validiert sind.
