# TODO – VideoBatch Fast nach Bildvergleichsanalyse 2026-08-07

## Regel

Nur Punkte mit realem Nutzen für Fehlerfreiheit, Soll-/Ist-Bildvergleich oder RC-Stabilität bleiben aktiv. Historische bereits erledigte Umsetzungsdetails werden nicht erneut als Arbeitsballast geführt.

## P0 – vor Stable zwingend

- [ ] **VIS-001 [M] Original-SOLL/IST-PNGs vergleichen** – Grund: ohne Binärbilder kein ehrlicher exakter Pixelvergleich. Abschluss: TXT/JSON/Diff-PNG mit Mean/RMSE/Changed/Edges/dHash/Aspect/BBox.
- [ ] **VIS-002 [M] KDE-X11-Sichtabnahme** – Grund: Xvfb deckt reale DPI-/Compositorabweichungen nicht ab. Abschluss: A-001 bis A-022 bei 1440×900, 1500×920, 1920×1080 und 90/105/125 %.
- [ ] **REL-001 [L] Langzeitrender auf realem System** – Grund: Langzeit-/I/O-/FFmpeg-Verhalten braucht physischen Nachweis.

## P1 – sichtbare Zielnähe

- [x] **UI-HOME-025 [M] Musterbild-Startseite Phase 1** – reale X11/Tk-Startschicht mit 4 Hauptkacheln, Infodashboard/Tipps, 4 bewusst leeren Ausbauflächen, Grundeinstellungen und Footer; bestehende Canonical-Funktionen bleiben darunter vollständig erreichbar.
- [x] **UI-ICON-001 [M] konsistentes Offline-Iconset** – lokales PNG-Set in 20/32/40 px; Sidebar und Hauptaktionen verwenden keine fontabhängigen Navigationssymbole mehr.
- [x] **KPI-001 [M] KPI-Untermetriken vervollständigen** – echte Bilder/Videos/Audio und Wartend/Abgeschlossen, keine Musterwerte.
- [x] **QUEUE-001B [M] Queue-Thumbnails ergänzen** – vorhandener persistenter Preview-Cache wird asynchron wiederverwendet; Tk-Bilder bleiben zentral referenziert.
- [x] **PREVIEW-001B [S] Video-Transport vervollständigen** – FFplay-basierter Transport mit Abspielen, Pause, Stopp und restart-basiertem Seek; keine zweite Decoderpipeline.

- [x] **START-001 [S] Startzeit-/Handshake-Telemetrie weiter schärfen** – strukturierte Phasenwerte werden im Ready-Marker, Bootstrap-Log und lokalen UI-Timing-Bericht gespeichert.

## P2 – sinnvoll, aber nicht vor P0/P1

- [x] **FOOTER-001 [S] realen Backupstatus anbinden** – verifizierte Projektzustands-Sicherung mit SHA-256/ZIP-Prüfung und realem letzten Sicherungszeitpunkt im Footer.
- [x] **DATA-001 [M] Persistentes Tagmodell** – normalisierte Pfad→Tag-Zuordnung in der Projektdatei, Tagfilter sowie echte „Unbenutzt“-Auswertung; keine Fake-UI.
- [x] **QUEUE-002 [M] aktuell nicht erforderlich** – Queue-Rendering bleibt auf 100 sichtbare Zeilen begrenzt; synthetischer Modelllauf: 2.000 Jobs ~0,52 ms, 10.000 Jobs ~3,05 ms ohne Tk-Rendering. Erst bei real gemessener UI-Latenz erneut öffnen.
- [x] **SCHED-001 [XL] Scheduler & Energy-Aware Automation** – persistente systemd-User-Planung, semantisch eingefrorener Renderzustand, Stale-Schutz, Wachhalteoption, Abschlussaktion und headless Worker sind in Welle 19 umgesetzt und regressionsgeprüft.

## Nachgewiesen in dieser Runde

- [x] Canonical-Shell ohne native helle Menüleiste im Primärpfad.
- [x] kompakte Topbar mit Suche sowie echten FFmpeg-/GPU-/Cachebadges.
- [x] KPI-Diagnoseprosa/Timestamps aus Primäransicht entfernt.
- [x] Drei-Spalten-Dashboard Quellen / Render Queue / Job Details.
- [x] Queue-Zielspalten und Jobdetailtabs umgesetzt.
- [x] Footer mit realen CPU/RAM/FFmpeg/GPU/Cache/Projektmetriken.
- [x] Scheduler bleibt sichtbar und ehrlich gesperrt.
- [x] visueller Screenshot-Runner prüft `CanonicalVideoBatchFastUI` statt Legacy-UI.
- [x] Bildvergleich um relative Größenbewertung, RMSE, Changed Ratio, Edge Difference, dHash, Aspect Delta und Diff-BBox erweitert.
- [x] Architekturgrenze durch separates `canonical_dashboard_detail_mixin.py` eingehalten.
- [x] 454 automatisierte Tests unter Xvfb bestanden.
- [x] UI-Ready-Handshake repariert: Bootstrap akzeptiert Schema 1 und 2; echte Schema-2-Ready-Meldung wird nicht mehr als Timeout verworfen.
- [x] Debug-Starter klassifiziert `UI_READY TIMEOUT` nicht mehr fälschlich als erfolgreichen Ready-Handshake.
- [x] A/B-Verify-Only repariert fehlendes Controller-`ab_contract.py` auch nach Application-Rollback.

Stable bleibt gesperrt, bis P0 einschließlich physischer Sichtabnahme und Langzeitrender auf demselben unveränderten Kandidaten abgeschlossen ist.

