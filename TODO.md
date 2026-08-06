# Offene Punkte nach RC24-Finalbereinigung

## Aktueller Schwerpunkt: Musterabgleich und robuste Desktop-Oberfläche

Die kanonische Referenz ist `docs/design/VIDEOBATCH_CANONICAL_UI_REFERENCE.svg`. Die folgenden Punkte stammen aus dem direkten Vergleich zwischen Referenz, Designmanifest, aktuellem Tk-Aufbau und der gemeldeten realen KDE-Darstellung.

**Statusregel:** Ein abgehakter Punkt bedeutet, dass die Codeänderung und ein statischer Vertrag vorliegen. Die reale Sichtabnahme unter KDE bleibt gesammelt unter `UI-P2-002` offen.

### P0 – sichtbare Layoutfehler und Blocker

- [x] **UI-P0-001 – Kanonisches Dashboard statt alter Einzelseite:** Quellen, Render-Queue und Jobdetails liegen gleichzeitig in einem echten, datenangebundenen Arbeitsbereich; der bisherige geführte Startassistent bleibt separat erreichbar.
- [x] **UI-P0-002 – Kontrolliertes vertikales Scrollen:** Das Dashboard besitzt einen eigenen Canvas-Scrollbereich; der Footer und die Navigation bleiben fest.
- [x] **UI-P0-003 – Responsive Spaltenumschaltung:** Reine, getestete Breakpoints steuern drei Spalten, zwei Spalten und kontrolliertes Stapeln.
- [x] **UI-P0-004 – Kopfzeile verdichten:** Theme- und Schriftwahl wurden aus dem Header entfernt; Suche und Bedienung brechen nur bei tatsächlich fehlender Breite kontrolliert um.
- [x] **UI-P0-005 – KPI-Karten gegen Schriftüberlauf härten:** Detailtexte verwenden reale Kartenbreiten, KPI-Karten wechseln zwischen vier, zwei und einer Spalte, Wiederherstellungsaktionen bleiben kompakt.
- [x] **UI-P0-006 – Aktionsleiste nach Wunschbreite umbrechen:** Die Spaltenzahl wird aus verfügbarer Breite und `winfo_reqwidth()` berechnet.
- [x] **UI-P0-007 – Hilfeeinstiege responsiv anordnen:** Die fünf „Ich möchte …“-Aktionen verwenden einen zentral getesteten Spaltenrechner.
- [x] **UI-P0-008 – Mindestgrößen und gespeicherte Geometrie begrenzen:** Gespeicherte Größe und Position werden auf sichtbare Bildschirmgrenzen normalisiert.
- [x] **TC-P0-001 – Lokale Prüfung nicht durch fehlendes Wheelhouse blockieren:** `verify_release.sh` verwendet standardmäßig die vorhandene bestätigte Qualitätsumgebung; `--strict` bleibt der reproduzierbare Stable-Pfad.
- [x] **TC-P0-002 – Verständliche Wheelhouse-Diagnose:** Lokale Qualitätsprüfung, Kernprüfung und strenge Wheelhouse-/Signaturprüfung sind in Hilfe und Ausgabe eindeutig getrennt.

### P1 – funktionale Unterschiede zum Muster

- [x] **UI-P1-001 – Quellenkarte an reale Medien- und Projektdaten binden:** Anzahl, fehlende Pfade, Projektname, Ausgabeziel und bis zu einhundert reale Quelldateien werden angezeigt.
- [x] **UI-P1-002 – Queue-Tabelle im Dashboard:** Reale Jobs mit Name, Effekt, Status und Fortschritt sowie eine lokale Suche werden angezeigt.
- [x] **UI-P1-003 – Jobdetail- und Vorschaukarte:** Reale Vorschauvariablen, ausgewählter Auftrag, Effekt, Modus, Auflösung, Codec und Ziel werden verwendet.
- [x] **UI-P1-004 – Scheduler sichtbar, aber ehrlich deaktiviert:** Die Startzeituhr bleibt bis Checkpoint 5 sichtbar deaktiviert; kein Attrappenstart wurde ergänzt.
- [x] **UI-P1-005 – Darstellungskarte aus dem Header verschieben:** Theme und Schriftprofil befinden sich in einem eigenen Dashboardbereich.
- [x] **UI-P1-006 – Footer auf eine kompakte Statuszeile begrenzen:** Führungstext wird einzeilig begrenzt; der Systemzustand bleibt separat sichtbar.
- [ ] **UI-P1-007 – Sidebar-Systemwerte vervollständigen:** Das Muster zeigt CPU, RAM, GPU und Cache. Nur tatsächlich messbare Werte dürfen ergänzt werden; unbekannte GPU-Beschleunigung darf nicht erfunden werden.
- [x] **UI-P1-008 – Typografie konsistent skalieren:** Shelltitel, KPI-Werte, Hinweise, Navigation und kompakte Aktionen verwenden zentrale Profile für 90 %, 105 % und 125 %.
- [ ] **UI-P1-009 – Referenz-Hashangaben synchronisieren:** Textmanifest und Designtokens enthalten unterschiedliche SHA-256-Angaben für dieselben SVG-Referenzen. Die tatsächlichen Dateihashes müssen lokal ermittelt und genau einmal übernommen werden.
- [ ] **UI-P1-010 – Reale Laufzeitbadges im Header:** FFmpeg-Version, Cachezustand und verfügbare Beschleunigung wie im Muster anzeigen; nur aus echten Diagnosedaten.
- [ ] **UI-P1-011 – Livefortschritt in der Dashboard-Queue:** Laufender Einzel- und Gesamtfortschritt soll aus den bestehenden Progressvariablen in die passende Tabellenzeile gespiegelt werden.
- [ ] **UI-P1-012 – Jobdetailregister:** Vorschau, Effekte und Ausgabe als klar getrennte, tastaturerreichbare Detailbereiche abbilden, ohne die bestehende Vorschauseite zu duplizieren.
- [ ] **UI-P1-013 – Backupstatus und sichere Aktion:** Das Muster besitzt Backupstatus und Schalter. Nur vorhandene, bestätigte Backupfunktionen dürfen angebunden werden.
- [ ] **UI-P1-014 – Reichere Footerkennzahlen:** CPU, RAM, FFmpeg, Cache, Projektordner und Backup wie im Muster nur dann anzeigen, wenn die Werte ohne Pollinglast und ohne Attrappen verfügbar sind.
- [ ] **UI-P1-015 – Icon- und Akzentkonsistenz:** Kartenicons, farbige Akzentlinien und Zustands-Pills an die Referenz annähern; keine externen Bildabhängigkeiten.
- [ ] **UI-P1-016 – Pixelabstände nach realen Screenshots feinjustieren:** Karteninnenabstände, Tabellenzeilen, Sidebarhöhe und Vorschauanteil erst nach der KDE-Matrix endgültig festlegen.

