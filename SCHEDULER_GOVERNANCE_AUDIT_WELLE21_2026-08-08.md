# Scheduler Governance Audit – Fortsetzungswelle 21

## Ergebnis

Fortsetzungswelle 21 erweitert den Scheduler von der reinen Wiederholungssteuerung zu einer persistenten Operations- und Governance-Schicht. Die Implementierung trennt Policy, Prioritätsqueue, Reconciliation, Operationssnapshot und Export in eigene Module, damit der Scheduler-Kern innerhalb der bestehenden Architekturgrenzen bleibt.

## Umgesetzte Verträge

1. Pause/Fortsetzen einzelner Serien einschließlich `pause_after_current` bei bereits laufendem Render.
2. Prioritäten 0–100 mit deterministischer Queue-Reihenfolge.
3. Persistente Konfliktqueue mit Grund, Earliest-Run und Catch-up-Deadline.
4. Globale Blackout-/Wartungsfenster einschließlich Zeitbereichen über Mitternacht.
5. Ressourcen-Preflight über realen freien Speicher des Ausgabe-Dateisystems.
6. Globale Parallelitätsgrenze bleibt ein prozessübergreifend gesicherter Renderbatch.
7. Reconciliation zwischen kanonischem VideoBatch-Plan und systemd-User-Units.
8. Konservative Behandlung unsicherer alter `running`-Zustände nach Neustart.
9. Scheduler-History und projektbezogener Operations-Export mit SHA-256-Manifest.
10. Konservatives Cleanup alter terminaler Serien ohne Verlust der Historie.
11. Schema-2-zu-3-Migration mit kanonischer Governance-Struktur und Standardpriorität.
12. Zentrale UI `Was läuft wann und warum?` mit Queuegrund, Priorität, Status und nächstem Termin.

## Gefundene und beseitigte Randfälle

- Projektbezogene Reconciliation durfte anfangs keine Queueeinträge anderer Projekte entfernen; der Prune arbeitet jetzt global sicher.
- Die Operationsansicht zählte zunächst Queueeinträge anderer Projekte; die Anzeige ist jetzt projektbezogen.
- Pause oder Löschen während eines aktiven Renderlaufs konnte theoretisch nach Worker-Abschluss wieder einen Folgetermin aktivieren; der Abschlussvertrag respektiert jetzt `pause_after_current` und `cancelled`.
- Der Worker überschritt vor dem Refactor die Komplexitätsgrenze; Queue-Gate, Governance-Preflight und Busy-Behandlung wurden getrennt.
- Die erste Coverage-Messung lag bei 64,92 % Branches knapp unter dem 65-%-Vertrag. Das Gate wurde nicht abgesenkt; zusätzliche Grenztests für Priorität 0/100 und Klassifizierung erhöhten die finale Branch-Coverage auf 65,07 %.

## Finaler Teststand

- 644/644 Tests bestanden.
- Coverage: 81,22 % Lines / 65,07 % Branches / 77,88 % kombiniert.
- Interne Codequalität: 327 Dateien / 2.831 Funktionen / maximale Komplexität 30 / 0 Befunde.
- Architektur: 0 Befunde.
- Ereignisarchitektur/-register: 0 Befunde.

## Nicht behauptet

Die sechs externen Stable-Gates bleiben offen: Ruff, MyPy, Bandit, pip-audit, physische KDE-X11-Abnahme und realer 96-Job-Slow-Target-Soak. Welle 21 verändert diesen externen Nachweisstatus nicht.