## Fortsetzungswelle 2 – 2026-08-07

- [x] Starttelemetrie: launch→run_app, Tk-Erzeugung, UI-Konstruktion, erster Idle-Flush und Gesamtzeit bis Ready.
- [x] KPI Medien: reale Bilder-/Videos-/Audio-Zählung.
- [x] KPI Queue: reale Wartend-/Abgeschlossen-Zählung.
- [x] Queuekopf: Suche + Statusfilter Alle/Wartend/Fertig/Fehler.
- [x] Job-Preview: Zoom −, Einpassen, Zoom + und Vollbild.
- [x] 454 Tests bestanden; Designregelwerk und Release-Dateistatus bestanden.

## Fortsetzungswelle 3 – 2026-08-07

- [x] Lokales, DPI-stabiles PNG-Iconset in 20/32/40 px eingeführt und Canonical-Sidebar/Actionbar angebunden.
- [x] Queue-Thumbnails nutzen den vorhandenen persistenten Preview-Cache asynchron; kein zweites Cache-System.
- [x] Jobauswahl lädt die reale Jobquelle direkt in die vorhandene Previewpipeline.
- [x] Reale FFplay-Videosteuerung: Abspielen, Pause/Weiter, Stopp und Seek durch kontrollierten Neustart am Zielzeitpunkt.
- [x] Projektzustands-Backup als verifiziertes ZIP mit Manifest, SHA-256 und atomarer Historie; Footer zeigt nur echte Sicherungen.
- [x] 470 automatisierte Tests unter Xvfb bestanden.

- [x] UI-Ready-Pfad ohne synchrones Idle-Drain: echter Xvfb-Prozess meldet Ready nach ca. 0,75 s; verschachtelte Workflow-Grid-Geometrieupdates werden per `after_idle` zusammengefasst.


## Fortsetzungswelle 4 – 2026-08-07

- [x] Topbar bei dynamischen Badge-/Statustexten neu berechnen; Suche sowie Hilfe/Einstellungen haben Vorrang, redundanter Status wird zuerst ausgeblendet.
- [x] Zoom-/Viewport-Matrix erweitert: 1440×900 @ 90/125 %, 1500×920 @ 105 %, 1920×1080 @ 100/125/140 %.
- [x] 22/22 visuelle Szenarien ohne Clipping-/Sichtbarkeitsvertragfehler bestanden; geprüfte Baselines aktualisiert.
- [x] Screenshot-Runner erkennt zu kleine Xvfb-/Desktop-Anzeigen und verweigert dadurch verfälschte Offscreen-Schwarzvergleiche.
- [x] Persistentes Tagmodell und echte „Unbenutzt“-Filterung abgeschlossen.
- [x] Release-Literal-Hygiene bereinigt: Version in Langzeitrender-/Workflowpfaden wird aus VERSION.json abgeleitet.
- [x] 480 automatisierte Tests unter Xvfb bestanden; interne Codequalität, Architektur- und Ereignisgate ohne Befund.


## Fortsetzungswelle 5 – 2026-08-07

- [x] Sicherungsmanager mit verifizierter Historie, manueller Prüfung und sicherer Wiederherstellung als neue Projektkopie.
- [x] Aktive Projektdatei im Sicherungsdialog gegen versehentliches Überschreiben geschützt.
- [x] Backuphistorie liefert nur noch vorhandene und erneut vollständig verifizierte Archive an die UI.
- [x] Scheduler-Voraussetzungsdiagnose für FFmpeg, FFprobe, systemd-inhibit und systemctl ergänzt; Checkpoint 5 bleibt unabhängig davon gesperrt.
- [x] 485 automatisierte Tests bestanden.
- [x] 22/22 visuelle Szenarien gegen die geprüften Welle-4-Baselines bestanden.
- [x] Codequalität, Architektur, Ereignisarchitektur, Designregelwerk und Release-Literal-Hygiene ohne Befund.

## Fortsetzungswelle 6 – 2026-08-07

- [x] Shutdown gegen doppelte/reentrante Schließanforderungen geschützt.
- [x] Shutdown garantiert Fensterbeendigung auch bei Autosave-, Settings- oder Hintergrunddienstfehlern; Teilfehler werden protokolliert.
- [x] FFplay-Prozess nach erzwungenem SIGKILL begrenzt reap-ed und Preview-Poll vor Shutdown abgebrochen.
- [x] Backupvertrag auf echte JSON-Projektobjekte begrenzt.
- [x] Backup-Verifikation gegen ungewöhnlich große entpackte Projekt-/Manifestdaten gehärtet.
- [x] Projekt-Schemaversion in neuen Backups gespeichert und gegen Payload validiert; Legacy-Backups bleiben lesbar.
- [x] 490 automatisierte Tests bestanden.
- [x] 22/22 visuelle Szenarien bestanden.
- [x] Codequalität, Architektur, Ereignisarchitektur, Design-, Text-, Versions- und Release-Literal-Verträge bestanden.
## Fortsetzungswelle 7 – 2026-08-07

- [x] Aktive Projektdateien vor JSON-Parsing auf 16 MiB begrenzt; übergroße Zustände werden sicher quarantänisiert.
- [x] Aktive Projektdateien müssen ein JSON-Objekt enthalten; Arrays/Skalare werden nicht still normalisiert.
- [x] Unbekannte zukünftige Projektschemata werden nicht still heruntergestuft, sondern quarantänisiert und durch einen sicheren neuen Zustand ersetzt.
- [x] Backup-Verifikation weist doppelte ZIP-Einträge und unerwartete Zusatzdateien explizit ab.
- [x] Backup-Manifestschema wird strikt auf Version 1 geprüft.
- [x] Backuphistorie und Wiederherstellung verwenden die gemeinsame atomare Safe-I/O-Schicht inklusive Verzeichnis-Fsync.
- [x] 496 automatisierte Tests bestanden.
- [x] 22/22 visuelle Szenarien bestanden.
- [x] Codequalität, Architektur, Ereignisarchitektur, Design-, Text-, Versions-, Registry- und Release-Literal-Verträge bestanden.


