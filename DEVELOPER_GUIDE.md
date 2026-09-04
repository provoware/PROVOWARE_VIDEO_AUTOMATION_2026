# VideoBatch Developer Guide

## Ziel

Diese Anleitung führt neue Mitwirkende vom sauberen Arbeitszweig bis zum geprüften Pull Request. Sie ergänzt `DEVELOPER_HANDBOOK.md`, ersetzt aber keine Architektur- oder Sicherheitsverträge.

## Pflichtgrad

- **Pflicht:** eigener Branch, zielgerichtete Tests, vollständige Qualitätsprüfung, Manifestprüfung und Pull Request.
- **Empfohlen:** kleine, thematisch geschlossene Commits.
- **Optional:** zusätzliche lokale Sichtprüfung außerhalb der verpflichtenden Matrix.

## Voraussetzungen

- Git und Python gemäß Projektvertrag
- vollständig ausgechecktes Repository
- FFmpeg und ffprobe im erwarteten Systempfad
- keine ungesicherten lokalen Änderungen
- Kenntnis der betroffenen Module und Tests

## Sicherung und Rückweg

Vor jeder Änderung:

```bash
git status --short
git branch --show-current
git rev-parse HEAD
```

**Warum notwendig?** Damit Ausgangsbranch, Ausgangscommit und vorhandene Änderungen eindeutig dokumentiert sind.

**Kann entfallen?** Nein. Ohne Ausgangsnachweis ist eine spätere Fehlerzuordnung unzuverlässig.

## Schritt-für-Schritt-Anleitung

### Schritt 1: Aktuellen `main`-Stand prüfen

```bash
git fetch --prune origin
git switch main
git pull --ff-only
```

**Warum notwendig?** Neue Arbeit soll nicht auf einem bereits veralteten Stand beginnen.

**Kann entfallen?** Nur bei einer ausdrücklich reproduzierten historischen Untersuchung.

**Erwartetes Ergebnis:** Lokaler `main` entspricht `origin/main`.

### Schritt 2: Eigenen Branch erstellen

```bash
git switch -c <typ>/<kurze-beschreibung>-<datum>
```

Beispiel:

```bash
git switch -c fix/queue-recovery-20260806
```

**Warum notwendig?** Änderungen bleiben vom stabilen Hauptzweig getrennt und können kontrolliert geprüft oder verworfen werden.

**Kann entfallen?** Nein.

### Schritt 3: Änderungsumfang festlegen

Vor dem Codieren notieren:

- Ziel
- betroffene Dateien
- erwartetes Verhalten
- nicht zu verändernde Verträge
- erforderliche Tests
- Rückweg

**Warum notwendig?** Verhindert schleichende Nebenänderungen und unkontrollierte Großpatches.

### Schritt 4: Kleinste vollständige Umsetzung entwickeln

Eine Iteration soll mindestens eine vollständig nutzbare Verbesserung liefern. Sichtbare Attrappen oder unvollständige Sicherheitswege sind nicht zulässig.

**Kann ein unvollständiger Zwischenstand committed werden?** Lokal ja, aber nicht als freigabefähiger Pull Request.

### Schritt 5: Zielgerichtete Tests ausführen

Beispiel:

```bash
PYTHONPATH=src python3 -m pytest -q tests/test_hardening_2_8_2.py
```

Den Testpfad an die tatsächliche Änderung anpassen.

**Warum notwendig?** Schnelle Rückmeldung, bevor die vollständige Suite Zeit verbraucht.

**Kann entfallen?** Nein.

### Schritt 6: Vollständige Tests und Qualitätsprüfung ausführen

```bash
./test.sh
./quality.sh
```

`test.sh` verwendet temporäre Verzeichnisse für XDG-Zustand, Coverage, Diagnosen und visuelle Kandidaten. Änderungen an manifestierten Projektdateien gelten als Fehler.

**Warum notwendig?** Ein lokaler Modultest beweist nicht, dass Architektur, Persistenz, Sicherheit und andere Module unverändert funktionieren.

**Kann entfallen?** Nein vor einer Mergefreigabe.

### Schritt 7: Dokumentation prüfen

Bei jeder Funktionsänderung kontrollieren:

1. Muss `README.md` angepasst werden?
2. Ändert sich `START_HIER_save_.md` oder `docs/BENUTZERHANDBUCH.md`?
3. Benötigt `ERROR_HANDLING.md` eine neue Ursache oder Wiederherstellungsaktion?
4. Muss eine Entwickler- oder Releasebeschreibung aktualisiert werden?
5. Entspricht die neue Anleitung `docs/DOKUMENTATIONSSTANDARD.md`?

**Warum notwendig?** Eine technisch korrekte Funktion ist für Nutzer nicht vollständig, wenn Bedienung und Fehlerbehebung veraltet bleiben.

