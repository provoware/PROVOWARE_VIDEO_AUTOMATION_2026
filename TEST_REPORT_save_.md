# Testbericht · VideoBatch Fast 2.8.3-rc25

## Aktueller Vollregressionsnachweis · Iteration 40D

Der aktuelle 40D-Testbestand wurde am 4. September 2026 auf Commit `58a8a06b5eae6992a6dd6e20ed3d4d0a982c7d4c` unter Ubuntu 24.04.4 LTS, Python 3.12.14 und Xvfb ausgeführt.

- Workflow-Lauf: `33845125393`
- **505 Tests gesammelt**
- **503 Tests bestanden**
- **2 Tests übersprungen**
- **0 Tests fehlgeschlagen**
- Vollregression: **21,91 s**
- separater Coverage-Lauf derselben Suite: **30,08 s**

Der zusätzliche 40D-Regressionsvertrag prüft den realen kanonischen UI-Lifecycle, sechs Shell-Seiten, Suche, Dashboardzustände, responsive Layoutpfade, KPI-Fehlerpfade und Debug-Umschaltung in einem isolierten Testprofil. Produktcode wurde für die Coverage-Schließung nicht verändert.

## Coverage-Vertrag 80/65

Der unveränderte Coverage-Vertrag ist **bestanden**:

- Zeilenabdeckung: **81,06 %** bei geforderten **80,00 %**
- Branch-Abdeckung: **65,79 %** bei geforderten **65,00 %**
- kombinierte Coverage: **78,04 %**
- Ergebnis `scripts/coverage_policy.py`: **BESTANDEN**

## Architektur und Paket

Im 40D-Nachweis wurden 115 Module, 1.140 Funktionen und 140 Klassen geprüft. Der Architekturaudit meldete **0 Befunde**. Das Release-Manifest und das deterministische Release-ZIP bestanden ebenfalls.

## Externe Qualitätswerkzeuge

Der letzte ausdrücklich freigegebene Offline-Qualitätsbericht bleibt `QUALITY_GATE_REPORT_2.8.3-rc24_save_.md`. Er dokumentiert den damaligen Lauf mit Ruff 0.16.1, MyPy 2.3.0, Bandit 1.9.4 und pip-audit 2.10.1. Für 40D wird kein nicht vorhandener rc25-Buildreport erfunden.

## Weitere belegte Prüfungen

- 12/12 Anwendungssimulationen bestanden
- 12/12 Fehlerlabor-Szenarien bestanden
- 18/18 vorhandene visuelle Referenzszenarien bestanden
- Kubuntu-CI-Matrix: 4/4 deterministische Kombinationen bestanden
- reale GUI-Stressprüfung mit 120 schnellen Medienklicks bereits bestanden

## Bewusst nicht behauptet

Stable ist weiterhin blockiert. Offen bleiben genau die realen Nachweise, die eine Headless-CI nicht ersetzen kann:

1. physische Kubuntu/KDE-X11-/Wayland-Abnahme auf dem finalen Kandidaten,
2. dokumentierter Langzeitrender mit großer Medienauswahl und langsamem externem Ziel.

Der Coverage-Blocker gehört seit Iteration 40D **nicht mehr** zu den offenen Stable-Gates.