## Fortsetzungswelle 8 – 2026-08-07

- [x] Backup-ZIP vor atomarem Replace per Datei-fsync synchronisiert; Zielverzeichnis danach fsync-synchronisiert.
- [x] Crash-Recovery für fehlende, beschädigte oder veraltete `history.json`: verifizierte Archive werden direkt wiederentdeckt und Historie selbstgeheilt.
- [x] Verwaiste neue Backups nach Crash werden anhand Manifest-Zeit + Mikrosekunden-Dateiname korrekt als neueste Sicherung einsortiert.
- [x] Konservative automatische Rotation auf 30 verifizierte Projektbackups eingeführt; unbekannte/defekte Dateien werden nie automatisch gelöscht.
- [x] Rotationslöschungen werden per Verzeichnis-fsync dauerhaft synchronisiert.
- [x] Simulierte `os.replace`-/Commitfehler hinterlassen das alte Ziel beziehungsweise keinen falschen fertigen Backupzustand.
- [x] Reine Backupstatus-Abfragen schreiben unveränderte Historien nicht erneut; unnötige periodische I/O-/fsync-Last entfernt.
- [x] 504 automatisierte Tests unter Xvfb bestanden.
- [x] Codequalität, Architektur, Ereignisarchitektur, Design-, Text-, Versions-, Registry- und Release-Literal-Verträge bestanden.
- [!] Dedizierter isolierter Screenshot-Runner erreichte in dieser Ausführungsumgebung das Kommando-Zeitlimit; deshalb kein neuer Welle-8-Visuellnachweis behauptet. Welle-7-Nachweis bleibt historisch bestehen.

## Fortsetzungswelle 9 – 2026-08-07

- [x] Fault-Lab von 15 auf 21 reproduzierbare, zerstoerungsfreie Szenarien erweitert.
- [x] ENOSPC beim Datei-fsync: letzter gueltiger Zielzustand bleibt erhalten; Tempdatei wird bereinigt.
- [x] EACCES bei Tempdateierzeugung: vorhandenes Ziel bleibt unveraendert.
- [x] PID-markierte atomare Tempdateien und Restart-Cleanup fuer nachweislich tote Schreibprozesse eingefuehrt; lebende Schreiber werden nicht beruehrt.
- [x] Prozessuebergreifender Linux/POSIX-Backup-Lock mit begrenztem Timeout eingefuehrt; Kernel gibt Lock nach SIGKILL automatisch frei.
- [x] Parallele Projektbackups serialisiert; 2 konkurrierende Prozesse erzeugen 2 verifizierte Archive und 2 Historieneintraege ohne Lost Update.
- [x] Beschädigte Backuphistorie wird beim Wiederanlauf aus verifizierten Archiven rekonstruiert.
- [x] Maschinenlesbare Crash-Matrix und Recovery-Audit angelegt.
- [x] 508/508 automatisierte Tests unter Xvfb bestanden.
- [x] Codequalitaet, Architektur, Ereignisarchitektur, Ereignisregister, Design-, Text-, Versions-, Registry-, Release-Literal- und Compile-Vertraege bestanden.
- [!] Stable-Gates VIS-001, VIS-002, REL-001 und SCHED-001 bleiben unveraendert ehrlich offen; Welle 9 simuliert keinen physischen Strom-/Datentraegerdefekt.


## Fortsetzungswelle 10 – 2026-08-07

- [x] Durable Write-Ahead-Journal für logisch zusammengehörige JSON-Dateien eingeführt.
- [x] Monotone Revisionen und optimistische Expected-Revision-Konflikterkennung gegen Lost Updates eingeführt.
- [x] Crash vor erstem Datenwrite und exakt zwischen zwei Cross-File-Writes per REDO-Recovery abgedeckt.
- [x] Manipulierte Journale, Pfad-Escapes und doppelte Ziele fail-closed abgewiesen.
- [x] Backuphistorie + SHA-256-Integritätsmetadaten produktiv als Cross-File-Transaktion integriert.
- [x] History/Meta-Inkonsistenz führt zur Rekonstruktion aus verifizierten Backup-Archiven.
- [x] Maschinenlesbare Crash-Matrix und Transaction-Recovery-Audit ergänzt.
- [x] 518/518 automatisierte Tests in vollständigen Testdatei-Batches unter Xvfb bestanden.
- [x] Codequalität, Architektur, Ereignisarchitektur, Ereignisregister, Design-, Text-, Versions-, Release-Literal-, Release-Dateistatus- und Compile-Verträge bestanden.
- [!] Stable-Gates VIS-001, VIS-002, REL-001 und SCHED-001 bleiben unverändert offen.

## Fortsetzungswelle 11 – 2026-08-07

