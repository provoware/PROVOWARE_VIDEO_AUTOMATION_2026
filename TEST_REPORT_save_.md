# Testbericht · VideoBatch Fast 2.8.3-rc24

## Vollständige dokumentierte Regressionsbasis

Die folgenden Zahlen sind die kanonisch dokumentierte vollständige RC24-Regressionsbasis. Der aktuelle Qt-/Wayland-Stand wird zusätzlich über die verpflichtenden PR-Gates geprüft.

- **325/325 automatisierte Tests bestanden** in der dokumentierten vollständigen Regression
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
3. Verzöwerte Tooltips werden bei Fokusverlust oder zerstörten Widgets sicher abgebrochen und bleiben innerhalb des Bildschirms.
4. Cache- und Hilfeaktionen verwenden zentrale Texte und erklären Wirkung sowie Schutzgrenze.
5. Historische Berichte und doppelte Baselines gelangen nicht mehr in aktive Releasepakete.

## Bewusst nicht behauptet

Stable ist weiterhin blockiert. Die automatisierten Qualitäts- und Qt-/Wayland-Verträge sind grün und der Langzeitrender ist dokumentiert bestätigt. **Nicht abschließend belegt ist nach den UI-/Skalierungsänderungen nur noch die erneute reale Kubuntu-26.04/KDE/Wayland-Sichtabnahme bei 100 %, 150 % und 200 %.**
