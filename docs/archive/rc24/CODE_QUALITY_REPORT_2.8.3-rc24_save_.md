# Code-Qualitätsbericht · 2.8.3-rc24

## Interne Prüfung

- 203 geprüfte Python- und Skriptdateien
- 1.602 analysierte Funktionen
- maximale Komplexität 29
- interne Qualitätsbefunde 0
- Architekturprobleme 0
- Text-, Versions- und Release-Dateiverträge bestanden

## Tests und Coverage

Die folgenden Zahlen sind die kanonisch dokumentierte vollständige RC24-Regressionsbasis:

- 325/325 Tests bestanden
- 82,43 % Statement-/Zeilenabdeckung
- 67,21 % Branch-Abdeckung
- 79,46 % kombinierte Coverage
- 18/18 vorhandene visuelle Referenzszenarien
- 12/12 Anwendungssimulationen
- 12/12 Fehlerlabor-Szenarien

## Zusätzliche Härtungen

- explizites PNG-Ausgabeformat für FFmpeg 7+
- Entfernung beschädigter Cacheziele vor Regeneration
- verzögerte, tastaturfähige und bildschirmgebundene Tooltips
- `xdg-open` wird vor lokalen Öffnungsaktionen validiert
- historische Nachweise liegen außerhalb aktiver Releaseartefakte
- maschinenlesbare Trennung releasefertiger und offener Unterlagen

## Externe Qualitätsgates

Ruff 0.16.1, MyPy 2.3.0, Bandit 1.9.4 und pip-audit 2.10.1 besitzen einen provenienzgebundenen vollständigen Offline-Nachweis. Die aktuelle Qt-/Wayland-Änderung wird zusätzlich durch die verpflichtenden Repository- und Qt-Gates geprüft. Der Langzeitrender ist manuell bestätigt. **Vor Stable bleibt ausschließlich die erneute reale Kubuntu-26.04/KDE/Wayland-Sichtabnahme des geänderten UI-Stands bei 100 %, 150 % und 200 % offen.**