- [x] Beschädigte Pending-Journale atomar quarantänisiert statt lediglich abgewiesen.
- [x] Persistente Transaction-Audit-Timeline mit Rotation ergänzt.
- [x] Startup-Konsistenzprüfung mit automatischem REDO gültiger Pending-WALs integriert.
- [x] Recovery-Gesundheitsstatus und letzte Audit-Ereignisse im Diagnosebereich sichtbar gemacht.
- [x] Beschädigte Commit-Marker und Revisionsregister erkannt und quarantänisiert.
- [x] Verwaiste Revisionen erkannt und metadata-only bereinigbar gemacht.
- [x] Bytegenaue Rollback-Vorzustände für Cross-File-Transaktionen ergänzt.
- [x] Rollback nach halbem Write sowie Backup-/Projektzustands-Doppelcrash reproduzierbar getestet.
- [x] 527/527 automatisierte Tests unter Xvfb bestanden.
- [x] Codequalität, Architektur, Ereignis-, Registry-, Design-, Text-, Versions- und Release-Verträge bestanden.
- [!] Stable-Gates VIS-001, VIS-002, REL-001 und SCHED-001 bleiben unverändert offen.

## Fortsetzungswelle 12 – 2026-08-07

- [x] Deterministische autonome Entscheidungsmatrix REDO / ROLLBACK / QUARANTINE / REBUILD eingeführt.
- [x] Recovery-Schweregrade und Health-Score 0–100 mit Korrelationsgewichtung eingeführt.
- [x] Projekt, Backup, Config, Transaction und Job-Journal als getrennte Recovery-Domänen korreliert.
- [x] Retry-Budget und Recovery-Loop-Schutz mit 3 identischen Versuchen pro Stunde eingeführt.
- [x] Budget-Eskalation auf kontrollierten Rollback bei wiederholt scheiternder identischer WAL-Recovery umgesetzt.
- [x] Backuphistorie ausschließlich aus erneut verifizierten Archiven deterministisch rebuildbar gemacht.
- [x] Automatische datensparsame Recovery-Diagnosepakete ergänzt.
- [x] Disaster-Recovery-Simulator mit 6 deterministischen Mehrfachfehlerketten ergänzt; 6/6 bestanden.
- [x] Recovery-Health-Score und gewählte Policy-Aktion im Diagnosebereich sichtbar gemacht.
- [x] 537/537 automatisierte Tests unter Xvfb bestanden.
- [x] Codequalität, Architektur, Ereignis-, Registry-, Design-, Text-, Versions-, Release-, Dokumentations- und Compile-Verträge bestanden.
- [!] Stable-Gates VIS-001, VIS-002, REL-001 und SCHED-001 bleiben unverändert offen.

## Fortsetzungswelle 13 – 2026-08-07

- [x] Konsistente System-Checkpoints über Projekt, Config, Retry-Queue, Job-Journale und Backup-Metadaten eingeführt.
- [x] Checkpoint-Erstellung über versteckte Staging-Generation mit Datei-/Verzeichnis-fsync und atomarem Publish gehärtet.
- [x] Zweiphasige Stable-read-Prüfung verhindert gemischte Generationen bei parallel veränderten Zustandsdateien.
- [x] Rekonstruierbaren Generation-Graph mit Parent-Kette eingeführt.
- [x] Crash vor Publish hinterlässt keine sichtbare Generation; Crash nach Publish wird beim Graph-Reconcile selbstgeheilt.
- [x] Restore-Probe prüft Checkpoint-Integrität, freien Speicher und echte dauerhafte Schreibfähigkeit der Ziel-Dateisysteme.
- [x] Durables Restore-Journal ermöglicht idempotentes Roll-forward nach Crash mitten in einer Multi-Datei-Rücksetzung.
- [x] Deterministische Point-in-Time-Recovery auf den neuesten verifizierten Checkpoint <= Zielzeitpunkt eingeführt.
- [x] Retention/GC mit Graph-Rebuild eingeführt; während eines offenen Restore-Journals gesperrt.
- [x] Startup beendet unterbrochene Checkpoint-Restores vor Config-/Projektload und erzeugt danach einen neuen Recovery-Checkpoint.
- [x] 548/548 automatisierte Tests unter Xvfb bestanden.
- [x] Codequalität, Architektur, Ereignis-, Registry-, Design-, Text-, Versions-, Release-, Dokumentations- und Compile-Verträge bestanden.
- [!] Stable-Gates VIS-001, VIS-002, REL-001 und SCHED-001 bleiben unverändert offen.


## Fortsetzungswelle 14 – 2026-08-07

- [x] SHA-256-Generationsfingerprints über kanonische Checkpoint-Manifestdaten eingeführt.
- [x] Restore-Dry-Run mit detailliertem Hash-/Größen-Diff und `unchanged`/`replace`/`create`/`delete` umgesetzt.
- [x] Automatische Recovery-Punktwahl priorisiert vollständige Zustandsdomänen vor bloßer Aktualität.
- [x] Beschädigte Generationen werden beweissicher quarantänisiert und aus dem aktiven Generation-Graph entfernt.
- [x] Robuste Checkpoint-Forensik-Timeline ergänzt.
- [x] Safe-Restore blockiert schlechtere Domänenabdeckung und unbeabsichtigte ältere gleichwertige Generationen.
- [x] Read-only Restore-Vorschau im Diagnosebereich integriert; Vorschau verändert keine Nutzdaten.
- [x] End-to-End-Pfad Checkpoint → Korruption → Diagnose → Auswahl → Probe → Restore → Re-Checkpoint reproduzierbar getestet.
- [x] Architekturrefactor hält `checkpoint_store.py` bei 683 und `ui.py` bei maximal 700 Zeilen.
- [x] 556/556 automatisierte Tests in vollständigen Xvfb-Testdatei-Batches bestanden.
- [x] Codequalität, Architektur, Ereignis-, Registry-, Design-, Text-, Release-, Dokumentations- und Compile-Verträge bestanden.
- [!] Stable-Gates VIS-001, VIS-002, REL-001 und SCHED-001 bleiben unverändert offen.

