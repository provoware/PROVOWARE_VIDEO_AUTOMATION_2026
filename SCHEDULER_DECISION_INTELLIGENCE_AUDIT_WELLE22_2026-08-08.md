# Scheduler Decision Intelligence Audit – Fortsetzungswelle 22

## Ergebnis

Fortsetzungswelle 22 erweitert die Welle-21-Governance um eine rein lesende Entscheidungs- und Prognoseschicht. Die neue Logik verändert im Dry-Run weder Schedulerdateien noch Queue, Policy, systemd-Units oder Renderzustand.

## Umgesetzte Verträge

1. Robuste Laufzeitprognose aus realen, erfolgreich abgeschlossenen `BatchJournal`-Historien.
2. Median-basierte P50-Laufzeit und P75/P90-Sicherheitsbänder statt empfindlichem arithmetischem Mittel.
3. Konfidenzstufen `high`, `medium`, `low`, `none`; bei fehlender Historie keine erfundene ETA.
4. Matching zuerst über exakte Renderoptionen, danach über kompatible Codec/Profile/Resolution/Assignment-Signatur und erst zuletzt global.
5. P75-Ausgabegrößenprognose pro Vorkommen und für die noch verbleibende Serie, soweit reale historische Outputs verfügbar sind.
6. Dry-Run-Simulation ausschließlich für 24, 48 und 168 Stunden.
7. Erwartete Start-/Endzeiten unter Beachtung der globalen Ein-Render-Regel, Priorität, Wartungsfenster und Catch-up-Deadline.
8. Storage-Risk-Vorschau auf Basis realen freien Speicherplatzes plus historischer P75-Ausgabegröße.
9. Konkrete Diagnose `Warum startet dieser Job nicht?` mit Fehlercode, Schweregrad, Ursache und nächster Aktion.
10. Persistenter `dead_letter`-Zustand für dauerhaft nicht mehr vertrauenswürdig ausführbare eingefrorene Zustände.
11. Quellzustandsänderung führt vor Renderbeginn in Dead-Letter statt in eine unspezifische Endmarkierung.
12. Ungültige bzw. nicht mehr lesbare Projektzustände werden ebenfalls als Dead-Letter mit Reparaturhinweis beendet.
13. Operations-UI zeigt ETA, konkrete Ursache und nächste Aktion; separater Dry-Run-Tab zeigt 24/48/168-Stunden-Vorschau.
14. Die Prognoseansicht zeigt zusätzlich P75-Speicherbedarf, Konfidenz und prognostizierte Konflikte.

## Sicherheits- und Qualitätsentscheidungen

- Der Dry-Run ist strikt nebenwirkungsfrei: kein `systemctl`, kein Re-Arm, kein Renderstart, keine Scheduler-/Queue-/Policy-Schreiboperation.
- Unbekannte Laufzeit wird nicht durch einen erfundenen Default ersetzt. Dadurch werden nachfolgende Queue-Zeiten als unsicher markiert, wenn eine fehlende ETA die Kette beeinflusst.
- Nur erfolgreiche reale Batch-Journale werden für Laufzeitprognosen verwendet; fehlgeschlagene Batches verzerren das Erfolgsmodell nicht.
- Historische Ausreißer werden durch Median/P75/P90 robuster behandelt. Die Python-Dokumentation weist ausdrücklich darauf hin, dass der Median deutlich weniger ausreißerempfindlich als der Mittelwert ist.
- Diagnose trennt Symptom und Ursache und liefert eine konkrete nächste Aktion. Das folgt dem SRE-Grundsatz, nicht nur „was ist kaputt“, sondern auch „warum“ sichtbar zu machen.
- Speicher wird als Sättigungs-/Kapazitätsrisiko behandelt; eine Prognose darf warnen, aber ohne belastbare historische Ausgabegrößen keine scheinpräzise Speichermenge erfinden.

## Externe Referenzen

- Python `statistics`: https://docs.python.org/3/library/statistics.html – Median als robuste zentrale Lage und Quantilkonzept.
- Google SRE, Monitoring Distributed Systems: https://sre.google/sre-book/monitoring-distributed-systems/ – Trennung von Symptom/Ursache sowie Latenz, Fehler und Sättigung als zentrale Betriebsgrößen.

## Finaler Teststand

- 658/658 Tests bestanden.
- Coverage: 81,29 % Lines / 65,22 % Branches / 77,94 % kombiniert.
- Coverage-Mindestvertrag 80/65 bestanden.
- Interne Codequalität: 332 Dateien / 2.867 Funktionen / maximale Komplexität 30 / 0 Befunde.
- Architektur: 0 Befunde.
- Ereignisarchitektur/-register: 0 Befunde.
- Isolierte Python-Kompilierung bestanden.

## Nicht behauptet

Die sechs externen Stable-Gates bleiben offen: Ruff, MyPy, Bandit, pip-audit, physische KDE-X11-Abnahme und realer 96-Job-Slow-Target-Soak. Welle 22 verändert deren externen Nachweisstatus nicht.
