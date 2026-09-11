# Dokumentationsaudit – 6. August 2026

## Ziel

Alle mit VideoBatch verbundenen Anleitungen und Textdateien wurden inventarisiert, nach Zweck klassifiziert und nach einem einheitlichen Laienstandard bewertet.

## Ausgangslage

Das Release-Manifest enthält aktive Nutzeranleitungen, Entwickler- und Fachanleitungen, Release- und Qualitätsberichte, historische Nachweise, Freigabeverträge sowie interne Arbeitsnotizen.

Eine pauschale sprachliche Neufassung aller Dateien wäre fachlich falsch: Historische Prüfberichte müssen ihren ursprünglichen Beweisstand behalten. Deshalb wurden aktive Anleitungen überarbeitet und die übrigen Dokumente zentral eingeordnet.

## Vollständig überarbeitet

| Datei | Verbesserung |
|---|---|
| `README.md` | Schnellstart, Dokumentationsnavigation, Pflichtgrade, Begründungen und sichere Fehlerwege |
| `START_HIER_save_.md` | vollständiger Einsteigerablauf vom Entpacken bis zur Ergebnisprüfung |
| `AUTOINSTALLATION_save_.md` | A/B-Installation mit Zweck, Weglassbarkeit, Fehlerfall und Rückfall |
| `ERROR_HANDLING.md` | Fehlerhandbuch mit Ampel, Wiederherstellung und Abschlussprüfung |
| `UPDATE_SYSTEM.md` | Updateablauf mit Signatur, Manifest, A/B-Slot, Stromausfall und Rollback |
| `DEVELOPER_GUIDE.md` | Entwicklungsablauf vom `main`-Stand bis zum geprüften Pull Request |

## Neu erstellt

| Datei | Aufgabe |
|---|---|
| `docs/DOKUMENTATIONSSTANDARD.md` | verbindlicher Aufbau für neue und geänderte Anleitungen |
| `docs/DOKUMENTATIONSINDEX.md` | zentrale Einordnung aktiver, technischer und historischer Textdateien |
| `docs/BENUTZERHANDBUCH.md` | vollständiges laiengerechtes Bedienhandbuch |
| `docs/DOCUMENTATION_CLASSIFICATION.json` | maschinenlesbare Dokumentklassifikation |
| `scripts/validate_documentation.py` | lokaler fail-closed Dokumentationsvalidator |
| `tests/test_documentation_contract.py` | fokussierter Vertragstest für Validator und Hilfeeinstiege |

## Vereinfachte Prüfarchitektur

Die eigenständige GitHub-Designprüfung wurde aus der Merge-Logik entfernt. Das Designmanifest bleibt als lokales Regelwerk für Oberfläche und Untermodule erhalten.

Der Dokumentationsvalidator läuft über das vorhandene lokale `test.sh`. Es gibt keinen zusätzlichen Dokumentationsworkflow und keinen zusätzlichen Required-Status-Kontext.

Ein kleiner GitHub-Kompatibilitäts-Preflight verwendet vorübergehend noch den bisherigen Statusnamen `Design manifest contract`, weil die vorhandene Branchregel diesen Namen erwartet. Er enthält keine Designprüfung. Nach Anpassung der Branchregel kann auch dieser Legacy-Name entfernt werden.

## Aktiv eingeordnet, aber nicht rückwirkend umgeschrieben

Technische Fachanleitungen bleiben fachlich getrennte Teilverträge. Ihre vollständige Neufassung erfordert jeweils eine eigene fachliche Abnahme, damit keine Sicherheits- oder Architekturaussage unbeabsichtigt verändert wird.

Historische Release-, Qualitäts- und Prüfnachweise bleiben unverändert. Sie belegen einen bestimmten Zeitpunkt, Teststand oder Versionszustand. Eine nachträgliche sprachliche Modernisierung könnte fälschlich eine erneute technische Prüfung suggerieren.

## Neue verbindliche Qualitätskriterien

Aktive Anleitungen müssen Ziel, Pflichtgrad, Voraussetzungen, Sicherung und Rückweg, nummerierte Schritte, Begründung, Weglassbarkeit, erwartetes Ergebnis, Fehlerfall, Abschlussprüfung und nächsten logischen Schritt enthalten.

## Abschlussprüfung dieser Iteration

- eigenständiger Dokumentationsbranch direkt von `main`
- zentrale Navigation vorhanden
- Einsteigerhandbuch vorhanden
- Hauptanleitungen überarbeitet
- historische Nachweise nicht verfälscht
- maschinenlesbare Klassifikation vorhanden
- lokaler Dokumentationsvalidator in `test.sh` integriert
- eigenständiger Dokumentationsworkflow entfernt
- Designmanifest vom Dokumentationsvertrag entkoppelt
- Designprüfung aus dem GitHub-Merge-Gate entfernt

## Nächster Schritt

Den lokalen Dokumentationsvalidator auf dem vollständigen finalen Checkout ausführen, reale Befunde einzeln korrigieren und danach `RELEASE_MANIFEST.json` genau einmal deterministisch regenerieren.