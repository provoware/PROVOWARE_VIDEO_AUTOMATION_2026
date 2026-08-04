# Code-Qualitätsbericht 2.8.3-rc23

## Automatisierte Ergebnisse

- 268 von 268 Tests bestanden.
- Zeilenabdeckung: 82,83 % bei einem Gate von 80 %.
- Branch-Abdeckung: 66,37 % bei einem Gate von 65 %.
- Kombinierte Coverage: 79,56 %.
- Fehlerlabor: 12 von 12 bestanden.
- Anwendungssimulationen: 12 von 12 bestanden.
- Visuelle Szenarien: 18 von 18 bestanden.
- Architekturprüfung: 0 Befunde.
- Interne Qualitätsprüfung: 0 Befunde.
- Maximale Komplexität: 29.
- Größte Python-Datei: `ui.py` mit 686 Zeilen.
- Release-Manifest: 385 geprüfte Dateien.

## Strukturelle Qualität

- Kein Tk-Aufruf aus einem Hintergrundarbeiter.
- Begrenzte Ereignisqueue und begrenzter Executor.
- Future-Abbruch ohne hängenden Aktivitätszustand.
- Virtualisierte statt widgetbasierter Thumbnailansicht.
- Thumbnail- und Fehlercache mit festen Grenzen.
- Modultrennung für Runtime, Layout, Sortierung und Kachelansicht.
- Kontrastberechnung über relative Luminanz.
- Reproduzierbarer Großordnertest mit 20.000 Datensätzen.

## Externe Werkzeuge

Ruff 0.16.1, MyPy 2.3.0, Bandit 1.9.4 und pip-audit 2.10.1 waren in der isolierten Umgebung nicht installiert. Sie bleiben Freigabegates und wurden nicht als bestanden markiert.
