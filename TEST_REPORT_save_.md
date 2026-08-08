# Testbericht · VideoBatch Fast 2.8.3-rc24

## Vollständige Abschlussprüfung

- **323/323 automatisierte Tests bestanden** unter realem Xvfb
- 0 übersprungene Tests im finalen Lauf
- 82,43 % Statement-/Zeilenabdeckung
- 67,21 % Branch-Abdeckung
- 79,46 % kombinierte Coverage
- 12/12 Anwendungssimulationen bestanden
- 12/12 Fehlerlabor-Szenarien bestanden
- 18/18 vorhandene visuelle Referenzszenarien bestanden
- 27/27 fokussierte Release-, Cache-, Tooltip- und Vorschauregessionen bestanden
- reale GUI-Stressprüfung mit 120 schnellen Medienklicks bestanden
- Version, Textkatalog, Release-Dateistatus, Dokumentrendering und interne Qualität bestanden

## Neu geprüfte Fehlerpfade

1. FFmpeg 7+ erzeugt PNG-Vorschauen trotz atomarer `.partial`-Dateiendung, weil Ausgabeformat und Codec explizit gesetzt werden.
2. Beschädigte oder zu kleine Cacheziele werden vor dem Neuaufbau entfernt.
3. Verzögerte Tooltips werden bei Fokusverlust oder zerstörten Widgets sicher abgebrochen und bleiben innerhalb des Bildschirms.
4. Cache- und Hilfeaktionen verwenden zentrale Texte und erklären Wirkung sowie Schutzgrenze.
5. Historische Berichte und doppelte Baselines gelangen nicht mehr in aktive Releasepakete.

## Bewusst nicht behauptet

Stable ist weiterhin blockiert. Nicht abschließend belegt sind Ruff 0.16.1, MyPy 2.3.0, Bandit 1.9.4, pip-audit 2.10.1, die physische KDE-X11-Abnahme und der Langzeitrender mit großer Medienauswahl auf langsamem externem Ziel.
