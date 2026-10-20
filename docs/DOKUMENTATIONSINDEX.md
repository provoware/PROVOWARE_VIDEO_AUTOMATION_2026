# VideoBatch-Dokumentationswegweiser

**Zweck:** Diese Seite zeigt, welche Datei für welchen Vorgang verwendet werden soll. Sie verhindert, dass Einsteiger versehentlich einen historischen Prüfbericht oder eine technische Vertragsdatei als Bedienungsanleitung verwenden.

## Ziel

Dieser Wegweiser ordnet jede aktuelle Anleitung und jeden historischen Nachweis eindeutig ein.

## Aktive Nutzeranleitungen

| Ziel | Richtige Datei | Pflichtgrad |
|---|---|---|
| aktuelle Entwicklungsprüfungen, PR-Bestand und offene Freigaben | `docs/STATUS.md`, `docs/TODO.md` | Pflicht für Entwicklung |
| VideoBatch zum ersten Mal starten | `docs/start/START_HIER_save_.md` | Pflicht |
| VideoBatch vollständig bedienen | `docs/BENUTZERHANDBUCH.md` | Empfohlen |
| automatische Installation verstehen | `docs/start/AUTOINSTALLATION_save_.md` | Pflicht bei Installation |
| Projektordner und Dateien verstehen | `docs/start/PROJEKTORDNERSTRUKTUR_save_.md` | Empfohlen |
| Schnellmodi auswählen | `docs/QUICK_MODES.md` | Optional |
| Fehler sicher beheben | `docs/manuals/ERROR_HANDLING.md` | Pflicht bei Fehlern |
| Updates und Rückfall verstehen | `docs/manuals/UPDATE_SYSTEM.md` | Pflicht bei Updates |
| aktuelle Änderungen nachlesen | `docs/archive/rc24/RELEASE_NOTES_save_.md` | Empfohlen |

## 2. Ich möchte entwickeln oder prüfen

| Ziel | Richtige Datei |
|---|---|
| Entwicklungsumgebung und erster Beitrag | `docs/manuals/DEVELOPER_GUIDE.md` |
| Architektur und Arbeitsregeln | `docs/reference/DEVELOPER_HANDBOOK.md`, `docs/ARCHITEKTUR.md`, `AGENTS.md` |
| Codequalitätsprüfung | `docs/CODE_QUALITY_PIPELINE.md`, `docs/OFFLINE_QUALITY_ENVIRONMENT.md` |
| reproduzierbare Updates | `docs/REPRODUCIBLE_UPDATE_PIPELINE.md` |
| Plugins prüfen | `docs/reference/PLUGIN_SYSTEM.md`, `docs/PLUGIN_PERMISSIONS.md`, `docs/PLUGIN_SIGNING.md`, `docs/PLUGIN_APPROVALS.md`, `docs/PLUGIN_APPROVAL_MANAGEMENT.md`, `docs/PLUGIN_OS_ISOLATION.md` |
| visuelle Prüfung | `docs/VISUAL_INSPECTION_HTML.md`, `docs/VISUAL_REGRESSION.md`, `docs/WORKSPACE_VISUAL_REGRESSION.md` |
| Neues responsives Raster V1 (800×600, 120×80) | `docs/design/PROVOWARE_RESPONSIVE_GRID_V1.md`, `config/contracts/PROVOWARE_RESPONSIVE_GRID_V1.json`, `visual_inspection/provoware_grid_reference.html` |
| Historischer VideoBatch-Grafikvertrag | `docs/design/VIDEOBATCH_GRAPHICS_MANIFEST.md`, `docs/design/VIDEOBATCH_DESIGN_IMPLEMENTATION_PLAN.md` |

## Technische Fachanleitungen

Technische Referenzdokumente liegen gebündelt unter `docs/reference/`. Diese Dateien beschreiben weiterhin gültige Teilbereiche, setzen aber technisches Grundwissen voraus:

- `docs/reference/BEST_PRACTICES.md`
- `docs/reference/KEY_ARCHIVE.md`
- `docs/reference/REGISTRY_MANIFEST.md`
- `docs/reference/STABLE_UPDATE.md`
- `docs/reference/TEST_SYSTEM.md`
- `docs/DATA_INTEGRITY_HARDENING.md`
- `docs/FAST_EFFECTS.md`
- `docs/WORKSPACE_2X2_AND_DEBUGGING.md`
- `docs/WORKSPACE_LAYOUT_PROFILES.md`
- `resources/signing/README.md`
- `toolchain_wheelhouse/README.md`

## Historische Nachweise

Die folgenden Dateien sind Belege eines bestimmten Entwicklungs- oder Prüfstands. Sie dürfen nicht als aktuelle Bedienungsanleitung verwendet werden:

