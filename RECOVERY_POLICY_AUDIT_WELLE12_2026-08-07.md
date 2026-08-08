# PROVOWARE VIDEO AUTOMATION – Recovery Policy Audit Welle 12

Stand: 2026-08-07

## Ziel

Autonome, deterministische Recovery-Policy über die Domänen Transaction, Projekt, Backup, Config und Job-Journal. Reparaturen erfolgen ausschließlich, wenn der Zustand eindeutig und reproduzierbar ableitbar ist.

## Entscheidungsmatrix

| Befund | Aktion | Sicherheitsregel |
|---|---|---|
| gültiges Pending-WAL | REDO | Commit-Absicht ist dauerhaft dokumentiert |
| gleiches gültiges WAL überschreitet Retry-Budget | ROLLBACK | bytegenauer Vorzustand wird wiederhergestellt |
| beschädigtes/manipuliertes WAL | QUARANTINE | keine Nutzdatenanwendung |
| inkonsistente Backuphistorie | REBUILD | nur aus erneut verifizierten Archiven |
| verwaiste Revisionen | REBUILD | ausschließlich Metadatenbereinigung |
| beschädigtes Projekt / Config / Job-Quelle | QUARANTINE bzw. Diagnose | keine spekulative Nutzdatenreparatur |
| kein relevanter Befund | NONE | kein unnötiger Schreibzugriff |

## Recovery-Schweregrade und Health-Score

- warning: -8 Punkte
- error: -20 Punkte
- critical: -35 Punkte
- harte Befunde in mehreren Domänen erhalten zusätzlich eine Korrelationsstrafe.
- 90–100: healthy
- 60–89: degraded
- 0–59: critical

## Loop-Schutz

- maximales Retry-Budget pro identischer Fehlersignatur: 3 Versuche innerhalb 1 Stunde.
- Signatur basiert auf Domäne, Severity und Fehlercode.
- Nach Budgetverbrauch wird ein gültiges Pending-WAL nicht weiter per REDO wiederholt, sondern kontrolliert zurückgerollt.
- Recovery-Aktionen pro Lauf sind hart begrenzt.

## Automatische Diagnosepakete

Bei ausgeführter Recovery mit verbleibendem Status degraded/critical wird ein ZIP-Diagnosepaket angelegt. Es enthält ausschließlich Recovery-Metadaten und Auditdaten, keine Projekt-Nutzdaten.

## Disaster-Recovery-Simulator

Deterministische Mehrfachfehlerketten:

1. Crash direkt nach durable WAL → REDO
2. Torn Cross-File Transaction → REDO
3. beschädigtes WAL → QUARANTINE
4. verwaiste Revision → REBUILD
5. wiederholter identischer Fehler → Budget → ROLLBACK
6. korrelierter Config-/Job-Journal-Defekt → kritischer korrelierter Zustand

Alle 6/6 Szenarien bestanden.

## Externe technische Referenzen

- PostgreSQL 16, Write-Ahead Logging: WAL-Datensätze müssen vor den beschriebenen Datenänderungen dauerhaft gespeichert werden; nach Crash ist REDO möglich.
  https://www.postgresql.org/docs/16/wal-intro.html
- SQLite Atomic Commit: Hot Journals kennzeichnen abgebrochene Transaktionen und werden vor weiterer Nutzung zurückgerollt.
  https://sqlite.org/atomiccommit.html
- NIST SP 1339, OT Backup Quick Start Guide, 17.06.2026: Backups regelmäßig erstellen, testen und in Recovery-Übungen prüfen.
  https://www.nist.gov/publications/ot-backup-quick-start-guide
- CISA #StopRansomware Guide: Offline-Backups sowie regelmäßige Integritäts- und Disaster-Recovery-Tests.
  https://www.cisa.gov/stopransomware/ransomware-guide

## Grenzen

Nicht als physisch validiert gelten weiterhin Stromausfall, Kernelpanic, Hardware-/Controllerdefekte, tatsächliche Medienkorruption und reale Langzeit-Soak-Szenarien.
