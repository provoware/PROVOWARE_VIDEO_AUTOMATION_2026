# Welle 25 – UI Phase 3: Workflow-Module

## Ziel
Nur die zweite der vier unteren Ausbauflächen wird mit bereits vorhandener Workflow-/Queue-Logik verbunden. Quellenübersicht bleibt erhalten; Render-Profile und Historie / Logs bleiben Platzhalter.

## Umsetzung
- `Workflow-Module` liest ausschließlich bestehende Zustände: `quick_mode`, `visual_effect`, `transition` und `jobs`.
- Kompakte Anzeige: Schnellmodus, Effekt, Übergang und Anzahl vorbereiteter Aufträge.
- `Workflow & Queue öffnen` führt in die bestehende Queue-/Produktionsseite (`page_index=4`).
- Keine neue Workflow-, Render-, Queue- oder Persistenzsemantik und keine zweite Fachlogik.
- Phase-2-Quellenübersicht bleibt unverändert funktionsfähig.
- `Render-Profile` und `Historie / Logs` bleiben ausdrücklich `Noch leer` / `Für spätere Inhalte`.

## Baseline-Bindung
Die Iteration basiert auf dem erneut bereitgestellten vollständigen Phase-2-ZIP mit SHA-256 `262f365fa221c0f77fbe7f8ac3c993def7f362fd5e011d6cb38f9c4630c39fdd`.

## Validierung
- `py_compile` geänderter Produkt-/Testdateien: PASS.
- Phase-1/2/3 + bestehende Tab-/Medienverträge: 21/21 PASS unter Xvfb.
- Ereignisarchitektur: 0 Befunde.
- Ereignisregister: 0 Befunde bei 18 erzeugten Kennungen.
- Versionskonsistenz: PASS.
- Release-Literal-Prüfung: PASS, 261 sensible Dateien geprüft.
- Designregelwerk: PASS.
- Vollregression: zweimal gestartet, aber in der verfügbaren Ausführungszeit bei ca. 55 % abgebrochen; daher ausdrücklich kein PASS-Nachweis.

## Stable-Grenze
Die sechs bestehenden externen/physisch erforderlichen Stable-Gates werden durch diese UI-Iteration nicht erfüllt oder umgedeutet. Insbesondere werden Ruff/MyPy/Bandit/pip-audit im finalen eingefrorenen Offline-Wheelhouse, reale KDE-X11-Abnahme und realer 96-Job-Langzeitrender nicht künstlich als bestanden markiert.
