# Authenticated Checkpoints & Recovery Trust Chain – Welle 15

## Ziel

Welle 15 ergänzt die Recovery-Checkpoints um eine kryptografisch authentifizierte Vertrauenskette. Inhaltliche SHA-256-Fingerprints bleiben bestehen; neue Manifeste erhalten zusätzlich HMAC-SHA-256 mit Key-ID. Dadurch kann ein Angreifer ohne gültiges Schlüsselmaterial einen manipulierten Manifestinhalt nicht durch bloßes Neuberechnen des unkeyed SHA-256-Fingerprints legitimieren.

## Sicherheitsmodell

- Neue lokale Schlüssel werden mit kryptografisch sicherem Zufall erzeugt und mit restriktiven Dateirechten gespeichert.
- Ein externer Schlüssel kann über `VIDEOBATCH_CHECKPOINT_HMAC_KEY` bereitgestellt werden; er wird nicht in das Projekt eingebettet.
- Schlüssel-IDs sind Bestandteil der Authentifizierungsdaten. Rotation verwendet für neue Checkpoints einen neuen Schlüssel und behält alte Schlüssel zur Prüfung historischer Generationen.
- HMAC schützt nicht gegen einen vollständig kompromittierten Benutzerkontext, der zugleich Keyring und Checkpoints verändern kann. Für ein stärkeres Vertrauensmodell muss der Schlüssel außerhalb dieses Benutzerkontexts verwaltet werden.

## Generation Trust Chain

Jede neue Generation enthält:

- `parent_generation_id`
- `parent_fingerprint_sha256`
- `fingerprint_sha256`
- `authentication.algorithm = HMAC-SHA256`
- `authentication.key_id`
- `authentication.mac_sha256`

Damit werden fehlende Mittelgenerationen, eingeschobene unsignierte Generationen, Reordering durch Manifestmanipulation und Manifest-Replacement erkannt.

## Retention / GC

Planmäßige Retention darf die Kette nicht wie ein Angriff erscheinen lassen. Vor dem Entfernen eines historischen Präfixes wird deshalb ein authentifizierter `trust-prune-anchor.json` geschrieben. Nur dieser Marker legitimiert den fehlenden Präfix. Unangekündigte Löschungen oder gefälschte Marker bleiben Trust-Chain-Fehler.

## Audit-Kette

Neue Checkpoint-Auditzeilen besitzen:

- Hash der vorherigen authentifizierten Auditzeile,
- eigenen SHA-256-Eintrags-Hash,
- HMAC-SHA-256 über den vollständigen Eintrag.

Manipulation, Löschung innerhalb der Kette oder Austausch einer Zeile werden erkannt. Eine vollständige Trunkierung des letzten Kettenendes kann ohne externen Anchor naturgemäß nicht allein aus derselben Datei erkannt werden.

## Trust-Level

- `trusted`: authentifiziert und Parent-Kette gültig
- `authenticated-unlinked`: HMAC gültig, aber Verkettung nicht vollständig beweisbar
- `legacy-unverified`: historischer Checkpoint ohne Welle-15-Authentifizierung
- `untrusted`: Verkettung oder Authentifizierung nicht vertrauenswürdig

Der Trust-Level des automatisch ausgewählten Recovery-Punkts wird in der Restore-Vorschau angezeigt.

## Legacy-Migration

Legacy-Generationen werden nicht still hochgestuft. `migrate_legacy_checkpoints()` ist ein expliziter Migrationsvorgang, der die Generationen chronologisch neu verkettet, Fingerprints kontrolliert aktualisiert und anschließend authentifiziert.

## Validierung

- 10/10 neue Welle-15-Trust-/Chaos-Tests bestanden.
- 566/566 Gesamtregressionstests bestanden.
- interne Codequalität: 0 Befunde, maximale Komplexität 29.
- Architektur, Ereignisarchitektur, Ereignisregister, Registry, Design, Text, Version, Release-Literal, Release-Dateistatus und isolierte Kompilierung bestanden.

## Externe Referenzen

Die Umsetzung orientiert sich an NIST SP 800-57 zum Lebenszyklus kryptografischer Schlüssel, dem 2026 veröffentlichten Entwurf NIST SP 800-133 Rev. 3 zur sicheren Schlüsselgenerierung sowie OWASP-Empfehlungen zu Key Storage, Rotation und Key Lifecycle Management.
