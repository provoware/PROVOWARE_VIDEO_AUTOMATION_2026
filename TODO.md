<!-- 40d-final:start -->
## 40D · finale Freigabepolitik

- [x] Coverage-Vertrag 80/65.
- [x] Interne Qualität und Architektur.
- [x] Wayland: nicht erforderlich.
- [x] Large-Media-/Slow-Target-Soak: bewusst übersprungen (Waiver, kein PASS).
- [ ] Physische KDE-X11-Abnahme auf dem finalen Kandidaten.

**Stable bleibt bis zur realen KDE-X11-Abnahme fail-closed.**
<!-- 40d-final:end -->

# TODO – aktueller Arbeitsplan

## Schwerpunkt

Aktuell haben **Start-/Absturzstabilität** und der reale **Soll/Ist-Bildvergleich** Vorrang vor weiteren Features.

Verbindliche visuelle Arbeitsliste:

`VIDEOBATCH_BILDVERGLEICH_CHECKLISTE_2026-08-07.txt`

Die Checkliste enthält die detaillierten Einzelbefunde `UI-001` bis `UI-081` sowie die reale Endabnahme `A-001` bis `A-022`. Diese Punkte werden hier bewusst **nicht dupliziert**. `TODO.md` steuert nur Reihenfolge, Arbeitsstatus und Abschlussnachweise.

## Statusregel – ab jetzt verbindlich

- `[x]` bedeutet: Implementierung **und** passende reale/automatisierte Abnahme sind nachgewiesen.
- Ein statischer Vertrag allein schließt keinen sichtbaren UI-Punkt mehr ab.
- Ein GitHub-Status `mergeable` ist keine Laufzeit- oder Sichtabnahme.
- Ein realer Screenshot, Crashbericht oder Test, der einen früheren Haken widerlegt, **öffnet den Punkt wieder**.
- Frühere visuelle Häkchen aus der Vorabimplementierung gelten deshalb nicht mehr als Endabnahme; die Bildvergleichscheckliste ist für die aktuelle Oberfläche maßgeblich.

## P0 – zuerst: Startabsturz real reproduzieren

- [ ] **RUN-P0-001 – Aktuellen `main` auf dem Kubuntu-Zielsystem starten:** `./STARTEN.sh` mit aktivem Debugmodus ausführen.
- [ ] **RUN-P0-002 – Absturzbericht sichern:** Bei erneutem Abbruch den automatisch erzeugten TXT-Bericht aus `debugging/` und die relevante Konsolenausgabe als primäre Ursache verwenden.
- [ ] **RUN-P0-003 – Nur den ersten realen Crashbefund korrigieren:** Keine Layout-, Architektur- oder Toolchainumbauten, bevor der konkrete Startfehler eingegrenzt ist.
- [ ] **RUN-P0-004 – Regulären Abschluss gegen Crash unterscheiden:** Nach dem Fix Start, kurze Bedienung und normales Schließen prüfen; der Wächter darf einen normalen Abschluss nicht als Absturz melden.

## P0/P1/P2 – `VIDEOBATCH_BILDVERGLEICH_CHECKLISTE_2026-08-07.txt` abarbeiten

### Vorbedingung

- [ ] **BV-000 – Bildzuordnung final bestätigen:** Die vereinbarte Uploadreihenfolge lautet *Muster zuerst, aktuelle Oberfläche zweitens*. Die vorhandene Checkliste bezeichnet im Kopf aktuell `Bild 1` als IST und `Bild 2` als SOLL. Vor einem Pixelpatch wird die Zuordnung anhand der Originalbilder/Filenames einmal eindeutig bestätigt. Die fachlichen Soll/Ist-Befunde werden nicht aus Vermutung umgedreht.
- [ ] **BV-001 – Ausgangszustand sichern:** Fenstergröße, Screenshotauflösung, KDE-Skalierung, Schriftprofil, Theme und X11/Wayland für den realen IST-Screenshot dokumentieren.

### Empfohlene Reihenfolge aus der Checkliste

- [ ] **BV-010 – UI-003 bis UI-012:** Höhenbudget, Clipping und sichtbaren Hauptarbeitsbereich korrigieren. **P0 zuerst.**
- [ ] **BV-011 – UI-041, UI-045, UI-052, UI-054:** echte Drei-Spalten-Kernoberfläche herstellen und real prüfen.
- [ ] **BV-012 – UI-004, UI-013 bis UI-019:** kompakte Topbar nach Muster herstellen.
- [ ] **BV-013 – UI-028 bis UI-036:** KPI-Karten vollständig verdichten; Diagnoseprosa aus der Primäransicht entfernen.
- [ ] **BV-014 – UI-020 bis UI-027:** Sidebar strukturell und visuell angleichen; nur echte Systemdaten anzeigen.
- [ ] **BV-015 – UI-037 bis UI-040:** Actionbar auf kompakte, vollständig lesbare Bedienung bringen.
- [ ] **BV-016 – UI-042 bis UI-058:** Quellen-, Queue- und Detailfunktionen strukturell und visuell angleichen.
- [ ] **BV-017 – UI-059 bis UI-063:** Schedulerstruktur angleichen; funktional bis Checkpoint 5 weiterhin sichtbar gesperrt lassen.
- [ ] **BV-018 – UI-064 bis UI-071:** Footer und Systemmetriken angleichen; keine erfundenen Werte.
- [ ] **BV-019 – UI-072 bis UI-081:** Pixel-, Farb-, Icon- und Stil-Feinschliff erst nach stabiler Geometrie.
- [ ] **BV-020 – A-001 bis A-022:** vollständige reale visuelle Endabnahme durchführen.
- [ ] **BV-021 – Finale TXT-Auswertung:** vollständige Bildervergleichsauswertung mit erledigten/offenen IDs und realen Prüfwerten ausgeben.