### P2 – nachhaltige Absicherung

- [x] **UI-P2-001 – Layoutvertragstests:** Breakpoints, Spaltenrechner, Bildschirmgeometrie, Pflichtzonen, Scrollbereich, MRO und lokale Prüfmodi besitzen statische Tests.
- [ ] **UI-P2-002 – Reale KDE-Sichtprüfung:** Screenshots bei 1024×768, 1366×768, 1500×920 und 1920×1080 sowie bei 90 %, 105 % und 125 % Schriftprofil dokumentieren.
- [x] **UI-P2-003 – Überlagerungswächter:** Der vorhandene GUI-Rundtrip instanziiert die kanonische Anwendung und prüft Kopfzeile, KPI-Karten, Aktionsleiste, Dashboardkarten und Hilfeeinstiege auf Überschneidung sowie Verlassen ihrer Container.
- [ ] **UI-P2-004 – Mustervergleich ohne Merge-Gate:** Lokales Prüfwerkzeug erzeugt einen Bericht über Zonen, Maße und Abweichungen; es blockiert keinen Merge automatisch.
- [ ] **UI-P2-005 – Historische und aktuelle Referenzen trennen:** Alte Screenshots bleiben Nachweise; nur eine ausdrücklich gekennzeichnete kanonische Referenz steuert neue Untermodule.

## Erledigt

- [x] Projektstamm von historischen RC-Berichten bereinigt; Nachweise verlustfrei archiviert.
- [x] Doppelte veraltete visuelle Baselines entfernt.
- [x] Releasefertige eigenständige Unterlagen mit `_save_` gekennzeichnet.
- [x] Fertig/unfertig maschinenlesbar in `RELEASE_FILE_STATUS.json` und zweispaltig in README dokumentiert.
- [x] Vorschauerzeugung für FFmpeg 7+ und beschädigte Cacheziele gehärtet.
- [x] Hilfe-, Cache- und Auswahltexte zentralisiert und Tooltips verbessert.
- [x] Ubuntu 22.04/24.04 × X11/Wayland als verpflichtende PR-Matrix etabliert.
- [x] Typisierten und versionierten `AppEvent`-Vertrag als zentrale UI-Ereignisgrenze eingeführt.
- [x] `BatchRunner` vollständig auf direkte `AppEvent`-Ausgabe mit typisierten Kern-Payloads migriert.
- [x] AST-Wächter blockiert neue freie `(name, payload)`-Ereignistupel außerhalb der Legacy-Grenze.
- [x] `SelectionPreviewController` auf direkte `AppEvent`-Ausgabe mit zwei Pflicht-Payloads migriert.
- [x] Zentrales Ereignisregister und Vollständigkeitsgate für Producer, Handler, Payloadtypen, Terminalstatus und Vertragstests ergänzt.
- [x] Ruff 0.16.1, MyPy 2.3.0, Bandit 1.9.4 und pip-audit 2.10.1 gebunden ausgeführt.

## Noch offene Stable-Gates

- [ ] Physische KDE-Abnahme unter X11 und Wayland dokumentieren.
- [ ] Langzeitrender mit großer Medienauswahl und langsamem externem Ziel durchführen.

Stable bleibt bis zum vollständigen Nachweis der beiden bewusst geparkten Realabnahmen gesperrt.
