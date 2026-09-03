# VideoBatch Fast A33 – kanonische Konsolidierung

## Ausgangslage

Die Suche über Chat-/Dateibestände und Repository-Stände ergab zwei unterschiedliche Arten von „aktuell“:

- jüngstes belegtes lokales Vollpaket: `PROVOWARE_VideoBatch_Fast_A32.4_SINGLE_INSTANCE_WATCHDOG_FIX_2026-09-03.zip`
- jüngster vollständig rekonstruierbarer Quellstand im Repository: A32.2-Branch, Ausgangs-SHA `8c6691cfaffd371d39fa5696c78f67114f83a7aa`

A33 verwendet den jüngeren rekonstruierbaren Quellstand als Basis. Die dort bereits vorhandene Single-Instance-/Watchdog-Härtung bleibt erhalten.

## A33-Ziele

1. Startroutine: Hilfe, Diagnoseführung, Python-Preflight und klare Fehlerpfade.
2. Erscheinungsbild: kompaktere Sidebar, mehr Nutzfläche, Root-Shell-Füllvertrag, geringere Randabstände.
3. KDE-Skalierung: keine automatische Doppel-Skalierung mehr; Systemskalierung bleibt maßgeblich.
4. Fehlerrobustheit: Architekturprüfung verarbeitet unlesbare oder syntaktisch defekte Quelldateien als Befund statt selbst abzustürzen.
5. Rückrollbarkeit: ersetzte A32.2-Dateien liegen unter `Backup/A32.2_vor_A33/`.

## Freigaberegel

A33 wird nur als technisch qualifizierter Konsolidierungsstand bezeichnet, wenn Startvertrag, Fokusregression, Vollregression, Architektur-Audit, Manifestbau und ZIP-Integritätsprüfung auf demselben Head erfolgreich sind. Eine physische KDE-X11-/Wayland-Abnahme und der reale Langzeitrender bleiben separate Stable-Gates.