## Fortsetzungswelle 15 – 2026-08-07

- [x] HMAC-SHA-256-authentifizierte Checkpoint-Manifeste mit versioniertem Auth-Envelope und Key-ID eingeführt.
- [x] Verkettete Parent-Generation-/Parent-Fingerprint-Struktur gegen Löschen, Einschieben und Reordering gehärtet.
- [x] Manipulationssichere Audit-Hash-/HMAC-Kette für neue Checkpoint-Forensikereignisse eingeführt.
- [x] Key-Rotation mit historischer Verifizierbarkeit alter Generationen umgesetzt.
- [x] Trust-Level je Recovery-Punkt (`trusted`, `authenticated-unlinked`, `legacy-unverified`, `untrusted`) eingeführt und in der Restore-Vorschau sichtbar gemacht.
- [x] Explizite Legacy-Migration ohne stilles Trust-Upgrade umgesetzt.
- [x] Authentifizierten Prune-Anchor ergänzt, damit legitime Retention von unautorisiertem Löschen unterscheidbar bleibt.
- [x] Chaos-Tests gegen Manifest-Replacement, Generation-Deletion/-Insertion, Audit-Tampering und partiell kompromittierte Checkpoint-Verzeichnisse ergänzt.
- [x] 566/566 automatisierte Tests unter Xvfb bestanden; Welle-15-Trusttests 10/10.
- [x] Codequalität, Architektur, Ereignis-, Registry-, Design-, Text-, Versions-, Release-, Dokumentations- und Compile-Verträge bestanden.
- [!] Stable-Gates VIS-001, VIS-002, REL-001 und SCHED-001 bleiben unverändert offen.

## Fortsetzungswelle 16 – 2026-08-07

- [x] Vollanalyse von Recovery-Trust, Restorepfaden, Architektur, Ausführungsrisiken, Toolchain-Verträgen und Stable-Gates durchgeführt.
- [x] Kritische Trust-Lücke geschlossen: automatische Recovery-Auswahl berücksichtigt ausschließlich vollständig `trusted` Generationen.
- [x] Direkter Restore und Safe-Restore erzwingen authentifizierte, vollständig verkettete Generationen; Legacy bleibt bis zur expliziten Migration gesperrt.
- [x] Trust darf nach einer eingeschobenen/untrusted Parent-Generation nicht still wieder zu `trusted` werden; Folgegeneration wird `authenticated-unlinked`.
- [x] Restore-Journal auf Schema 2 gehärtet: HMAC-authentifiziert, an exakten Generation-Fingerprint gebunden und mit `trusted-generation-required` autorisiert.
- [x] Manipulierte Restore-Journale und Auditketten stoppen Recovery vor dem ersten Nutzdatenwrite.
- [x] Legacy-Migration führt vollständigen Preflight durch und darf eine bereits authentifizierte, aber manipulierte Generation nicht neu signieren.
- [x] Toolchain-Pins gegen direkte PyPI-/Upstream-Seiten verifiziert: Ruff `0.16.1` (2026-07-30) und cryptography `50.0.0` (2026-07-31) sind veröffentlicht; die zwischenzeitliche Downgrade-Annahme wurde verworfen und der ursprünglich vorgesehene reproduzierbare Vertrag beibehalten.
- [x] Ruff `0.16.2` ist am 2026-08-07 veröffentlicht, wird im laufenden RC bewusst nicht ungeprüft übernommen; Versionssprünge erfolgen nur als eigener validierter Toolchain-Schritt.
- [x] Linux-Entrypoint-Rechte repariert: alle Shell-Starter sind ausführbar; Desktop-Launcher-Ziel `STARTEN.sh` und `verify_release.sh` funktionieren ohne Permission-Denied durch fehlendes Execute-Bit.
- [x] Neuer Entrypoint-Permissionsvertrag verhindert Regression der ausführbaren Shell-Dateien.
- [x] Coverage-Policy-Drift durch UI-Refactor behoben: reine Canonical-Präsentationsmodule liegen wieder im etablierten UI-Ausschluss, Canonical-Kernlogik bleibt messpflichtig.
- [x] Aktueller Coverage-Vertrag real bestanden: 81,93 % Zeilen / 66,43 % Branches bei Mindestwerten 80/65.
- [x] 578/578 automatisierte Tests in vier vollständigen Xvfb-/pytest-cov-Batches bestanden; neue Welle-16-Trusttests 8/8.
- [x] Codequalität 0 Befunde, max. Komplexität 29; Architektur, Ereignisarchitektur, Ereignisregister, Registry, Text, Version, Release-Literal, Release-Dateistatus, Dokumentation und Compile bestanden.
- [x] Historischen Offline-Qualitätsbericht commitgebunden gekennzeichnet; verhindert, dass ein Lauf für `2e33a2c…` nach späteren Welle-16-Codeänderungen irrtümlich als aktuelle Freigabe gilt.
- [x] Veraltetes `RELEASE_MANIFEST.json` vollständig aus dem aktuellen Stand neu aufgebaut; 566 manifestierte Release-Dateien mit Größe, SHA-256 und Unix-Modus erneut validiert.
- [!] Externe Stable-Gates Ruff/MyPy/Bandit/pip-audit wurden auf diesem Host mangels installierter exakter Toolchain weiterhin nicht als bestanden behauptet.
- [!] Physische KDE-X11-Abnahme und realer Large-Media-Soak bleiben Stable-Pflichtnachweise.

