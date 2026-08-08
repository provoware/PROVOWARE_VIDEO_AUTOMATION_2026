# Recovery Checkpoints & Generational State Engine – Audit Welle 13

Stand: 2026-08-07

## Ziel

Fortsetzungswelle 13 erweitert die bisherige WAL-/Recovery-Architektur um konsistente, verifizierbare System-Checkpoints über mehrere zusammenhängende Zustandsdomänen. Der Schwerpunkt liegt auf einem nachweisbaren Wiederherstellungspunkt statt auf spekulativer Reparatur einzelner Dateien.

## Implementierter Vertrag

1. **Systemweite Generationen** – Projekt, Konfiguration, Retry-Queue, aktive/historische Job-Journale sowie Backup-Historie und deren Integritätsmetadaten können in einer gemeinsamen Generation aufgenommen werden.
2. **Verdeckte Erstellung** – neue Checkpoints entstehen zunächst ausschließlich in `.creating-*`. Erst nach vollständigem Snapshot, Manifest, Datei-fsync und Verzeichnis-fsync wird die Generation per atomarem Rename veröffentlicht.
3. **Stable-read-Kontrolle** – jede vorhandene Quelle wird nach dem Snapshot erneut auf Existenz, mtime und SHA-256 geprüft. Ändert sie sich während der Aufnahme, wird die Generation nicht veröffentlicht.
4. **Generation-Graph** – `graph.json` bildet die chronologische Parent-Kette der verifizierten Generationen. Der Graph wird aus den tatsächlich verifizierten Generationen rekonstruierbar gehalten.
5. **Crash vor Publish** – unvollständige `.creating-*`-Generationen bleiben unsichtbar und können beim nächsten Lauf sicher bereinigt werden.
6. **Crash nach Publish, vor Graph-Update** – die bereits vollständig verifizierte Generation wird beim Reconcile erneut entdeckt und in den Graph aufgenommen.
7. **Checkpoint-Integrität** – jeder Snapshot besitzt SHA-256 und Größenangabe; Manifest-Zählung und Gesamtgröße werden erneut geprüft.
8. **Restore-Probe** – vor einer echten Rücksetzung werden Checkpoint-Integrität, Snapshot-Lesbarkeit, freier Speicher und tatsächliche dauerhafte Schreibfähigkeit der Ziel-Dateisysteme per temporärem Write/fsync/Delete geprüft.
9. **Durables Restore-Journal** – ein Point-in-Time-Restore schreibt vor dem ersten Nutzdatenwrite ein `pending-restore.json`. Ein Crash mitten in der Rücksetzung wird beim Wiederanlauf durch Roll-forward auf exakt dieselbe Generation beendet.
10. **Fehlende Dateien als Zustand** – war eine Zustandsdatei im Checkpoint nicht vorhanden, wird dieser Existenzzustand beim Restore ebenfalls reproduziert.
11. **Point-in-Time-Recovery** – es wird deterministisch die neueste verifizierte Generation gewählt, deren Zeitstempel den Zielzeitpunkt nicht überschreitet.
12. **Retention/GC** – alte verifizierte Generationen können begrenzt entfernt werden; danach wird der Parent-Graph auf die verbleibende Kette neu aufgebaut. Während eines offenen Restore-Journals ist GC gesperrt.
13. **Startup-Integration** – ein unterbrochener Checkpoint-Restore wird vor dem Laden von Projekt und Konfiguration beendet. Nach erfolgreichem Recovery-Startup wird ein neuer Systemcheckpoint erzeugt und anschließend retention-bereinigt.

## Sicherheitsinvarianten

- Eine partielle Checkpoint-Erstellung wird nie als gültige Generation sichtbar.
- Eine beschädigte Generation darf nicht restauriert werden.
- Vor dem Restore findet eine nicht-destruktive Probe statt.
- Ein gestarteter Restore besitzt eine dauerhafte, idempotent wiederholbare Zielabsicht.
- Garbage Collection läuft nicht parallel zu einem offenen Restore.
- Point-in-Time-Auswahl verwendet nur vollständig verifizierte Generationen.
- Der Engine überschreibt keine Nutzdaten auf Basis eines beschädigten Snapshots.

## Externe technische Referenzen

- PostgreSQL Documentation, Write Ahead Log / Checkpoints / Recovery: https://www.postgresql.org/docs/current/runtime-config-wal.html
- SQLite, Atomic Commit: https://sqlite.org/atomiccommit.html
- NIST SP 1339, OT Backup Quick Start Guide, Juni 2026: https://www.nist.gov/publications/ot-backup-quick-start-guide
- NIST CSRC, Recovery Point Objective: https://csrc.nist.gov/glossary/term/recovery_point_objective

## Validierung

- Neue Welle-13-Checkpointtests: 11/11 bestanden.
- Kombinierte Welle-12/13-Recoverytests: 21/21 bestanden.
- Vollsuite unter Xvfb nach finaler Implementierung: siehe `FINAL_VALIDIERUNG_WELLE13_2026-08-07.txt`.
