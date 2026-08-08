# Scheduler System Audit – Welle 19 – 2026-08-08

## Ziel

SCHED-001 wird nach den abgeschlossenen Architektur-, Recovery- und Release-Härtungen als produktiver lokaler Scheduler freigegeben, ohne die weiterhin offenen externen Stable-Nachweise umzudeuten.

## Systemvertrag

- Zeitbasis: lokaler `systemd --user`-Timer mit `OnCalendar`, `AccuracySec=1s` und `Persistent=true`.
- Ausführung: headless Worker über den vorhandenen Projektstarter; keine offene Tk-Oberfläche erforderlich.
- Preflight: Projekt, Quellen, Ausgabe und Batch-Validierung müssen vor dem Planen frei von Blockern sein.
- Renderbindung: geordnete Audio-/Medienpfade werden semantisch gehasht; BatchOptions werden vollständig eingefroren.
- Quelldrift: Dateigröße und `mtime_ns` werden vor Start erneut geprüft.
- Sicherheitsgrenze: Projekt, Quellen und Starter dürfen keine symbolischen Links sein; Starter muss ausführbar sein.
- Doppelstartschutz: pro Projekt wird nur ein aktiver Plan zugelassen; finalisierte Pläne werden nicht erneut ausgeführt.
- Verspätung: außerhalb des konfigurierten Fensters wird `missed` statt eines überraschenden Spätstarts gesetzt.
- Energie: `systemd-inhibit` ist optional und nur für den tatsächlichen Renderlauf aktiv; `suspend` ist eine optionale Nachaktion.
- Kein Wake-on-Power-Off: ausgeschaltete Hardware wird nicht automatisch aufgeweckt.

## Robustheitskorrekturen aus der Tiefenprüfung

1. Volatile Projektmetadaten werden nicht in den Render-Fingerprint aufgenommen; dadurch invalidiert der automatische KPI-/Autosave-Pfad einen gerade angelegten Plan nicht selbst.
2. Renderrelevante Pfadänderungen und Reihenfolgeänderungen invalidieren den Plan weiterhin fail-closed.
3. Symlink-Prüfung findet vor `resolve()` statt, damit ein Link nicht durch Pfadauflösung unsichtbar wird.
4. Eine fehlgeschlagene optionale Energieaktion ändert einen vollständig erfolgreichen Render nicht in einen Renderfehler; der Energiefehler bleibt separat sichtbar.
5. Readiness-Abfragen des systemd-User-Managers sind für den KPI-Poll 30 Sekunden gecacht.

## Validierung

- 609/609 Gesamtregressionstests bestanden.
- Coverage: 80,96 % Lines / 65,49 % Branches / 77,80 % kombiniert; Mindestvertrag 80/65 bestanden.
- Interne Codequalität: 313 Dateien, 2.692 Funktionen, maximale Komplexität 29, 0 Befunde.
- Architektur: 0 Befunde.
- Ereignisarchitektur / Ereignisregister: 0 Befunde.
- Designvertrag und isolierte Python-Kompilierung: bestanden.

## Nicht als erledigt gewertet

Die vom Nutzer übersprungenen externen Stable-Nachweise bleiben offen: exakt gepinnte Ruff-/MyPy-/Bandit-/pip-audit-Evidence, physische KDE-X11-Abnahme und realer 96-Job-Slow-Target-Soak. Diese Punkte sind unabhängig von der internen Scheduler-Freigabe.
