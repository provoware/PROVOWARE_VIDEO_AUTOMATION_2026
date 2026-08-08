# Checkpoint Verification, Forensics & Safe Restore UX – Welle 14

## Ziel

Welle 14 erweitert den generationalen Checkpoint-Kern um nachvollziehbare, kryptografisch gebundene Recovery-Punkte und eine sichere Restore-Vorschau. Automatische oder interaktive Rücksetzungen dürfen nur auf vollständig verifizierte Generationen zielen; beschädigte Generationen werden isoliert statt gelöscht.

## Implementierte Schutzmechanismen

1. Jede neu erzeugte Generation enthält einen SHA-256-Generationsfingerprint über die kanonischen semantischen Manifestdaten. Änderungen an Domäne, Ziel, Snapshotreferenz, Dateigröße, Prüfsumme oder Generationsmetadaten werden damit erkannt.
2. Der Restore-Dry-Run verifiziert zunächst Checkpoint und Ziel-Dateisysteme und klassifiziert danach jede Zieldatei als `unchanged`, `replace`, `create` oder `delete`. Dabei werden aktuelle und Checkpoint-Prüfsummen, Größen und Restore-Datenmenge ausgewiesen.
3. Die automatische Recovery-Punktwahl priorisiert vollständige Abdeckung der geforderten Zustandsdomänen vor Aktualität. Eine neuere, aber unvollständigere Generation verdrängt daher keinen vollständigeren Recovery-Punkt.
4. Beschädigte Generationen werden atomar in `.videobatch-checkpoints/quarantine/generations/` verschoben. Sie bleiben für Forensik erhalten und werden aus dem aktiven Generation-Graph entfernt.
5. Die Recovery-Forensik-Timeline liest das bestehende durable Audit-Log robust; einzelne beschädigte JSONL-Zeilen machen die restliche Timeline nicht unlesbar.
6. `safe_restore_checkpoint()` blockiert standardmäßig Generationen mit geringerer Zustandsabdeckung und ebenso ältere gleichwertige Generationen, wenn ein neuerer verifizierter Punkt verfügbar ist. Bewusste Point-in-Time-Recovery muss diese Schutzschranke explizit aufheben.
7. Der Diagnosebereich zeigt eine read-only Restore-Vorschau mit Recovery-Punkt, Fingerprint, Änderungsanzahl, Aktionstypen, Datenmenge und Forensik-Ereignissen. Die Vorschau verändert keine Nutzdaten.
8. Beim Startup werden beschädigte Checkpoint-Generationen vor neuer Checkpointerzeugung isoliert.

## End-to-End-Nachweis

Der deterministische Welle-14-Testpfad führt aus:

`Checkpoint → Snapshot-Korruption → Diagnose → Quarantäne → Auswahl bester gültiger Generation → Restore-Dry-Run → Safe Restore → neuer Checkpoint`

Dabei wird geprüft, dass die beschädigte Generation nicht mehr aktiv auswählbar ist, der letzte vollständige verifizierte Zustand wiederhergestellt wird und anschließend wieder eine neue gültige Generation erzeugt werden kann.

## Architektur- und Sicherheitsgrenzen

- SHA-256 dient hier als kryptografischer Integritätsfingerprint, nicht als digitale Signatur oder Schutz gegen einen Angreifer, der gleichzeitig Manifest und alle lokalen Metadaten kontrolliert.
- Historische Welle-13-Generationen ohne explizites Fingerprintfeld bleiben lesbar; ihr Fingerprint wird deterministisch aus dem Manifest berechnet. Neue Generationen speichern den Fingerprint explizit und prüfen ihn beim Verify.
- Point-in-Time-Recovery bleibt bewusst möglich, muss bei einem älteren gleichwertigen Zustand aber explizit als absichtlicher Downgrade freigegeben werden.
- Physische Datenträger-, Kernel-, Controller- und Stromausfalltests bleiben außerhalb dieser softwareseitigen Simulation.

## Fachliche Referenzen

- PostgreSQL beschreibt Recovery Targets als bewusst wählbare frühere Wiederherstellungspunkte und unterscheidet diese von der Standard-Recovery bis zum Ende des WAL: https://www.postgresql.org/docs/19/runtime-config-wal.html
- SQLite beschreibt atomare Commits und „hot journals“ als Mechanismus, um einen nach Crash inkonsistenten Zustand vor weiterer Nutzung zu erkennen und zu reparieren: https://sqlite.org/atomiccommit.html
- NIST SP 1339 fordert regelmäßige Backups, Tests und die Überprüfung im Rahmen von Recovery-Übungen: https://www.nist.gov/publications/ot-backup-quick-start-guide
- NIST Contingency Planning beschreibt koordinierte technische Maßnahmen zur Wiederherstellung von Informationssystemen, Betrieb und Daten nach Störungen: https://csrc.nist.gov/topics/security-and-privacy/security-programs-and-operations/contingency-planning

## Validierung

- Welle-14-Tests: 8/8 bestanden.
- Kombinierte Welle-13/14-Tests nach Refactor: 19/19 bestanden.
- Vollregression in vier deterministischen Batches: 149 + 124 + 132 + 151 = 556/556 bestanden.
- Interne Codequalität: 295 Dateien, 2484 Funktionen, maximale Komplexität 29, 0 Befunde.
- Architektur: 129 Module, 1329 Funktionen, 164 Klassen, größte Datei 700 Zeilen, 0 Befunde.
- Ereignisarchitektur und Ereignisregister: 0 Befunde.
- Registry, Design, Text, Release-Literal, Release-Dateistatus, Dokumentation und isolierte Python-Kompilierung: bestanden.
