# Welle 25 – UI Phase 2: Quellenübersicht

## Ziel
Nur die erste der vier unteren Ausbauflächen wird mit vorhandener Medienlogik verbunden. Workflow-Module, Render-Profile und Historie / Logs bleiben Platzhalter.

## Umsetzung
- Quellenübersicht liest ausschließlich die bereits vorhandenen Sammlungen `audios` und `media`.
- Kompakte Anzeige: Gesamtzahl, Audioanzahl, Bilder-/Videoanzahl und nicht verfügbare Pfade.
- `Medienbibliothek öffnen` führt in die bestehende Medienseite (`page_index=1`) statt eine zweite Fachlogik aufzubauen.
- Keine neue Persistenz, keine Änderung an Render-, Scheduler- oder Mediensemantik.
- Die drei übrigen Ausbauflächen bleiben `Noch leer` / `Für spätere Inhalte`.

## Baseline-Bindung
Vor der Phase-2-Änderung wurde das validierte Phase-1-ZIP mit SHA-256, Dateianzahl, Ausgangscommit und vollständigem Dateiinventar gebunden.

## Validierung
- Fokussierte Phase-1/Phase-2-Vertragstests: 10/10 PASS.
- Vollständige Testsuite unter Xvfb: 696/696 PASS.
- `py_compile` für geänderten Produktcode und neue Tests: PASS.
- Ohne X-Display schlagen ausschließlich 8 bekannte GUI-Tests wegen `TclError: couldn't connect to display` fehl; unter Xvfb sind diese grün.

## Stable-Grenze
Externe Toolchain- und physische KDE-Nachweise werden durch diese UI-Iteration nicht ersetzt und nicht künstlich auf PASS gesetzt.
