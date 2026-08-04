# Externe Stable-Abnahmen

Die Finalisierung liest einen externen Nachweisordner über
`--acceptance-evidence ORDNER`. Sie erzeugt oder verändert darin keine Dateien.
Der Ordner enthält genau die benötigten Dateien `kde_x11.json`,
`kde_wayland.json` und `long_render.json` im Format Version 1.

```json
{
  "schema_version": 1,
  "evidence_type": "kde_x11",
  "candidate_id": "2.8.3-rc24",
  "manifest_sha256": "64-stelliger SHA-256 von RELEASE_MANIFEST.json",
  "environment": {"system": "Kubuntu 24.04", "session_or_target": "KDE X11"},
  "timestamp": "2026-08-04T10:00:00Z",
  "result": "passed",
  "checks": {
    "physical_session": true,
    "application_started": true,
    "preview_rendered": true,
    "window_scaling_checked": true
  }
}
```

`kde_wayland.json` verwendet dieselben Prüfpunkte und `evidence_type` gleich
`kde_wayland`. `long_render.json` verwendet `evidence_type` gleich `long_render`
und die Prüfpunkte `large_media_selection`, `slow_external_target`,
`render_completed` und `output_hash_verified`.

Alle Prüfpunkte müssen `true` und das Ergebnis muss `passed` sein. Kandidat und
Manifest-Hash müssen exakt passen. Der Zeitpunkt benötigt eine Zeitzone und darf
höchstens 30 Tage alt sowie höchstens fünf Minuten in der Zukunft liegen. Neue
Nachweise werden ausschließlich nach den realen Prüfungen manuell exportiert.
