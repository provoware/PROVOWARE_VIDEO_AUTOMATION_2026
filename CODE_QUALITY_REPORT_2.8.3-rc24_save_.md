# Code-Qualitätsbericht · 2.8.3-rc24

## Interne Prüfung

- 203 geprüfte Python- und Skriptdateien
- 1.602 analysierte Funktionen
- maximale Komplexität 29
- interne Qualitätsbefunde 0
- Architekturprobleme 0
- Text-, Versions- und Release-Dateiverträge bestanden

## Tests und Coverage

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

Ruff 0.16.1, MyPy 2.3.0, Bandit 1.9.4 und pip-audit 2.10.1 sind für den aktuellen Kandidaten im provenienzgebundenen Offline-Lauf `34421827176` vollständig bestanden. Ein einzelner Bandit-B112-Befund niedriger Schwere wurde durch enges Abfangen von `tkinter.TclError` fachlich behoben und im vollständigen Wiederholungslauf verifiziert. Offen bleiben nur die physische KDE-X11-/Wayland-Abnahme und der reale Langzeitrender.
