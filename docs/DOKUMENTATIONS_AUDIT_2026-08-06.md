# Dokumentationsaudit – 6. August 2026

## Ziel

Alle mit VideoBatch verbundenen Anleitungen und Textdateien wurden inventarisiert, nach Zweck klassifiziert und nach einem einheitlichen Laienstandard bewertet.

## Ausgangslage

Das Release-Manifest enthält rund 50 Markdown-Dateien. Darunter befinden sich:

- aktive Nutzeranleitungen;
- Entwickler- und Fachanleitungen;
- Release- und Qualitätsberichte;
- historische Analyse- und Versionsnachweise;
- visuelle Freigabeverträge;
- interne Kalender- und Arbeitsnotizen.

Eine pauschale sprachliche Neufassung aller Dateien wäre fachlich falsch: Historische Prüfberichte müssen ihren ursprünglichen Beweisstand behalten. Deshalb wurden aktive Anleitungen überarbeitet und sämtliche übrigen Dokumente zentral eingeordnet.

## Vollständig überarbeitet

| Datei | Verbesserung |
|---|---|
| `README.md` | klarer Schnellstart, Dokumentationsnavigation, Pflichtgrade, Begründungen, sichere Fehlerwege |
| `START_HIER_save_.md` | vollständiger Einsteigerablauf vom Entpacken bis zur Ergebnisprüfung |
| `AUTOINSTALLATION_save_.md` | A/B-Installation mit Zweck, Weglassbarkeit, Fehlerfall und Rückfall |
| `ERROR_HANDLING.md` | vollständiges Fehlerhandbuch mit Ampel, Wiederherstellung und Abschlussprüfung |
| `UPDATE_SYSTEM.md` | sicherer Updateablauf mit Signatur, Manifest, A/B-Slot, Stromausfall und Rollback |
| `DEVELOPER_GUIDE.md` | reproduzierbarer Entwicklungsablauf vom `main`-Stand bis zum geprüften Pull Request |

## Neu erstellt

| Datei | Aufgabe |
|---|---|
| `docs/DOKUMENTATIONSSTANDARD.md` | verbindlicher Aufbau für jede neue oder geänderte Anleitung |
| `docs/DOKUMENTATIONSINDEX.md` | zentrale Einordnung aller aktiven, technischen und historischen Textdateien |
| `docs/BENUTZERHANDBUCH.md` | vollständiges laiengerechtes Bedienhandbuch |
| `docs/DOKUMENTATIONS_AUDIT_2026-08-06.md` | maschinenunabhängiger Prüf- und Umfangsnachweis |

## Aktiv eingeordnet, aber nicht rückwirkend umgeschrieben

### Technische Fachanleitungen

- `BEST_PRACTICES.md`
- `DEVELOPER_HANDBOOK.md`
- `PLUGIN_SYSTEM.md`
- `docs/ARCHITEKTUR.md`
- `docs/CODE_QUALITY_PIPELINE.md`
- `docs/DATA_INTEGRITY_HARDENING.md`
- `docs/FAST_EFFECTS.md`
- `docs/OFFLINE_QUALITY_ENVIRONMENT.md`
- `docs/PLUGIN_APPROVALS.md`
- `docs/PLUGIN_APPROVAL_MANAGEMENT.md`
- `docs/PLUGIN_OS_ISOLATION.md`
- `docs/PLUGIN_PERMISSIONS.md`
- `docs/PLUGIN_SIGNING.md`
- `docs/QUICK_MODES.md`
- `docs/REPRODUCIBLE_UPDATE_PIPELINE.md`
- `docs/VISUAL_INSPECTION_HTML.md`
- `docs/VISUAL_REGRESSION.md`
- `docs/WORKSPACE_2X2_AND_DEBUGGING.md`
- `docs/WORKSPACE_LAYOUT_PROFILES.md`
- `docs/WORKSPACE_VISUAL_REGRESSION.md`
- `resources/signing/README.md`
- `toolchain_wheelhouse/README.md`

**Begründung:** Diese Dateien sind technisch gültige Teilverträge oder Spezialanleitungen. Ihre vollständige Neufassung erfordert jeweils eine eigene fachliche Abnahme, damit keine Sicherheits- oder Architekturaussage unbeabsichtigt verändert wird. Der neue Dokumentationsindex verhindert trotzdem, dass Einsteiger sie ohne Kontext verwenden.