## Fortsetzungswelle 17 – 2026-08-07

- [x] Candidate-Identität aus Kandidat, `RELEASE_MANIFEST.json`-SHA-256 und separatem ausführungsrelevantem Source-Fingerprint eingeführt.
- [x] Externe Qualitätsberichte und physische Stable-Evidence strikt an Manifest- und Source-Digest gebunden; stale Evidence wird fail-closed gesperrt.
- [x] Deterministischen Quality-Evidence-Index und byte-reproduzierbares Evidence-ZIP ergänzt.
- [x] Wheelhouse-Manifest Schema 2 bindet Toolchain-Lock, Toolchain-Vertrag und kanonische gesamte Wheelliste.
- [x] Offline-Installation erzwingt `--no-index`, `--only-binary=:all:` und `--require-hashes`.
- [x] Physischer KDE-X11-Harness mit explizitem Physical-Acceptance-Modus und 9 Größen-/Skalierungsprofilen vorbereitet.
- [x] Large-Media-/Slow-Target-Harness exportiert Stable-Evidence nur nach realem 96-Job-Lauf auf validiertem externem Ziel.
- [x] Importreihenfolge-Abhängigkeit der Evidence-Validatoren beseitigt.
- [x] 588/588 Gesamtregressionstests in acht vollständigen Xvfb-/Coverage-Batches bestanden.
- [x] Frische Welle-17-Coverage: 81,93 % Lines / 66,43 % Branches / 78,78 % kombiniert; Policy 80/65 bestanden.
- [x] Interne Codequalität 0 Befunde, max. Komplexität 29; Architektur-/Ereignisgates ohne Befund.
- [!] Exakte externe Ruff-/MyPy-/Bandit-/pip-audit-Evidence bleibt offen, weil dieser Host PyPI/Files-PyPI aktuell nicht per DNS erreichen kann; kein Erfolg wird simuliert.
- [!] Reale KDE-X11- und Large-Media-/Slow-Target-Abnahmen bleiben Stable-Pflichtnachweise.

## Fortsetzungswelle 18 – 2026-08-07

- [x] Portables Welle-18-Operator-Kit mit fester Stable-Gate-Reihenfolge umgesetzt.
- [x] Freigaberelevanten externen Quality-Runner auf echte Offline-Netzwerksperre korrigiert.
- [x] pip-audit-Advisory-Cache als getrennten online vorbereiteten, gehashten Input für den nachfolgenden Offline-Gate-Lauf eingeführt.
- [x] Persistente Operator-Sitzung strikt an Kandidat, Release-Manifest und Source-Fingerprint gebunden.
- [x] Stale-Session- und Evidence-Tampering-Sperre ergänzt; alle bereits protokollierten Artefakte werden erneut hashverifiziert.
- [x] KDE-X11 als einzige reale Desktop-Abnahmephase erzwungen; Xvfb/CI kann keine physische Stable-Evidence erzeugen.
- [x] Raw-Desktop-Report und Screenshot pro realer Sitzung dauerhaft in der Operator-Evidence konserviert.
- [x] 96-Job-Langzeitrenderphase bindet Stable-Summary, unveränderten Vertrag und vollständigen final-report.json.
- [x] Sourcegebundene Stable-Promotion-Rehearsal mit byteidentischer Doppelpaketierung implementiert; kein Stable-Artefakt wird dabei veröffentlicht.
- [x] Finale Regression auf Welle-18-Code: 600/600 Tests bestanden.
- [x] Coverage 81,93 % Lines / 66,43 % Branches; Policy 80/65 bestanden.
- [x] Interne Codequalität 0 Befunde, max. Komplexität 29; Architektur-/Ereignisgates ohne Befund.
- [!] Die sechs realen Stable-Gates bleiben offen, bis das Operator-Kit auf geeigneter Hardware vollständig ausgeführt wurde.


## Fortsetzungswelle 19 – 2026-08-08

- [x] SCHED-001 nach der vorgesehenen Reifephase als echten persistenten Systemvertrag freigegeben.
- [x] Exakte lokale Startzeit über `systemd --user`-Timer mit `OnCalendar`, `AccuracySec=1s` und `Persistent=true` umgesetzt.
- [x] Headless Scheduler-Worker führt geplante Batches ohne geöffnete GUI aus.
- [x] Semantischer Render-Fingerprint bindet Audio-/Medienreihenfolge, ohne volatile Autosave-/KPI-Metadaten fälschlich als Änderung zu behandeln.
- [x] Quellenzustand wird zusätzlich über Pfad, Dateigröße und `mtime_ns` eingefroren; echte Änderungen blockieren den geplanten Lauf fail-closed.
- [x] Symbolische Links für Projekt, Quellen und Starter werden am Scheduler-Sicherheitsrand abgewiesen; Starter muss ausführbar sein.
- [x] Optionales `systemd-inhibit` blockiert Schlaf/Shutdown während eines laufenden Renderjobs; ausgeschaltete Rechner werden ausdrücklich nicht automatisch aufgeweckt.
- [x] Optionale Abschlussaktion `Energiesparen` wird getrennt vom Rendererfolg protokolliert und kann einen erfolgreichen Batch nicht nachträglich zum Renderfehler machen.
- [x] Verpasste Startzeit besitzt ein begrenztes, konfigurierbares Verspätungsfenster; außerhalb davon wird der Plan als `missed` beendet.
- [x] systemd-User-Manager-Bereitschaft wird 30 Sekunden gecacht, damit der 2-Sekunden-KPI-Refresh keine unnötigen Subprozesse erzeugt.
- [x] 609/609 automatisierte Tests in acht vollständigen Xvfb-Batches bestanden.
- [x] Frische Welle-19-Coverage: 80,96 % Lines / 65,49 % Branches / 77,80 % kombiniert; Policy 80/65 bestanden.
- [x] Interne Codequalität: 313 Python-Dateien / 2.692 Funktionen / maximale Komplexität 29 / 0 Befunde; Architektur- und Ereignisgates ohne Befund.
- [!] Übersprungene externe Stable-Nachweise bleiben bewusst offen: Ruff/MyPy/Bandit/pip-audit, physische KDE-X11-Abnahme und realer 96-Job-Slow-Target-Soak wurden nicht simuliert.

