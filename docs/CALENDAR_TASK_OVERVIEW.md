# Kalender-Aufgabenübersicht

Die kompakte Monatsansicht bleibt im Header erhalten. Über **Aufgaben** öffnet sich eine separate filterbare Übersicht.

## Filter
- Alle Einträge
- Heute
- Nächste 7 Tage
- Aktueller Monat
- Nur Aufgaben
- Nur Termine
- Offen / aktiv

## Datenquelle
Die Übersicht liest ausschließlich die versionierten `calendar_notes` der Projektdatei. Ungültige Datumswerte und leere Einträge werden sicher ignoriert.
