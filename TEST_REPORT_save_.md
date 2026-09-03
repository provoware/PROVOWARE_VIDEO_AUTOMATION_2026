# Testbericht · VideoBatch Fast 2.8.3-rc24

## Vollständige Abschlussprüfung

- **325/325 automatisierte Tests bestanden** im kanonischen Vollregressionsnachweis
- 0 übersprungene Tests im belegten Vollregressionslauf
- 82,43 % Statement-/Zeilenabdeckung
- 67,21 % Branch-Abdeckung
- 79,46 % kombinierte Coverage
- 12/12 Anwendungssimulationen bestanden
- 12/12 Fehlerlabor-Szenarien bestanden
- 18/18 vorhandene visuelle Referenzszenarien bestanden
- 27/27 fokussierte Release-, Cache-, Tooltip- und Vorschauregessionen bestanden
- reale GUI-Stressprüfung mit 120 schnellen Medienklicks bestanden
- Version, Textkatalog, Release-Dateistatus, Dokumentrendering und interne Qualität bestanden
- P0-Kubuntu-CI-Matrix, kanonischer Evidence-Lauf `33791408050` auf `9823e790f8e67a6e0f406b132c37569e3b95d977`: 4/4 Kombinationen bestanden

## Externe Qualitätswerkzeuge

Der exakte Offline-Qualitätslauf `33801346178` auf Produkt-Commit `048aa5733d9d0ce5fef872d25e0437fae08eab94` ist abgeschlossen:

- Ruff 0.16.1: bestanden
- MyPy 2.3.0: bestanden
- Bandit 1.9.4: bestanden
- pip-audit 2.10.1: bestanden

Der vollständige Nachweis steht in `QUALITY_GATE_REPORT_2.8.3-rc24_save_.md`.

## Neu geprüfte Fehlerpfade

1. FFmpeg 7+ erzeugt PNG-Vorschauen trotz atomarer `.partial`-Dateiendung, weil Ausgabeformat und Codec explizit gesetzt werden.
2. Beschädigte oder zu kleine Cacheziele werden vor dem Neuaufbau entfernt.
3. Verzögerte Tooltips werden bei Fokusverlust oder zerstörten Widgets sicher abgebrochen und bleiben innerhalb des Bildschirms.
4. Cache- und Hilfeaktionen verwenden zentrale Texte und erklären Wirkung sowie Schutzgrenze.
5. Historische Berichte und doppelte Baselines gelangen nicht mehr in aktive Releasepakete.

## Bewusst nicht behauptet

Stable ist weiterhin blockiert. Noch nicht abschließend belegt sind ausschließlich die physische KDE-X11-/Wayland-Abnahme und der Langzeitrender mit großer Medienauswahl auf langsamem externem Ziel.