## Fortsetzungswelle 20 – 2026-08-08

- [x] Begrenzte Wiederholungsregeln `once`, `daily` und `weekly` mit Intervall 1–30 und maximal 366 Vorkommen eingeführt.
- [x] Scheduler-Schema 2 mit expliziter Migration bestehender Schema-1-Pläne umgesetzt.
- [x] IANA-Zeitzonenbindung und deterministische DST-Regel eingeführt; Frühlingslücke wird übersprungen, doppelte Herbststunde verwendet den späteren Zeitpunkt.
- [x] systemd-Trigger auf konkrete UTC-Zeitpunkte umgestellt, damit DST-Mehrdeutigkeiten den tatsächlichen Start nicht verändern.
- [x] Catch-up-Policy `skip` / `run_once` mit begrenztem Verspätungsfenster umgesetzt.
- [x] Mehrere Zeitpläne pro Projekt sowie Verwaltungsansicht mit Neu/Bearbeiten/Duplizieren/Löschen und separatem Verlauf eingeführt.
- [x] Scheduler-Historie mit maximal 500 atomar gespeicherten Verlaufseinträgen eingeführt.
- [x] Globale prozessübergreifende Render-Lease schützt GUI und Scheduler vor parallelen Batches.
- [x] Renderkonflikte werden nur innerhalb des Catch-up-Fensters erneut terminiert; keine unbegrenzte Konfliktschleife.
- [x] Reine Scheduler-Tk-Dialogmodule konsistent zum bestehenden UI-Coverage-Scope aus der Business-Coverage ausgeschlossen; Fachlogik bleibt vollständig messpflichtig.
- [x] 624/624 Gesamtregressionstests in acht vollständigen Xvfb-Batches bestanden.
- [x] Frische Welle-20-Coverage: 81,42 % Lines / 65,76 % Branches / 78,21 % kombiniert; Policy 80/65 bestanden.
- [x] Interne Codequalität: 318 Python-Dateien / 2.744 Funktionen / maximale Komplexität 29 / 0 Befunde; Architektur- und Ereignisgates ohne Befund.
- [!] Externe Stable-Nachweise bleiben bewusst offen: Ruff/MyPy/Bandit/pip-audit, physische KDE-X11-Abnahme und realer 96-Job-Slow-Target-Soak wurden nicht simuliert.

## Fortsetzungswelle 21 – 2026-08-08

- [x] Scheduler-Schema 3 mit Governance-Struktur und sicherer Schema-2-Migration eingeführt.
- [x] Pause/Fortsetzen einzelner Serien inklusive `pause_after_current` für laufende Renderjobs umgesetzt.
- [x] Prioritäten 0–100 und persistente, priorisierte Konfliktwarteschlange eingeführt.
- [x] Globale Blackout-/Wartungsfenster mit IANA-Zeitzone und Zeitbereichen über Mitternacht umgesetzt.
- [x] Ressourcen-Preflight mit Mindest-Freispeicher auf dem tatsächlichen Ausgabe-Dateisystem ergänzt.
- [x] Globaler Parallelitätsvertrag weiterhin auf genau einen prozessübergreifend gesicherten Renderbatch begrenzt.
- [x] Reconciliation zwischen VideoBatch-Plänen und systemd-User-Units einschließlich Drift-Reparatur umgesetzt.
- [x] Projektisolation bei Queue/Reconciliation gegen Cross-Project-Löschung und Fehlzählung gehärtet.
- [x] Scheduler-History/Operations-Export mit SHA-256-Manifest und konservatives Cleanup terminaler Serien ergänzt.
- [x] Zentrale Operationsansicht `Was läuft wann und warum?` mit Status, Priorität, Queueposition und Blockiergrund umgesetzt.
- [x] Race-Schutz für Pause/Löschen während aktivem Worker geschlossen.
- [x] 644/644 Gesamtregressionstests in acht vollständigen Xvfb-/Coverage-Batches bestanden.
- [x] Frische Welle-21-Coverage: 81,22 % Lines / 65,07 % Branches / 77,88 % kombiniert; Policy 80/65 bestanden.
- [x] Interne Codequalität: 327 Dateien / 2.831 Funktionen / maximale Komplexität 30 / 0 Befunde; Architektur- und Ereignisgates ohne Befund.
- [!] Externe Stable-Nachweise bleiben bewusst offen: Ruff/MyPy/Bandit/pip-audit, physische KDE-X11-Abnahme und realer 96-Job-Slow-Target-Soak wurden nicht simuliert.


## Fortsetzungswelle 22 – 2026-08-08

