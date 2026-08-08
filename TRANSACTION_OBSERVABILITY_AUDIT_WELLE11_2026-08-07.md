# Transaction Observability & Corruption Recovery – Welle 11

## Ziel
Die Welle erweitert die Welle-10-WAL-Schicht um beobachtbare und kontrollierte Fehlerbehandlung, ohne beschädigte Recovery-Metadaten automatisch zu vertrauen.

## Implementiert
1. Beschädigte Pending-Journale werden vor Fehlerweitergabe atomar in `.videobatch-transactions/quarantine/` verschoben.
2. Persistente, begrenzte JSONL-Audit-Timeline mit Commit-, Recovery-, Quarantäne-, Health- und Rollback-Ereignissen.
3. Startup-Health-Check mit automatischem REDO für gültige Pending-WALs.
4. UI-Anzeige für Recovery-Gesundheit und letzte Audit-Ereignisse im Diagnosebereich.
5. Commit-Marker- und Revisionsregister-Korruption wird erkannt und quarantänisiert.
6. Verwaiste Revisionszuordnungen werden erkannt und können metadata-only entfernt werden.
7. Neue Transaktionen speichern bytegenaue Vorzustände; expliziter Rollback kann dadurch auch bereits teilweise geschriebene Cross-File-Transaktionen zurückführen.
8. Ungültige/kaputte JSON-Vorzustände bleiben rollbackfähig, weil der Snapshot raw/base64 + SHA-256 verwendet.
9. Backup- und Projektzustands-Recovery bleiben getrennte Fehlerdomänen.

## Sicherheitsinvarianten
- Quarantänisierte WAL-Daten werden niemals als Nutzdaten angewandt.
- Auditfehler blockieren keinen sicheren Commit.
- Rollback vertraut nur einem vollständig validierten Journal und prüft den SHA-256-Vorzustand.
- Metadata-only-Pruning löscht keine Nutzdateien.
- Startup-Recovery arbeitet unter dem vorhandenen exklusiven Transaktionslock.

## Fachliche Referenzen
- PostgreSQL WAL: Datenänderungen werden erst nach dauerhaftem Logeintrag angewandt; Crash-Recovery erfolgt per REDO.
- SQLite Atomic Commit: Journal-/Commitverfahren sollen einen Commit trotz Prozess-/OS-Ausfall atomar erscheinen lassen.
- NIST SP 1339 (2026): Backups regelmäßig erstellen, testen und in Recovery-Übungen prüfen.

## Nachweis
- Welle-11-Tests: 9/9 bestanden.
- Welle-10 + Welle-11 Transaktionstests: 19/19 bestanden.
- Vollsuite: 527/527 bestanden.
