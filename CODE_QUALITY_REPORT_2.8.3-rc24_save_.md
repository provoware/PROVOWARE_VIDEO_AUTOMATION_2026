# Code-Qualitätsbericht · 2.8.3-rc24

## Interne Prüfung

- 203 geprüfte Python- und Skriptdateien
- 1.602 analysierte Funktionen
- maximale Komplexität 29
- interne Qualitätsbefunde 0
- Architekturprobleme 0
- Text-, Versions- und Release-Dateiverträge bestanden

## Tests und Coverage

- 325/325 Tests im kanonischen Vollregressionsnachweis bestanden
- 82,43 % Statement-/Zeilenabdeckung
- 67,21 % Branch-Abdeckung
- 79,46 % kombinierte Coverage
- 18/18 vorhandene visuelle Referenzszenarien
- 12/12 Anwendungssimulationen
- 12/12 Fehlerlabor-Szenarien

## Exakte Offline-Qualitätswerkzeuge

Der separate Nachweis `QUALITY_GATE_REPORT_2.8.3-rc24_save_.md` belegt den reproduzierbaren Offline-Lauf:

- Ruff 0.16.1: bestanden, Rückgabecode 0
- MyPy 2.3.0: bestanden, Rückgabecode 0
- Bandit 1.9.4: bestanden, Rückgabecode 0
- pip-audit 2.10.1: bestanden, Rückgabecode 0
- Workflow `33801346178`, geprüfter Commit `048aa5733d9d0ce5fef872d25e0437fae08eab94`

## Zusätzliche Härtungen

- explizites PNG-Ausgabeformat für FFmpeg 7+
- Entfernung beschädigter Cacheziele vor Regeneration
- verzögerte, tastaturfähige und bildschirmgebundene Tooltips
- `xdg-open` wird vor lokalen Öffnungsaktionen validiert
- historische Nachweise liegen außerhalb aktiver Releaseartefakte
- maschinenlesbare Trennung releasefertiger und offener Unterlagen

## Verbleibende Stable-Gates

Stable bleibt ausschließlich wegen zweier noch nicht abgeschlossener Realabnahmen blockiert:

1. physische KDE-X11-/Wayland-Abnahme auf echten Zielsystemen,
2. Langzeitrender mit großer Medienauswahl auf langsamem externem Ziel.
