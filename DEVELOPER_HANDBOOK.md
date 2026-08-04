# Entwicklerhandbuch – VideoBatch Fast 2.8.3-rc24

## 1. Zweck und Zielplattform

VideoBatch Fast ist eine lokale, offline nutzbare Linux-Anwendung für Medienauswahl,
Diashows und Videoverarbeitung. Die Oberfläche basiert auf Tkinter. FFmpeg und FFprobe
übernehmen Medienanalyse und Rendering. Nutzerdaten, Konfiguration und Protokolle
liegen ausschließlich in XDG-Benutzerpfaden.

## 2. Projektstruktur

- `src/videobatch_fast/`: Anwendungsmodule
- `resources/`: Texte, Themes und öffentliche Prüfressourcen
- `manifests/`: Verträge, Schemas und Reparaturkataloge
- `tests/`: automatisierte Regressionen
- `scripts/`: Build-, Audit-, Signatur- und Releasewerkzeuge
- `visual_inspection/`: erzeugte visuelle Prüfoberfläche
- `README.md`: Nutzerstart
- `STATUS.md`: aktueller Releasezustand
- `DEVELOPMENT_STATUS.json`: maschinenlesbarer Fortschritt
- `TEST_REPORT.md`: geprüfte Ergebnisse

Keine Python-Datei darf 700 Zeilen überschreiten. UI-freie Logik bleibt von Tkinter
getrennt. Hintergrundarbeiter dürfen Tk-Widgets niemals direkt verändern.

## 3. Start

```bash
chmod +x videobatch.sh
./videobatch.sh
```

Kernprüfung ohne externe Stable-Freigabe:

```bash
./test.sh --core
```

## 4. Medien- und Vorschauarchitektur

### Importdialog

Der Medienimport verwendet eine begrenzte GUI-Ereignisqueue, inkrementelles
Ordnerladen und eine virtualisierte Symbolansicht. Hintergrundthreads liefern nur
Daten. Widgetänderungen erfolgen im Tk-Hauptthread.

### Bereits ausgewählte Projektmedien

RC24 verwendet `SelectionPreviewController`:

1. Ein Auswahlereignis startet einen 180-ms-Debounce.
2. Die Fokuszeile bestimmt die gewünschte Datei.
3. Neue Anfragen ersetzen noch wartende Anfragen.
4. Genau ein Vorschauarbeiter verarbeitet Aufträge seriell.
5. Ein Generationstoken verwirft verspätete Ergebnisse.
6. Pillow prüft Datei, Größe und Pixelzahl.
7. `ImageTk.PhotoImage` wird ausschließlich im GUI-Hauptthread erzeugt.
8. Beim Schließen wird der Controller invalidiert und kontrolliert beendet.

Dieser Vertrag darf nicht durch zusätzliche per-Klick-Threads oder direkte
`PhotoImage(file=...)`-Aufrufe umgangen werden.

## 5. Fehlerbehandlung

Fehler dürfen die Anwendung nicht kommentarlos beenden. Der Nutzer erhält:

- eine verständliche Ursache,
- den geschützten Zustand,
- höchstens zwei vorrangige Lösungsaktionen,
- Protokollzugriff,
- bei Bedarf einen Debugexport.

Vorschaufehler bieten „Datei technisch prüfen“ und „Extern öffnen“. Defekte Dateien
bleiben unverändert.

## 6. Pfade und Rechte

Es werden keine Rootrechte benötigt. Wichtige Pfade:

- Konfiguration: `$XDG_CONFIG_HOME/VideoBatchFast`
- Status: `$XDG_STATE_HOME/VideoBatchFast`
- Cache: `$XDG_CACHE_HOME/VideoBatchFast`
- Diagnose: `$VIDEOBATCH_DIAGNOSTICS_DIR` oder sicherer Standardpfad

Diagnosewerkzeuge legen fehlende Elternordner selbst an. Ist ein vorgesehener
Statuspfad nicht beschreibbar, wird kontrolliert auf einen temporären Benutzerpfad
ausgewichen.

## 7. Tests

Pflicht je Änderung:

```bash
python -m compileall src
python -m pytest -q tests
```

Releasekandidat zusätzlich:

- Versionsvertrag
- Textressourcenvertrag
- Registryvertrag
- Architekturaudit
- interne Qualitätsprüfung
- Coverage: mindestens 80 % Zeilen und 65 % Branches
- Anwendungssimulationen
- Fehlerlabor
- GUI-Roundtrip
- visuelle Isolation
- Release-Manifest
- Frischprüfung aus dem fertigen ZIP

RC24 besitzt eine reale Xvfb-Stressregression mit 120 schnellen Klicks in der
bereits ausgewählten Medienliste.

## 8. Releasebau

```bash
python scripts/build_release_manifest.py
python scripts/validate_release_manifest.py
python scripts/package_release.py --output /pfad/VideoBatch_Fast_2.8.3-rc24.zip
python scripts/verify_release_zip.py /pfad/VideoBatch_Fast_2.8.3-rc24.zip
```

Das Paket muss zweimal unabhängig byteidentisch erzeugt werden. Danach wird es
mit Ed25519 signiert. Private Schlüssel dürfen niemals in Projekt, ZIP, Repository
oder Updatepaket gelangen.

## 9. Versionierung

SemVer:

- MAJOR: inkompatible Änderung
- MINOR: neue Funktion
- PATCH: Fehlerkorrektur oder Verbesserung
- RC-Suffix: noch nicht Stable-freigegeben

Bei jeder Iteration müssen mindestens `VERSION.json`, `manifest.json`,
`CHANGELOG.md`, `STATUS.md`, `TEST_REPORT.md` und `DEVELOPMENT_STATUS.json`
konsistent sein.

## 10. Stable-Grenze

Ein Release Candidate darf nicht als Stable bezeichnet werden, solange externe
Qualitätswerkzeuge, physische KDE-X11-/Wayland-Abnahme oder vorgeschriebene
Langzeittests offen sind. Automatisierte Xvfb-Prüfungen ersetzen keine physische
Desktopfreigabe.
