# Code-Qualitätsbericht · 2.8.3-rc24

## Interne Prüfung

- 203 geprüfte Python- und Skriptdateien
- 1.602 analysierte Funktionen
- maximale Komplexität 29
- interne Qualitätsbefunde 0
- Architekturprobleme 0
- Text-, Versions- und Release-Dateiverträge bestanden

## Tests und Coverage

- 323/323 Tests bestanden
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

## Offene externe Gates

Ruff, MyPy, Bandit und pip-audit sind noch nicht abschließend in der exakt gesperrten Qualitätsumgebung ausgeführt. Physische KDE-Abnahme und Langzeitrender bleiben ebenfalls offen.