- [x] Robuste ETA-/Laufzeitprognose aus realer erfolgreicher BatchJournal-Historie eingeführt.
- [x] Median/P75/P90 und Konfidenzstufen statt ausreißerempfindlicher Scheinpräzision umgesetzt.
- [x] P75-Speicherprognose pro Vorkommen und für die verbleibende Serie ergänzt.
- [x] Dry-Run-Simulation für 24/48/168 Stunden ohne Datei-, Timer-, Queue- oder Renderänderung umgesetzt.
- [x] Prognostizierte Queue-Start-/Endzeiten unter Priorität, Blackout, Catch-up-Deadline und globalem Render-Slot ergänzt.
- [x] `Warum startet dieser Job nicht?`-Diagnose mit Ursache, Schweregrad und konkreter nächster Aktion eingeführt.
- [x] Persistenten Dead-Letter-Zustand für dauerhaft nicht ausführbare eingefrorene Quell-/Projektzustände ergänzt.
- [x] Operations-UI um ETA, nächste Aktion, Dry-Run-Tab, Konfidenz und Speicherprognose erweitert.
- [x] 658/658 Gesamtregressionstests in acht vollständigen Xvfb-Batches bestanden.
- [x] Frische Welle-22-Coverage: 81,29 % Lines / 65,22 % Branches / 77,94 % kombiniert; Policy 80/65 bestanden.
- [x] Interne Codequalität: 332 Dateien / 2.867 Funktionen / maximale Komplexität 30 / 0 Befunde; Architektur- und Ereignisgates ohne Befund.
- [!] Externe Stable-Nachweise bleiben bewusst offen: Ruff/MyPy/Bandit/pip-audit, physische KDE-X11-Abnahme und realer 96-Job-Slow-Target-Soak wurden nicht simuliert.

## Fortsetzungswelle 23 – 2026-08-08

- [x] Persistente Actual-vs-Predicted-Historie für reale Scheduler-Batchabschlüsse eingeführt.
- [x] Rolling-Origin-Backtest ohne Future-Leakage über die letzten 30/90/180 auswertbaren realen Läufe umgesetzt.
- [x] MAE, RMSE, medianen/P90-Prozentfehler, Bias und Outputgrößenfehler als Prognosegüte-Metriken ergänzt.
- [x] Forecast-Fehler getrennt nach Codec, Profil und Auflösung ausgewiesen.
- [x] Confidence automatisch an reale Backtest-Güte und Error-Drift gekoppelt; schlechte Kalibrierung kann `high`/`medium` begrenzen.
- [x] Kontrollierte Altersgewichtung historischer Samples eingeführt: <=30d 1,0; <=90d 0,75; <=180d 0,5; älter 0,25.
- [x] Laufzeit-Level-Drift und Forecast-Error-Drift als getrennte Signale implementiert.
- [x] Operations-UI um `Prognosequalität`, Segmentfehler und echte Actual-vs-Predicted-Vergleiche erweitert.
- [x] Scheduler-Export um Forecast-Qualitätsbericht und Kalibrierungshistorie ergänzt.
- [x] 672/672 Gesamtregressionstests in acht vollständigen Xvfb-/Coverage-Batches bestanden.
- [x] Frische Welle-23-Coverage: 81,40 % Lines / 65,30 % Branches / 78,03 % kombiniert; Policy 80/65 bestanden.
- [x] Interne Codequalität: 334 Dateien / 2.913 Funktionen / maximale Komplexität 30 / 0 Befunde; Architektur- und Ereignisgates ohne Befund.
- [!] Externe Stable-Nachweise bleiben bewusst offen: Ruff/MyPy/Bandit/pip-audit, physische KDE-X11-Abnahme und realer 96-Job-Slow-Target-Soak wurden nicht simuliert.


## Fortsetzungswelle 24 – 2026-08-08

- [x] Datensparsames renderrelevantes Environment-Profil ohne Hostname/Benutzerkennung eingeführt.
- [x] Environment-Fingerprint bindet CPU-/Threadprofil, FFmpeg-Version/Build, Encoderpfad sowie Ziel-Dateisystem-/Mediumklasse.
- [x] Live-Forecasts trennen unterschiedliche Runtime-Environments und aktive Performance-Epochen.
- [x] Frühere Epochen derselben Umgebung nur noch als expliziten Low-Confidence-Fallback zugelassen.
- [x] Fremde Environment-Profile ohne Legacybasis aus der Prognose ausgeschlossen.
- [x] Automatisches Re-Baselining bei anhaltender >=35-%-Medianverschiebung mit mindestens 10 passenden Beobachtungen eingeführt.
- [x] Re-Baselining lernt zentral aus Scheduler- und manuellen erfolgreichen BatchJournals; alte Epochen bleiben auditierbar.
- [x] Driftursachen `environment_change`, `performance_drift_same_environment` und `forecast_model_drift` getrennt.
- [x] Actual-vs-Predicted-Evidence um Environment-/Epoch-ID und Sekunden-pro-Job erweitert.
- [x] Scheduler-Export um `forecast-environment-epochs.json` ergänzt.
- [x] Während der Altregression gefundene Dry-Run-State-Nebenwirkung beseitigt; Forecast/Simulation bleibt strikt read-only.
- [x] 686/686 Gesamtregressionstests in acht vollständigen Xvfb-Batches bestanden.
- [x] Frische Welle-24-Coverage: 81,35 % Lines / 65,33 % Branches / 77,98 % kombiniert; Policy 80/65 bestanden.
- [x] Interne Codequalität: 336 Dateien / 2.960 Funktionen / maximale Komplexität 30 / 0 Befunde; Architektur- und Ereignisgates ohne Befund.
- [!] Externe Stable-Nachweise bleiben bewusst offen: Ruff/MyPy/Bandit/pip-audit, physische KDE-X11-Abnahme und realer 96-Job-Slow-Target-Soak wurden nicht simuliert.