## P0 – Überlagerung und Clipping als eigene Abnahmeklasse

Diese Punkte dürfen nicht durch Scrollen oder kleinere Schrift lediglich verdeckt werden:

- [ ] **LAY-P0-001 – Schrift unter anderem Element:** kein Label/Text darf hinter Button, Entry, Treeview, Canvas oder Nachbarkarte liegen.
- [ ] **LAY-P0-002 – Containergrenzen:** Primäraktionen und Pflichtinformationen bleiben vollständig innerhalb ihres vorgesehenen Containers.
- [ ] **LAY-P0-003 – Text-Clipping:** keine abgeschnittenen letzten Zeilen, Buttontexte oder Tabellenköpfe.
- [ ] **LAY-P0-004 – Vertikales Höhenbudget:** Header + KPI + Actionbar dürfen den Kernarbeitsbereich nicht aus dem normalen Viewport verdrängen.
- [ ] **LAY-P0-005 – Proportionsfehler:** Quellen, Queue und Jobdetails erhalten die aus dem bestätigten Muster abgeleiteten relativen Flächenanteile.
- [ ] **LAY-P0-006 – Resize-/Schriftrobustheit:** 90 %, 105 % und 125 % sowie kleine/mittlere/große Fenster ohne Überlagerung prüfen.

## P2 – geometrischen GUI-Wächter nach der Bildkorrektur erweitern

- [ ] **GUARD-P2-001 – Sollzonen aus echten Messungen ableiten:** Header, KPI, Hauptarbeitsbereich, Sidebar und Footer anhand der bestätigten Referenz messen.
- [ ] **GUARD-P2-002 – Mindestabstände ableiten:** nur tatsächlich gemessene Mindestabstände und sinnvolle Toleranzen festlegen; keine erfundenen Pixelwerte.
- [ ] **GUARD-P2-003 – Bestehenden GUI-Rundtrip erweitern:** Zonen, Mindestabstände, Clipping und Containerüberschreitung in den vorhandenen Test integrieren; **kein neuer GitHub-Workflow**.
- [ ] **GUARD-P2-004 – Menschliche Fehlermeldung:** der Wächter nennt Zone, Istwert, Sollbereich/Toleranz und den nächstmöglichen Reparaturhinweis.
- [ ] **GUARD-P2-005 – Reale KDE-Gegenprobe:** automatisierter Wächter und echter Screenshot müssen übereinstimmen, bevor die Bildkorrektur abgeschlossen wird.

## Entwicklungsweise – Effizienzkorrekturen

- [x] **DEV-001 – `AGENTS.md` auf Minimalpatch-Prinzip umgestellt:** reproduzieren → eingrenzen → minimal korrigieren → gezielt prüfen → real abnehmen.
- [x] **DEV-002 – Scope-Churn entfernt:** keine Pflicht mehr, in jeder Iteration pauschal README, CHANGELOG, Hilfe, Startlogik und Erscheinungsbild gleichzeitig zu ändern.
- [x] **DEV-003 – Workflow-Proliferation untersagt:** lokale Design-/Dokumentations-/Bildprüfungen werden nicht ohne echten Bedarf zu neuen Required-Checks.
- [x] **DEV-004 – Release-Manifest auf einen finalen Lauf begrenzt:** keine Regeneration zwischen Einzelpatches.
- [x] **DEV-005 – Codesparsamkeit priorisiert:** bestehende Module/Tests wiederverwenden; neue Datei/Mixin/Abstraktion nur bei klarer Verantwortungsgrenze.
- [ ] **DEV-006 – Ab nächstem Codepatch Patchbudget anwenden:** bevorzugt höchstens 3 Produktdateien + 1 fokussierte Testdatei pro Einzelbefund.
- [ ] **DEV-007 – Ab nächstem Codepatch reale Ursache zuerst:** kein neuer struktureller Umbau, solange ein aktueller Crashbericht oder Screenshotbefund noch nicht eingegrenzt ist.

## Bereits vorhandene technische Grundlagen

- [x] Typisierter `AppEvent`-Vertrag und Ereignisregister vorhanden.
- [x] BatchRunner und SelectionPreviewController auf typisierte Kernereignisse migriert.
- [x] AST-/Ereignisarchitekturwächter vorhanden.
- [x] Dokumentations-Schnellprüfung über `./test.sh --docs` vorhanden.
- [x] Lokale Qualitätsprüfung und strenger Stable-Pfad getrennt.
- [x] Persistenter menschlicher Debugmodus mit TXT-Absturzberichten vorhanden.
- [x] Bestehender GUI-Rundtrip besitzt eine grundlegende Überlagerungsprüfung; seine Sollwerte werden erst nach der realen Bildkorrektur erweitert.

## Noch offene Stable-Gates

- [x] **Coverage-Vertrag 80/65:** 81,06 % Zeilen / 65,79 % Branch; Schwellen unverändert bestanden · Workflow `33845125393` · Python 3.12.14.
- [ ] **Physische KDE-Abnahme unter X11 und Wayland** für den finalen, korrigierten UI-Stand dokumentieren.
- [ ] **Langzeitrender** mit großer Medienauswahl und langsamem externem Ziel durchführen.
- [x] `RELEASE_MANIFEST.json` nach dem 40D-Status-/Evidence-Sync auf dem workflowfreien Endbaum regenerieren und read-only verifizieren.

Stable bleibt gesperrt, bis diese realen Nachweise auf demselben unveränderten Kandidaten vorliegen.
