# VideoBatch-Dokumentationswegweiser

**Zweck:** Diese Seite zeigt, welche Datei für welchen Vorgang verwendet werden soll. Sie verhindert, dass Einsteiger versehentlich einen historischen Prüfbericht oder eine technische Vertragsdatei als Bedienungsanleitung verwenden.

## Ziel

Dieser Wegweiser ordnet jede aktuelle Anleitung und jeden historischen Nachweis eindeutig ein.

## Aktive Nutzeranleitungen

| Ziel | Richtige Datei | Pflichtgrad |
|---|---|---|
| VideoBatch zum ersten Mal starten | `START_HIER_save_.md` | Pflicht |
| VideoBatch vollständig bedienen | `docs/BENUTZERHANDBUCH.md` | Empfohlen |
| automatische Installation verstehen | `AUTOINSTALLATION_save_.md` | Pflicht bei Installation |
| Projektordner und Dateien verstehen | `PROJEKTORDNERSTRUKTUR_save_.md` | Empfohlen |
| Schnellmodi auswählen | `docs/QUICK_MODES.md` | Optional |
| Fehler sicher beheben | `ERROR_HANDLING.md` | Pflicht bei Fehlern |
| Updates und Rückfall verstehen | `UPDATE_SYSTEM.md` | Pflicht bei Updates |
| aktuelle Änderungen nachlesen | `RELEASE_NOTES_save_.md` | Empfohlen |

## 2. Ich möchte entwickeln oder prüfen

| Ziel | Richtige Datei |
|---|---|
| Entwicklungsumgebung und erster Beitrag | `DEVELOPER_GUIDE.md` |
| Architektur und Arbeitsregeln | `DEVELOPER_HANDBOOK.md`, `docs/ARCHITEKTUR.md`, `AGENTS.md` |
| Codequalitätsprüfung | `docs/CODE_QUALITY_PIPELINE.md`, `docs/OFFLINE_QUALITY_ENVIRONMENT.md` |
| reproduzierbare Updates | `docs/REPRODUCIBLE_UPDATE_PIPELINE.md` |
| Plugins prüfen | `PLUGIN_SYSTEM.md`, `docs/PLUGIN_PERMISSIONS.md`, `docs/PLUGIN_SIGNING.md`, `docs/PLUGIN_APPROVALS.md`, `docs/PLUGIN_APPROVAL_MANAGEMENT.md`, `docs/PLUGIN_OS_ISOLATION.md` |
| visuelle Prüfung | `docs/VISUAL_INSPECTION_HTML.md`, `docs/VISUAL_REGRESSION.md`, `docs/WORKSPACE_VISUAL_REGRESSION.md` |
| Designvertrag | `docs/design/VIDEOBATCH_GRAPHICS_MANIFEST.md`, `docs/design/VIDEOBATCH_DESIGN_IMPLEMENTATION_PLAN.md` |

## Technische Fachanleitungen

Diese Dateien beschreiben weiterhin gültige Teilbereiche, setzen aber technisches Grundwissen voraus:

- `BEST_PRACTICES.md`
- `docs/DATA_INTEGRITY_HARDENING.md`
- `docs/FAST_EFFECTS.md`
- `docs/WORKSPACE_2X2_AND_DEBUGGING.md`
- `docs/WORKSPACE_LAYOUT_PROFILES.md`
- `resources/signing/README.md`
- `toolchain_wheelhouse/README.md`

## Historische Nachweise

Die folgenden Dateien sind Belege eines bestimmten Entwicklungs- oder Prüfstands. Sie dürfen nicht als aktuelle Bedienungsanleitung verwendet werden:

- `CHANGELOG.md`
- `CODE_QUALITY_REPORT_2.8.3-rc24_save_.md`
- `FAIL_MEMORY_PASS.md`
- `FINAL_AUDIT_2.8.3-rc24_save_.md`
- `FRESH_PACKAGE_REPORT_save_.md`
- `IMPLEMENTATION_REPORT_2.8.3-rc24_save_.md`
- `QUALITY_GATE_REPORT_2.8.3-rc24_save_.md`
- `STABLE_GATE_ITERATION_2.8.3-rc24_2026-08-04.md`
- `docs/LONG_RENDER_2.8.3-rc24.md`
- `docs/QUALITY_TOOLCHAIN_2_8_3_RC3.md`
- `docs/QUALITY_TOOLCHAIN_2_8_3_RC4.md`
- `docs/SETUP_2_8_3_RC5.md`
- `docs/STABLE_ACCEPTANCE_EVIDENCE.md`
- `docs/ANALYSE_AUSGANGSTOOL.md`
- `docs/DESIGN_SYSTEM_ANALYSIS_2_5.md`
- `docs/VISUAL_LAYOUT_ANALYSIS_2_4.md`

**Warum bleiben diese Dateien unverändert?** Sie dokumentieren einen historischen Zustand. Eine sprachliche Überarbeitung könnte unbeabsichtigt so wirken, als wäre auch der damalige Prüfstand nachträglich verändert worden.

**Kann man sie löschen?** Nein, nicht ohne gesonderte Archiventscheidung. Sie dienen der Nachvollziehbarkeit und Releasebeweiskette.

## 5. Interne Kalender- und Arbeitsnotizen

- `docs/CALENDAR_NOTES.md`
- `docs/CALENDAR_TASK_OVERVIEW.md`

Diese Dateien sind interne Planungshilfen und keine Nutzeranleitungen.

## 6. Visuelle Freigaben und Normalisierung

- `VISUAL_APPROVAL_NORMALIZATION.md`
- `VISUAL_DESKTOP_APPROVAL.md`
- `docs/VISUAL_DESKTOP_APPROVAL.md`

Diese Dateien dokumentieren Prüfverträge. Eine Freigabe darf nur als bestanden bezeichnet werden, wenn der zugehörige aktuelle Nachweis vorhanden und gültig ist.

## 7. Welche Datei ist maßgeblich?

Bei widersprüchlichen Angaben gilt diese Reihenfolge:

1. Sicherheits- und Integritätsverträge im Code und in maschinenlesbaren Manifesten
2. `README.md` und `START_HIER_save_.md`
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