**Kann diese Detailüberarbeitung entfallen?** Für die aktuelle Einsteigerverbesserung ja. Für eine spätere vollständige Fachredaktion nein.

## Historische Nachweise – absichtlich unverändert

- `CHANGELOG.md`
- `CODE_QUALITY_REPORT_2.8.3-rc24_save_.md`
- `FAIL_MEMORY_PASS.md`
- `FINAL_AUDIT_2.8.3-rc24_save_.md`
- `FRESH_PACKAGE_REPORT_save_.md`
- `IMPLEMENTATION_REPORT_2.8.3-rc24_save_.md`
- `QUALITY_GATE_REPORT_2.8.3-rc24_save_.md`
- `RELEASE_NOTES_save_.md`
- `STABLE_GATE_ITERATION_2.8.3-rc24_2026-08-04.md`
- `docs/ANALYSE_AUSGANGSTOOL.md`
- `docs/DESIGN_SYSTEM_ANALYSIS_2_5.md`
- `docs/LONG_RENDER_2.8.3-rc24.md`
- `docs/QUALITY_TOOLCHAIN_2_8_3_RC3.md`
- `docs/QUALITY_TOOLCHAIN_2_8_3_RC4.md`
- `docs/SETUP_2_8_3_RC5.md`
- `docs/STABLE_ACCEPTANCE_EVIDENCE.md`
- `docs/VISUAL_LAYOUT_ANALYSIS_2_4.md`

**Warum unverändert?** Diese Dateien belegen einen bestimmten Zeitpunkt, Teststand oder Versionszustand. Eine nachträgliche sprachliche Modernisierung könnte den Eindruck erzeugen, auch der historische Inhalt sei neu geprüft worden.

**Können sie gelöscht werden?** Nicht ohne gesonderten Archiv- und Releaseentscheid. Sie gehören zur Nachvollziehbarkeit.

## Interne Notizen

- `docs/CALENDAR_NOTES.md`
- `docs/CALENDAR_TASK_OVERVIEW.md`

Sie sind im Dokumentationsindex ausdrücklich als interne Planungshilfen gekennzeichnet.

## Neue verbindliche Qualitätskriterien

Aktive Anleitungen müssen künftig enthalten:

1. Ziel;
2. Pflichtgrad;
3. Voraussetzungen;
4. Sicherung und Rückweg;
5. nummerierte Einzelschritte;
6. Begründung kritischer Schritte;
7. Aussage, ob ein Schritt entfallen darf;
8. erwartetes Ergebnis;
9. Fehlerfall;
10. Abschlussprüfung;
11. nächsten logischen Schritt.

## Festgestellte Risiken

### Versionsgebundene Überschriften

Einige Fachanleitungen nennen ältere RC-Versionen. Sie sind im Index als technische oder historische Dokumente eingeordnet und dürfen nicht ungeprüft als aktuelle Hauptanleitung verwendet werden.

### Doppelte oder ähnlich benannte Freigabedokumente

Beispiele:

- `VISUAL_DESKTOP_APPROVAL.md`
- `docs/VISUAL_DESKTOP_APPROVAL.md`

Der Dokumentationsindex erklärt ihre Rolle. Eine spätere Bereinigung darf erst erfolgen, wenn alle referenzierenden Skripte und Manifeste geprüft wurden.

### Gemischte Sprache

Einzelne technische Tabellen und Statusblöcke enthalten englische Begriffe. Automatisch erzeugte oder vertragsgebundene Bereiche wurden nicht willkürlich übersetzt.

## Abschlussprüfung dieser Iteration

- eigenständiger Dokumentationsbranch direkt von `main`
- technischer KPI-Branch wieder bereinigt
- zentrale Navigation vorhanden
- vollständiges Einsteigerhandbuch vorhanden
- Start-, Installation-, Fehler-, Update- und Entwickleranleitung überarbeitet
- historische Nachweise nicht verfälscht
- verbindlicher Standard dokumentiert
- offene Fachredaktion klar benannt

## Nächster Schritt

In einer nachfolgenden Fachredaktionsiteration werden die technischen Spezialanleitungen gruppenweise überarbeitet:

1. Projektstruktur und Schnellmodi;
2. Plugins und Signaturen;
3. Qualitätswerkzeuge und Offline-Umgebung;
4. visuelle Prüfung und Layoutprofile;
5. Architektur und Datenintegrität.

Jede Gruppe erhält eigene technische Tests und einen getrennten Review, damit keine Vertragsaussage durch reine Textoptimierung verändert wird.
