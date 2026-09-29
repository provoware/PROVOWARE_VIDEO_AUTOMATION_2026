# Stable-Abnahmenachweise – aktueller Zielvertrag

## Zweck

Der kanonische Projektstatus führt die Kubuntu-Basisabnahme seit **29.09.2026** als manuell freigegeben. Diese Freigabe dokumentiert eine ausdrückliche Projektentscheidung und behauptet keinen neu ausgeführten physischen Kubuntu-26.04-Lauf. Der technische Stable-Promotionspfad bleibt davon unabhängig fail-closed und verlangt weiterhin seine formalen Nachweisdateien; zusätzlich bleibt der reale Langzeitrender offen.

## Manuelle Kubuntu-Basisfreigabe 2026-09-29

Die Provenienz liegt unter `diagnostics/release_readiness/KUBUNTU_OPERATOR_ACCEPTANCE_2026-09-29.json`. Sie setzt das kanonische Gate `physical_kubuntu_26_04_wayland` für die Projektfortschrittsanzeige auf grün, ohne nicht vorhandene Messwerte oder eine erneute physische Ausführung zu erfinden.

## Benötigte Dateien für den strikten Stable-Promotionspfad

Der Nachweisordner enthält genau diese beiden JSON-Dateien:

- `kubuntu_26_04_wayland.json`
- `long_render.json`

X11, XWayland sowie Ubuntu 22.04/24.04 sind keine Stable-Zielpfade mehr. Alte Nachweise bleiben historische Evidenz, erfüllen aber den aktuellen Gate-Vertrag nicht.

## Gemeinsame Pflichtfelder

```json
{
  "schema_version": 1,
  "evidence_type": "kubuntu_26_04_wayland",
  "candidate_id": "2.8.3-rc24",
  "manifest_sha256": "<SHA-256 des unveränderten RELEASE_MANIFEST.json>",
  "environment": {
    "system": "Kubuntu 26.04 LTS",
    "desktop": "KDE Plasma",
    "session_or_target": "Wayland"
  },
  "timestamp": "2026-09-11T12:00:00+02:00",
  "result": "passed",
  "checks": {}
}
```

## Pflichtprüfungen Zielsystem

`kubuntu_26_04_wayland.json` muss alle folgenden Prüfpunkte mit `true` enthalten:

- `physical_session`
- `application_started`
- `native_wayland_backend`
- `preview_rendered`
- `window_scaling_checked`

## Pflichtprüfungen Langzeitrender

`long_render.json` verwendet `evidence_type: "long_render"` und benötigt:

- `large_media_selection`
- `slow_external_target`
- `render_completed`
- `output_hash_verified`

## Sicherheitsregeln

- Beide Nachweise müssen zum exakt gleichen Kandidaten und Manifest-Hash gehören.
- Das Ergebnis muss `passed` sein.
- Die Prüfumgebung darf nicht leer sein.
- Nachweise dürfen höchstens 30 Tage alt sein.
- Fehlende, veraltete oder fremde Nachweise blockieren Stable; sie werden niemals automatisch erzeugt oder umgeschrieben.
