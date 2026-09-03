# Testbericht · VideoBatch Fast 2.8.3-rc24

## Aktueller Vollregressionsnachweis

Der vollständige aktuelle Testbestand wurde am 3. September 2026 auf dem Kandidaten `2e7d4350b0ccb0a5d0a69fa1033f0b1aded54e02` unter Ubuntu 24.04.4 LTS, Python 3.12.3 und Xvfb (`1920x1080x24`) ausgeführt.

- Workflow-Lauf: `33805992774`
- Evidence-Artefakt: `a32-full-suite-2e7d4350`
- Artefakt-ID: `9912964969`
- Artefakt-SHA-256: `592d17cf5120bdd7a1920ddf8dc3e7db14f4cf7233541ea350f00da71d9b9e2a`
- **468 Tests gesammelt**
- **466 Tests bestanden**
- **2 Tests übersprungen**
- **0 Tests fehlgeschlagen**
- Laufzeit der vollständigen Pytest-Suite: **31,38 s**

Damit ist der aktuelle 468-Test-Funktionsbestand ohne Testfehler durchgelaufen. Dieser Befund ersetzt die frühere 325-Test-Angabe als aktueller Vollregressionsnachweis.

## Coverage-Vertrag

Der nachgelagerte Coverage-Gate ist im selben Lauf **nicht bestanden** und bleibt ein eigener technischer Blocker:

- Zeilenabdeckung: **73,38 %** bei geforderten **80,00 %**
- Branch-Abdeckung: **59,01 %** bei geforderten **65,00 %**
- kombinierte Coverage: **70,54 %**
- Ergebnis `scripts/coverage_policy.py`: **BLOCKIERT**

Die funktional grüne 468-Test-Suite darf daher nicht als vollständige Releasefreigabe oder als bestandener Gesamt-Quality-Gate bezeichnet werden.

Der explizite nachgelagerte GUI-Rundtrip wurde in diesem Workflow nicht mehr ausgeführt, weil der Workflow nach dem roten Coverage-Gate fail-closed blieb. Die 468 Tests selbst liefen bereits vollständig unter Xvfb; eine separate reale Kubuntu/X11-Wiederholungsprüfung bleibt davon unberührt.

## Externe Qualitätswerkzeuge

Der exakte Offline-Qualitätslauf `33804721216` auf Produkt-Commit `934688e8a2f9e1344a91a959396aaef361ee9b67` ist abgeschlossen:

- Ruff 0.16.1: bestanden
- MyPy 2.3.0: bestanden
- Bandit 1.9.4: bestanden
- pip-audit 2.10.1: bestanden

Der vollständige Nachweis steht in `QUALITY_GATE_REPORT_2.8.3-rc24_save_.md`.

## Weitere bereits belegte Prüfungen

- 12/12 Anwendungssimulationen bestanden
- 12/12 Fehlerlabor-Szenarien bestanden
- 18/18 vorhandene visuelle Referenzszenarien bestanden
- 27/27 fokussierte Release-, Cache-, Tooltip- und Vorschauregessionen bestanden
- reale GUI-Stressprüfung mit 120 schnellen Medienklicks bestanden
- Version, Textkatalog, Release-Dateistatus, Dokumentrendering und interne Qualität bestanden
- P0-Kubuntu-CI-Matrix, kanonischer Evidence-Lauf `33791408050` auf `9823e790f8e67a6e0f406b132c37569e3b95d977`: 4/4 Kombinationen bestanden

Diese historischen Einzelbefunde ergänzen den aktuellen Vollregressionslauf, ersetzen ihn aber nicht.

## Neu geprüfte Fehlerpfade

1. FFmpeg 7+ erzeugt PNG-Vorschauen trotz atomarer `.partial`-Dateiendung, weil Ausgabeformat und Codec explizit gesetzt werden.
2. Beschädigte oder zu kleine Cacheziele werden vor dem Neuaufbau entfernt.
3. Verzögerte Tooltips werden bei Fokusverlust oder zerstörten Widgets sicher abgebrochen und bleiben innerhalb des Bildschirms.
4. Cache- und Hilfeaktionen verwenden zentrale Texte und erklären Wirkung sowie Schutzgrenze.
5. Historische Berichte und doppelte Baselines gelangen nicht mehr in aktive Releasepakete.

## Bewusst nicht behauptet

Stable ist weiterhin blockiert. Aktuell offen beziehungsweise nicht als bestanden behauptet werden insbesondere:

1. der Coverage-Vertrag mit 80 % Zeilen- und 65 % Branch-Abdeckung,
2. die reale Kubuntu/KDE-X11-/Wayland-Abnahme unter physischen Zielbedingungen,
3. der dokumentierte Langzeitrender mit großer Medienauswahl und langsamem externem Ziel.

PR #84 bleibt bis zur vollständigen Evidence-Kette ein Release-Kandidat und wird nicht als Stable bezeichnet.
