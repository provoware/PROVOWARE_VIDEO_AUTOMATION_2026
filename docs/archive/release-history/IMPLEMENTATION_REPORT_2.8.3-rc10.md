# Implementierungsbericht 2.8.3-rc10

## Ziel

Die Anwendung muss ohne Nutzerintervention bis in die Oberfläche starten. Reparierbare Konflikte werden vor dem Start automatisch behoben. Nicht startkritische Konflikte werden innerhalb der geöffneten Anwendung sichtbar gemacht, statt den Benutzer im Terminal festzuhalten.

## Vorausschauender Startvertrag

`STARTUP_CONTRACT.json` definiert die vier unveränderlichen Startstufen:

1. Programmpaket und System prüfen
2. Laufzeit automatisch vorbereiten
3. Projekt und Medienfunktionen prüfen
4. Oberfläche öffnen

Der Vertrag verbietet Rückfragen und verhindert, dass Qualitätswerkzeuge oder eine fehlerhafte FFmpeg-Listenauswertung künftig erneut zum Startblocker werden.

## Behobene Ursachen

### FFmpeg-AAC-Falscherkennung

FFmpeg-Encoderlisten verwenden zusätzliche Fähigkeitskennzeichen wie `A....D`. Die frühere Auswertung akzeptierte diese Zeichen nicht und meldete deshalb trotz vorhandenem AAC-Encoder einen Fehler. RC10 verwendet:

- eine tolerante Listenauswertung,
- einen realen Kurztest mit zwei Audioframes,
- den realen Test als maßgebliche Entscheidung.

### Unvollständige Umgebung wurde als bereit behandelt

Die bisherige virtuelle Umgebung wurde in einem temporären Pfad aufgebaut und anschließend verschoben. Konsolenskripte in virtuellen Umgebungen besitzen jedoch absolute Interpreterpfade. Nach dem Verschieben konnten Qualitätsprogramme fehlen oder auf einen nicht mehr vorhandenen Pfad zeigen.

RC10 erzeugt Umgebungen direkt an ihrem endgültigen, inhaltsadressierten Pfad:

```text
~/.local/share/VideoBatchFast/environments/
├── runtime-py<Version>-<Fingerabdruck>/
└── quality-py<Version>-<Fingerabdruck>/
```

Die Umgebung wird niemals nachträglich verschoben.

## Trennung der Verantwortlichkeiten

### Laufzeitumgebung

Enthält nur die Pakete, die zum Öffnen und Betreiben der Anwendung erforderlich sind. Sie wird vom Start automatisch aufgebaut und geprüft.

### Qualitätsumgebung

Enthält zusätzlich Ruff, MyPy, Bandit, pip-audit, pytest und Coverage. Sie wird ausschließlich für Qualitätsprüfung und Finalisierung benötigt. Ein fehlendes Entwicklerwerkzeug kann den Anwendungsstart nicht mehr verhindern.

## Nutzerführung

`scripts/bootstrap.py` zeigt ein kompaktes Startfenster. Technische Ausgaben werden in ein Protokoll geschrieben. Der Benutzer sieht nur den aktuellen Schritt. Der Prozess läuft im Hintergrund, damit das Startfenster ansprechbar bleibt.

Beim ersten erfolgreichen Start werden automatisch gepflegt:

- KDE-/Desktop-Menüeintrag,
- `~/.local/bin/videobatch-fast`,
- Doppelklickstarter im Projekt.

## Sicheres Degradieren

Fehlendes FFmpeg, FFprobe oder einzelne Codec-Fähigkeiten verhindern nicht das Öffnen der Oberfläche. Betroffene Produktionsfunktionen werden erst beim konkreten Auftrag blockiert und mit Lösung erklärt. Projekt-, Hilfe-, Datei- und Diagnosebereiche bleiben erreichbar.

## Prüfstand

- 183 Python-Tests bestanden
- 80,43 % Zeilenabdeckung
- 65,99 % Branch-Abdeckung
- 12/12 Anwendungssimulationen
- 16/16 visuelle Szenarien
- GUI-Rasterprofil-Roundtrip bestanden
- maximale Komplexität 28/30
- Architektur- und interne Qualitätsbefunde: 0
