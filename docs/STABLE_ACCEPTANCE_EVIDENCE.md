# Stable-Abnahmenachweise – aktueller Zielvertrag

## Zweck

Die Kubuntu-Basisabnahme und der Langzeitrender vom **29.09.2026** bleiben als historische, ausdrücklich bestätigte Operator-Nachweise erhalten. Nach den späteren UI-/Skalierungsänderungen aus PR #228 reicht die damalige Basisabnahme für den aktuellen Releasekandidaten jedoch nicht mehr aus. Der kanonische Status führt deshalb die physische UI-Abnahme wieder als offen, bis der geänderte Stand real bei 100 %, 150 % und 200 % geprüft wurde.

## Manuelle Kubuntu-Basisfreigabe 2026-09-29

Die Provenienz liegt unter `diagnostics/release_readiness/KUBUNTU_OPERATOR_ACCEPTANCE_2026-09-29.json`. Sie belegt den damaligen Basiszustand unverändert. Sie wird **nicht** auf den später geänderten UI-/Skalierungsstand übertragen und setzt das aktuelle Gate daher nicht mehr automatisch auf grün.

## Erneute UI-Sichtabnahme nach PR #228

Vor Stable muss der aktuelle Stand auf **Kubuntu 26.04 LTS · KDE Plasma · natives Wayland** real geprüft werden. Pflichtumfang:

- 100 %, 150 % und 200 % Ansichtsgröße,
- keine abgeschnittenen Tabellenzeilen oder Bedienelemente,
- sichtbarer Tastaturfokus,
- lesbare Status- und Hilfetexte,
- korrekte Trennung von globaler Ansichtsgröße und Listen-Zoom,
- kein unbeabsichtigtes Ändern der Produktionsreihenfolge beim Sortieren.

Erst nach dokumentierter Abnahme dieses unveränderten Kandidaten darf das Gate `physical_kubuntu_26_04_wayland` wieder `passed` sein.

## Manuelle Langzeitrender-Freigabe 2026-09-29

Die Provenienz liegt unter `diagnostics/release_readiness/LONG_RENDER_OPERATOR_ACCEPTANCE_2026-09-29.json`. Sie dokumentiert die ausdrückliche Bestätigung, dass der Langzeitrender in Ordnung war, ohne fehlende Einzelmessungen oder Hashwerte zu rekonstruieren.

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


## Expliziter Operator-Freigabepfad

Wenn die beiden fachlichen P0-Abnahmen ausdrücklich durch den Projektverantwortlichen bestätigt wurden, darf die Stable-Promotion alternativ über `scripts/validate_operator_stable_acceptance.py` gebunden werden. Dieser Pfad ist **kein stiller Bypass**:

- beide Operator-Nachweise müssen aktuell, kandidatgebunden und als `passed` dokumentiert sein;
- `RELEASE_EVIDENCE.json`, `DEVELOPMENT_STATUS.json` und der freigegebene Qualitätsbericht müssen vollständig `stable_ready` und blockerfrei sein;
- der RC-Manifest-Hash wird vor der Promotion erneut gebunden;
- fehlende Einzelmessungen werden ausdrücklich **nicht** rekonstruiert;
- die Promotion führt danach erneut Qualitäts-, Test-, Desktop-, Visual-, Manifest- und deterministische Doppelpaketierungsprüfungen aus;
- die Stable-Arbeitskopie wird getrennt vom RC erzeugt und als eigener Stable-Commit veröffentlicht.

Der klassische strikte Pfad mit `kubuntu_26_04_wayland.json` und `long_render.json` bleibt unverändert verfügbar.