- `docs/CHANGELOG.md`
- `docs/archive/rc24/CODE_QUALITY_REPORT_2.8.3-rc24_save_.md`
- `docs/archive/rc24/FINAL_AUDIT_2.8.3-rc24_save_.md`
- `docs/archive/rc24/FRESH_PACKAGE_REPORT_save_.md`
- `docs/archive/rc24/IMPLEMENTATION_REPORT_2.8.3-rc24_save_.md`
- `docs/archive/release-history/QUALITY_GATE_REPORT_2.8.3-rc24_save_.md`
- `docs/LONG_RENDER_2.8.3-rc24.md`
- `docs/STABLE_ACCEPTANCE_EVIDENCE.md`
- `docs/archive/release-history/` – frühere Release-, Qualitäts-, Design- und Prüfstände (unverändert archiviert)

**Warum bleiben diese Dateien unverändert?** Sie dokumentieren einen historischen Zustand. Eine sprachliche Überarbeitung könnte unbeabsichtigt so wirken, als wäre auch der damalige Prüfstand nachträglich verändert worden.

**Kann man sie löschen?** Nein, nicht ohne gesonderte Archiventscheidung. Sie dienen der Nachvollziehbarkeit und Releasebeweiskette.

## Archivierte Stable-Arbeitsstände

Überholte Zwischenstände liegen unter `docs/archive/release-history/` und sind **keine aktuellen Freigabestatus**.

## 5. Interne Kalender- und Arbeitsnotizen

- `docs/CALENDAR_NOTES.md`
- `docs/CALENDAR_TASK_OVERVIEW.md`

Diese Dateien sind interne Planungshilfen und keine Nutzeranleitungen.

## 6. Visuelle Freigaben und Normalisierung

- `docs/reference/VISUAL_APPROVAL_NORMALIZATION.md`
- `docs/VISUAL_DESKTOP_APPROVAL.md`
- `docs/archive/release-history/VISUAL_DESKTOP_APPROVAL.md` – historische 2.8.1-rc1-Abnahme, nicht aktuell

Diese Dateien dokumentieren Prüfverträge. Eine Freigabe darf nur als bestanden bezeichnet werden, wenn der zugehörige aktuelle Nachweis vorhanden und gültig ist.

## 7. Welche Datei ist maßgeblich?

Bei widersprüchlichen Angaben gilt diese Reihenfolge:

1. Sicherheits- und Integritätsverträge im Code und in maschinenlesbaren Manifesten
2. `README.md` und `docs/start/START_HIER_save_.md`
3. `docs/BENUTZERHANDBUCH.md`
4. aktive Fachanleitungen
5. historische Berichte und Archive

## 8. Dokumentationsfehler melden

Bei einer unklaren oder falschen Anleitung:

1. Dateiname notieren.
2. Überschrift oder Abschnitt notieren.
3. Erwartetes Verhalten und tatsächliches Verhalten getrennt beschreiben.
4. Keine Originaldateien oder Projekte verändern, nur um die Anleitung „passend zu machen“.
5. Korrektur als eigene Dokumentationsänderung einreichen.

Der verbindliche Schreib- und Prüfstandard steht in `docs/DOKUMENTATIONSSTANDARD.md`.


## Neu archivierte überholte Root-Nachweise

- `docs/archive/release-history/QUALITY_GATE_ATTEMPT_2.8.3-rc24.md`
- `docs/archive/release-history/STABLE_GATE_ITERATION_2.8.3-rc24_2026-09-11.md`
- `docs/archive/release-history/VISUAL_DESKTOP_APPROVAL.md`

Diese Dateien dienen nur noch der Historie. `diagnostics/release_readiness/RELEASE_EVIDENCE.json` dokumentiert ausschließlich den historischen RC24-Nachweis (496 Dateien); für PR #240 liegen die getrennten Entwicklungsnachweise in `CANDIDATE_PR240_CI_EVIDENCE.json` und `CANDIDATE_PR240_QUALITY_STATUS.json` im selben Verzeichnis. Einstieg und ausdrückliche Freigabesperren stehen in `README.md` und `STATUS.md`.


## Aktuelle Strukturmigration und PR-Status

- **Start:** `STARTEN.sh`; technische Kommandos unter `scripts/cli/`, Installation unter `scripts/install/`.
- **Aktueller PR:** [#246](https://github.com/provoware/PROVOWARE_VIDEO_AUTOMATION_2026/pull/246); #247, #248 und #250 sind geschlossen (letzterer ohne Merge).
- **Prüfgrundlage:** Commit `2ae2ae5`, 8/8 GitHub-Workflows bestanden; Benutzer-ZIP entpackt und sieben Hauptordnerdateien gezählt.
- **Grenze:** Der vollständige grafische Offline-Erststart aus diesem ZIP und die persönliche Kubuntu-Endabnahme stehen aus. Ein neuer Release ist nicht freigegeben.

Die jeweils aktuellen Arbeitspunkte werden in `docs/TODO.md` geführt; die Projektübersicht steht in `README.md`.
