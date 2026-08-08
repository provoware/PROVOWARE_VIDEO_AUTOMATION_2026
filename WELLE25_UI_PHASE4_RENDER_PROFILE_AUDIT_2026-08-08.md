# Welle 25 – UI Phase 4: Render-Profile

## Ziel
Nur die dritte der vier unteren Ausbauflächen wird mit bereits vorhandenen Render-/Ausgabeparametern verbunden. Quellenübersicht und Workflow-Module bleiben erhalten; Historie / Logs bleibt unverändert Platzhalter.

## Umsetzung
- `Render-Profile` liest ausschließlich bereits vorhandene Zustände: `resolution`, `codec`, `profile` und `output_dir`.
- Kompakte Anzeige: Profil, Auflösung, Codec und Ausgabeziel.
- `Render & Export öffnen` führt in die bestehende Queue-/Produktionsseite (`page_index=4`).
- Keine neue Render-, Queue-, Scheduler-, Preset- oder Persistenzsemantik.
- Ungültige oder noch nicht initialisierte Tk-Variablen werden defensiv als `—` angezeigt.
- Der Ausgabeordner wird nur für die Anzeige auf den letzten Pfadbestandteil verdichtet; der gespeicherte Pfad wird nicht verändert.
- `Historie / Logs` bleibt ausdrücklich `Noch leer` / `Für spätere Inhalte`.

## Baseline-Bindung
Die Iteration basiert auf `PROVOWARE_VIDEO_AUTOMATION_2026_WELLE25_UI_PHASE3_FINAL_GEFIXT(1).zip` und dessen SHA-256, dokumentiert in `ITERATION_BASELINE_WELLE25_UI_PHASE4_2026-08-08.json`.

## Validierung
- `py_compile` geänderter Produkt-/Testdateien: PASS.
- Phase 1/2/3/4 + bestehende Tab-/Medienverträge: 25/25 PASS unter Xvfb.
- Ereignisarchitektur: 0 Befunde.
- Ereignisregister: 0 Befunde bei 18 erzeugten Kennungen.
- Versionskonsistenz: PASS.
- Release-Literal-Prüfung: PASS, 261 sensible Dateien geprüft.
- Designregelwerk: PASS.
- Vollregression: gestartet, aber in der verfügbaren Laufzeit bei ca. 29 % durch das Ausführungszeitlimit beendet; daher ausdrücklich kein PASS-Nachweis.

## Stable-Grenze
Die bestehenden externen bzw. physischen Stable-Gates werden durch diese UI-Iteration weder erfüllt noch umgedeutet. Insbesondere bleiben die exakt gepinnten finalen Offline-Läufe von Ruff/MyPy/Bandit/pip-audit, die reale KDE-X11-Abnahme und der reale 96-Job-Langzeitrender offen.