**Kann entfallen?** Nur wenn nachvollziehbar keine sichtbare Bedien-, Fehler- oder Vertragsänderung vorliegt.

### Schritt 8: Visuelle Kandidatenprüfung

Visuelle Prüfungen nur in einer temporären Kopie oder über den vorgesehenen Workflow ausführen.

**Warum notwendig?** Prüfartefakte dürfen den Quellbaum nicht unbemerkt verändern.

### Schritt 9: Build-Artefakte ausdrücklich erzeugen

```bash
./build_artifacts.sh
```

**Warum notwendig?** Buildprodukte sollen nur durch einen bewusst gestarteten, protokollierten Vorgang entstehen.

**Kann entfallen?** Bei rein internen Codeexperimenten ja. Vor einer Releaseprüfung nein.

### Schritt 10: Release-Manifest erzeugen und read-only prüfen

```bash
PYTHONPATH=src python3 scripts/build_release_manifest.py
PYTHONPATH=src python3 scripts/build_release_manifest.py --check --json
```

**Warum notwendig?** Jede release-relevante Datei wird mit Pfad, Größe, Modus und SHA-256 an den geprüften Stand gebunden.

**Kann entfallen?** Nein, wenn release-relevante Dateien geändert wurden.

### Schritt 11: Arbeitsbaum kontrollieren

```bash
git status --short
git diff --check
git diff --stat
```

**Erwartetes Ergebnis:** Nur geplante Dateien sind verändert; keine temporären Dateien, Secrets oder Buildreste sind enthalten.

### Schritt 12: Pull Request öffnen

Der Pull Request muss enthalten:

- Ziel und Nutzen
- exakte Basis
- umgesetzte Änderungen
- nicht veränderte Verträge
- Tests und Run-IDs
- offene Punkte
- Rückweg

Der PR bleibt Draft, bis alle verpflichtenden Prüfungen grün sind.

## Verbindliche Entwicklungsfolge

```text
Ausgangsstand belegen
→ Branch erstellen
→ Umfang festlegen
→ kleinste vollständige Änderung
→ zielgerichtete Tests
→ vollständige Qualitätsprüfung
→ Dokumentationsprüfung
→ visuelle Kandidatenprüfung
→ Build ausdrücklich erzeugen
→ Release-Manifest erzeugen
→ read-only Vollprüfung
→ Frischpaketprüfung
→ Pull Request und Matrix
```

## Kernmodule

- `naming.py`: stapelweite Zielreservierung
- `archive_service.py`: Journal und Recovery
- `runner.py`: terminale Ereignisgarantie und Prozesseskalation
- `os_sandbox.py`: Seccomp, Landlock und Ressourcenlimits
- `plugin_runtime.py`: Namespace-/Chroot-Launcher
- `updates.py`: unveränderlicher Kandidatenvertrag
- `internal_quality_gate.py`: AST-, Sicherheits- und Komplexitätsgrenzen

## Abhängigkeiten

- Laufzeit: `requirements.lock`
- Entwicklerwerkzeuge: `requirements-quality.lock`

Lockdateien verwenden keine Versionsbereiche. Jede Abhängigkeitsänderung benötigt:

1. begründete Versionsänderung;
2. aktualisierte Hashes;
3. neue Tests;
4. Sicherheitsprüfung;
5. Manifestaktualisierung;
6. Dokumentation der Auswirkungen.

## Fehler und Rücknahme

### Test schlägt fehl

1. Nicht weitere Änderungen stapeln.
2. Ersten reproduzierbaren Fehler isolieren.
3. Ursache mit kleinstem Patch beheben.
4. Zieltest erneut ausführen.
5. Danach vollständige Suite wiederholen.

### Branch ist hinter `main`

1. Aktuellen `main`-SHA erfassen.
2. Konfliktfreien Merge oder Rebase bewusst durchführen.
3. Release-Manifest neu erzeugen.
4. Alle verpflichtenden Prüfungen auf demselben neuen Head wiederholen.

### Änderung soll verworfen werden

Uncommittete Dateien nur gezielt zurücksetzen. Keine pauschalen Löschbefehle verwenden, solange unbekannte Dateien vorhanden sind.

## Abschlussprüfung

- Branch basiert auf aktuellem `main`
- nur geplante Dateien geändert
- Zieltests grün
- vollständige Tests grün
- Qualitätsprüfung grün
- Dokumentation aktuell
- Manifest synchron
- visueller Vertrag geprüft
- Arbeitsbaum sauber
- Pull Request nachvollziehbar

## Nächster Schritt

Architekturdetails in `DEVELOPER_HANDBOOK.md`, Dokumentationsregeln in `docs/DOKUMENTATIONSSTANDARD.md` und die vollständige Dateieinordnung in `docs/DOKUMENTATIONSINDEX.md` lesen.
