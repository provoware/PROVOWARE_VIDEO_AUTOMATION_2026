# Registry-Manifest 2.8.3-rc11

Verbindliche Registries:

- `ERROR_REGISTRY.json`
- `FUNCTION_REGISTRY.json`
- `PLUGIN_REGISTRY.json`
- `PLUGIN_TRUST_REGISTRY.json`
- `PLUGIN_APPROVAL_REGISTRY.json`
- `UPDATE_REGISTRY.json`
- `SCENARIO_REGISTRY.json`
- `UI_BLUEPRINT.json`
- `UI_COMPONENT_REGISTRY.json`
- `WORKSPACE_LAYOUT_REGISTRY.json`
- `VISUAL_REGRESSION_REGISTRY.json`
- `VISUAL_INSPECTION_REGISTRY.json`
- `VISUAL_APPROVAL_REGISTRY.json`
- `CODE_QUALITY_REGISTRY.json`
- `ARTIFACT_ROLE_REGISTRY.json`

`ARTIFACT_ROLE_REGISTRY.json` kennzeichnet Dateien, die trotz Archivpfad weiterhin aktive Vertragsquellen sind. Solche Dateien dürfen nicht verschoben oder gelöscht werden, ohne Registry und alle deklarierten Verbraucher im selben Patch anzupassen.

Doppelte JSON-Schlüssel, fehlende Schemas und unvollständige Verträge blockieren die Anwendung oder Releaseprüfung.

## Zusätzliche beratende Entwicklungsregister

- `PROJECT_FILE_POLICY.json`: lokal persistierter Dateiindex, ohne CI-Freigabewirkung.
- `ROOT_MIGRATION_REGISTRY.json`: nachprüfbare Umzugswege mit ursprünglichen Git-Blob-IDs.
- `TEST_EVIDENCE_POLICY.json`: ausschließlich für wiederverwendbare, unveränderte **Entwicklungstests**; kein Release-Gate und keine Stable-Freigabe.

Diese Register ergänzen die bestehenden verbindlichen Release-Verträge, ersetzen sie nicht.
