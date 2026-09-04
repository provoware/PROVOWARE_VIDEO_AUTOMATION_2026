# VideoBatch Fast A33 – kanonische Konsolidierung

## Ausgangslage

Die Suche über Chat-/Dateibestände und Repository-Stände ergab zwei unterschiedliche Arten von „aktuell“:

- jüngstes belegtes lokales Vollpaket: `PROVOWARE_VideoBatch_Fast_A32.4_SINGLE_INSTANCE_WATCHDOG_FIX_2026-09-03.zip`
- historischer rekonstruierbarer A32.2-Ausgangspunkt: `8c6691cfaffd371d39fa5696c78f67114f83a7aa`
- kanonische A32.2-Rebase-Basis für Iteration 39A: `8755d5333b2f53ff8080655f8af39727db9b8c48`

A33 wurde in Iteration 39A auf die kanonische A32.2-Basis rebaset. Die dort bereits vorhandene Single-Instance-/Watchdog-Härtung bleibt erhalten.

## A33-Ziele

1. Startroutine: Hilfe, Diagnoseführung, Python-Preflight und klare Fehlerpfade.
2. Erscheinungsbild: kompaktere Sidebar, mehr Nutzfläche, Root-Shell-Füllvertrag, geringere Randabstände.
3. KDE-Skalierung: keine automatische Doppel-Skalierung mehr; Systemskalierung bleibt maßgeblich.
4. Fehlerrobustheit: Architekturprüfung verarbeitet unlesbare oder syntaktisch defekte Quelldateien als Befund statt selbst abzustürzen.
5. Rückrollbarkeit: ausschließlich über die Git-Historie und die dokumentierte kanonische Basis-SHA; keine doppelten Quellkopien im Projektbaum.

## Packaging-Hygiene

Der finale 39A-Diff-Audit hat die ursprünglich mitgeführten Quellkopien unter `Backup/A32.2_vor_A33/` aus der Integrations-Lineage entfernt. Der zentrale Release-Dateivertrag schließt `Backup/` weiterhin defensiv aus, damit künftig versehentlich erzeugte Sicherungskopien niemals Bestandteil eines Release-Pakets werden.

## Freigaberegel

A33 wird nur als technisch qualifizierter Konsolidierungsstand bezeichnet, wenn Startvertrag, Fokusregression, Vollregression, Architektur-Audit, Manifestbau und ZIP-Integritätsprüfung auf demselben Head erfolgreich sind. Eine physische KDE-X11-/Wayland-Abnahme und der reale Langzeitrender bleiben separate Stable-Gates. Das Coverage-Gate bleibt zusätzlich bei 80 % Zeilen / 65 % Branch fail-closed.
