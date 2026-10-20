# TODO – Stable-Finalisierung 2.8.3-rc24

## Verbindlicher Entwicklungsplan ab 20.10.2026 – nach dem QA-Audit

**Arbeitsstand:** PR [#253](https://github.com/provoware/PROVOWARE_VIDEO_AUTOMATION_2026/pull/253), aufbauend auf Raster-PR [#252](https://github.com/provoware/PROVOWARE_VIDEO_AUTOMATION_2026/pull/252). Historische RC24- und PR-#240/#246-Nachweise sind keine neue Freigabe. #246 und #251 sind inzwischen in `main` übernommen; die früheren Hinweise „#246 offen“ in der nachfolgenden historischen Arbeitsliste sind überholt.

**Arbeitsweise:** Entwicklung und Prüfungen auf getrennten Zweigen, kein direktes Stable-Merge. Zuerst echte Funktion und Sicherheit, danach optische Verfeinerung. Kein Punkt erhält ein Häkchen, bevor ein aktueller Commit und reproduzierbare Belege vorliegen.

### Neue Umsetzung: kleine Ansichten, Qt-Direktmethoden und externer Update-Starter (20.10.2026)

- [x] Bei 800×600 / 175–200 % den **dekorativen Kopf** verkleinert, ohne die Arbeits-Schriftstufe global zu ändern; Datei-Auswahltasten und Auftrags-Spalten erhalten kurze sichtbare Texte sowie vollständige Tooltips. `tests/qt_phase3_42_matrix.py` prüft die kompakte Darstellung.
- [x] Diashow-Reihenfolge sowie vier Qt-Phase-3-Abläufe (**Optionen, Aktualisieren, Laufzeitstatus, Start**) aus der dynamischen Klassenersetzung in ausdrücklich definierte Methoden überführt; die vier Importdialog-Einstiege ebenfalls direkt an Qt Phase 3 gebunden. Die bestehenden Qt-Roundtrip-/Smoke-Verträge bleiben Teil der CI.
- [x] Vor dem lokalen Aktivieren eines Updates wird `<Installationsordner>-SICHER-STARTEN.sh` **außerhalb** des austauschbaren Ordners angelegt, zusammen mit dem eigenständigen Standardbibliothek-Python-Starter. Er prüft die persistierte Transaktion und kann einen kaputten neuen `STARTEN.sh` **und** `debug_launcher.py` unabhängig von neuen Programmimporten zurückrollen. Ein neuer echter Unterprozesstest zerstört beide neuen Startdateien und verlangt einen erfolgreichen Start der Vorversion.
- [ ] Alle neuen technischen UI-/Sicherheitsprüfungen, Release-Manifest und Dateiindex **auf genau einem finalen Commit** erfolgreich auswerten; bei Fehlern zuerst den Quellcode reparieren.
- [ ] Die verbleibenden echten Qt-Kompatibilitätsadapter für **DropList-Ansicht/Produktionsreihenfolge und PreviewPanel** mit unabhängigen Verhaltenstests in die jeweiligen Klassen übertragen. Keine pauschale Altcode-Löschung.
- [ ] Die neu erzeugten **126 echten Screenshots** vollständig begutachten, insbesondere 800×600 mit 175/200 %, und mögliche Restüberläufe beheben. Automatischer Geometrie- und Fokusnachweis sind keine physische Barrierefreiheitsfreigabe.
- [ ] Den sichtbaren Bedienweg zur externen Sicherungs-Startdatei und bestehende Startverknüpfungen auf einem echten Kubuntu-System kontrollieren. Ein völlig zerstörtes **ursprüngliches** STARTEN.sh muss über die externe Sicherungsdatei gestartet werden; der alternative Pfad darf nicht verschwiegen werden.

### P0 – grafische Vollprüfung (Issue [#254](https://github.com/provoware/PROVOWARE_VIDEO_AUTOMATION_2026/issues/254))

- [x] Echtes Qt-Phase-3-Fenster in einer automatisierten **42-Fälle-Schleife** erfassen: sechs Größen (800×600, 1024×768, 1280×720, 1366×768, 1920×1080, 2560×1440) × sieben Schriftstufen (80/100/110/125/150/175/200 %).
- [x] **Drei Arbeitsseiten pro Fall** (Dateien, Ausgabe, Produktion) fotografieren; erwartete Gesamtzahl: **126 Bilder**. `tests/qt_phase3_42_matrix.py` und `.github/workflows/qt6-phase3-smoke.yml` sind als neue Entwicklungsprüfungen eingebunden.
- [ ] Tatsächlichen Prüflauf am finalen unveränderten Commit vollständig grün nachweisen, Bericht und Bilder als CI-Artefakt archivieren; fehlgeschlagene Fälle mit Bildname und Ursache dokumentieren.
- [ ] Alle Hauptregister, Texte, Schaltflächen, Überläufe, Scrollbereiche, Fokusringe und Tastaturwege bei 800×600 und 200 % **sichtbar** prüfen und gefundene Fehler korrigieren. Die erste automatisierte Geometrieprüfung ersetzt keine qualifizierte Sichtauswertung.
- [ ] Farbkontrast und Barrierefreiheit inklusive Touch-/Maus-Zielgrößen ergänzen; mindestens drei Schritte immer verständlich beschriften.
- [ ] Physische Kubuntu-26.04-/KDE-Plasma-/Wayland-Abnahme bei 100/125/150/200 % **erst nach Kandidaten-Freeze** ausführen; kein CI-Offscreen-Ergebnis als physische Freigabe ausgeben.

### P0 – stromausfallfeste Aktualisierung (Issue [#255](https://github.com/provoware/PROVOWARE_VIDEO_AUTOMATION_2026/issues/255))

- [x] Update-Sicherungen gegen versehentliches Überschreiben geschützt, abgefangene Aktivierungsfehler mit Rollback-Tests geprüft (PR #253).
- [x] Bereits vorhandenen A/B-Slotstarter als geeigneten Referenzweg identifiziert: `scripts/ab_launcher.py` mit persistiertem `pending_transaction.json` und atomarer `current`-Umschaltung.
- [ ] **Zweiten lokalen Updateweg** in `src/videobatch_fast/updates.py` auf A/B umstellen oder mit gleichwertiger außerhalb des austauschbaren Installationsordners erreichbarer Transaktionssteuerung absichern. Zwischen zwei Ordnerumbenennungen darf die Anwendung nicht dauerhaft unstartbar bleiben.
- [ ] Prozessabbruch/KILL vor und nach jeder kritischen Schreiboperation; beschädigte Startverweise, gesperrte/volle Platte, verlorene Bestätigung und unerwarteten Neustart mit Unterprozessprüfungen reproduzieren.
- [ ] Immer letzte bestätigte Installation und alle Benutzerprojekte erhalten; Diagnosebericht und sicheren Rückfall automatisch nachweisen.

### P1 – funktionstreues Qt-/Tk-Refactoring (Issue [#256](https://github.com/provoware/PROVOWARE_VIDEO_AUTOMATION_2026/issues/256))

- [ ] Produktiv verwendete Tk-/Legacy-Aufrufketten und alle Speicher-/Menü-/Dialogverträge maschinenprüfbar inventarisieren.
- [ ] Nachträgliche Klassen-Methodenersetzung in `qt_phase3_components.py` und `qt_legacy_parity_completion.py` schrittweise durch direkte Qt-Methoden und testbare Dienste ersetzen.
- [ ] Zwei oder mehr Zustandsquellen für Sortierung/Ansicht, globale und bereichsspezifische Schriftgröße, Projekteinstellungen und Dialoge prüfen; nur fachlich identische Pfade zusammenführen.
- [ ] Paritätstests vor **jeder** Entfernung; danach reale Qt-GUI, Projekt-Roundtrip, FFmpeg-Erstellung, Plugin-Schutz, Update und Benutzerpaket prüfen.

### P1 – Freigabebelege und Dokumentation (Issue [#257](https://github.com/provoware/PROVOWARE_VIDEO_AUTOMATION_2026/issues/257))

- [ ] Alle relevanten **auch früheren** Tests auf einem einzigen unveränderten Commit ausführen, veraltete Annahmen reparieren und Resultate eindeutig speichern.
- [ ] `RELEASE_MANIFEST.json` und `registries/PROJECT_FILE_INDEX.json` nach der **letzten** Änderung erzeugen, Driftprüfungen erfolgreich durchführen. Nachträgliche Schreibänderungen verlangen einen neuen Nachweis.
- [ ] Frisch entpacktes Benutzerpaket mit höchstens acht Hauptordnerdateien, echte Qt-Bereitschaft, Offline-Start, reale FFmpeg-Ausgabe und Unterbrechungs-Rückfall miteinander prüfen.
- [ ] `docs/STATUS.md`, Dokumentationswegweiser, Bedienungsanleitung, Update-Anleitung und Entwicklungsbericht am geprüften Stand synchronisieren, historische RC24-Werte unverändert lassen.
- [ ] Stable nur nach explizitem Freeze, sauberer automatisierter Gesamtabnahme und danach gebündelter persönlicher Kubuntu-Endprüfung.

### P2 – Einsteigerführung und Barrierefreiheit (Issue [#258](https://github.com/provoware/PROVOWARE_VIDEO_AUTOMATION_2026/issues/258))

- [ ] Hauptnavigation, Schritt-Hinweise und Hilfe einheitlich **1 Dateien → 2 Ausgabe/Einstellungen → 3 Produktion** benennen.
- [ ] Kurze, gut lesbare Bedienelemente; flexible Umbrüche und bedarfsweise vertikales Scrollen ohne versteckte horizontale Inhalte; vollständige Tastaturbedienung.
- [ ] Nicht benötigte erweiterte Werkzeuge standardmäßig ausblenden, doppelte Schaltflächen/Sortierwege vermeiden.
- [ ] Drei geeignete Erscheinungsbilder (dunkel, hell, hoher Kontrast) mit tatsächlichem Kontrast-, Schrift- und Fokusnachweis prüfen; optische Kosmetik bleibt bis zum Abschluss von P0 nachrangig.

### Ergänzung 20.10.2026 – tatsächliche Implementierung auf PR #253

- [x] Qt-Phase-3-Lebenszyklus von den beiden importseitig ersetzten `__init__`-Methoden getrennt: ausdrückliche, in Reihenfolge gestartete Qt-Paritätsdienste in `qt_phase3.py`.
- [x] Importseitig ersetztes `closeEvent` entfernt: Sicht- und Sortiereinstellungen werden über `persist_parity_on_close` direkt beim Schließen der Qt-Phase-3-Oberfläche gesichert. Weiter bestehende Medienlisten-, Vorschau- und Optionenadapter bleiben bis zu gleichwertigen Einzeltests aktiv.
- [x] Tastaturtest für 800×600 bei 175/200 % auf Eingabefelder, Auswahlfelder, Schalter und Einstellregler erweitert; die automatisierte Prüfung ersetzt keine vollständige Sichtabnahme auf einem physischen Monitor.
- [x] Echter Unterprozess-Negativtest ergänzt: geprüftes Update mit absichtlich defektem `scripts/bootstrap.py` installieren, wirklichen `debug_launcher.py` ausführen und alte Version automatisch erneut starten. Nicht abgedeckt: defekter Debug-Starter selbst vor Ausführung des Wiederanlaufcodes; dafür ist ein unabhängiger, außerhalb des Programmordners gelegener Starter nötig.
- [ ] Alle Tests, einschließlich der erweiterten Qt-Tastaturprüfung, am letzten unveränderten Commit abschließend grün nachweisen; `RELEASE_MANIFEST.json` und Git-Dateiindex nach der letzten Quellcodeänderung synchronisieren.
- [ ] Restliche dynamische Methodenadapter in `_patch_phase2_class`, `_patch_drop_list`, `_patch_preview_panel` und `_patch_media_browsers` funktionsgleich in definierte Klassen/Dienste überführen.
- [ ] Vollständige Sichtkontrolle aller 126 Bilder, tatsächliche Register-/Tastatur-Reihenfolge, Bildschirmlesbarkeit bei 800×600/175–200 % und physische Kubuntu-Endabnahme nach Freeze.

### Freigabegrenze

- [ ] PR #253 und der darauf folgende Entwicklungsstand sind nur **Entwürfe**; bestandene Teilprüfungen sind nicht gleichbedeutend mit bestandenem Gesamtrelease.
- [ ] Die einmalige **physische** Kubuntu-Endabnahme bleibt ausdrücklich bis zum Abschluss aller Entwicklungsarbeiten aufgeschoben.

---

### Folgeschritt – 20.10.2026, verifizierbar erst auf neuem Commit

- [x] Sechs Dialogaufrufe (Plugins, Update, Wiederherstellung, Archiv, visuelle Freigabe) sind explizit in `qt_phase2.py` gebunden; Importzeit-Klassenüberschreibungen und die früheren Dialog-Instanzpatches wurden entfernt. Der Qt-Phase-3-Smoke prüft, dass keine dynamischen Instanzmethoden zurückbleiben.
- [x] `tests/qt_phase3_keyboard_matrix.py` prüft auf der echten Qt-Phase-3-Oberfläche **800×600 bei 175/200 %**, jeweils auf den drei Hauptseiten, den Tastaturfokus und die tatsächliche Sichtbarkeit beim Scrollen; in `.github/workflows/qt6-phase3-smoke.yml` eingebunden.
- [x] Der lokale Paket-Updateweg behält sein Journal nach erfolgreicher Dateiumschaltung **bis zur normalen UI_READY-Erststartbestätigung**. `scripts/debug_launcher.py` führt bei Startfehler oder erforderlichem Safe-Mode den Rückfall auf die bestätigte Vorversion mit **einem** neuen Startversuch aus.
- [x] Vier neue Update-Sicherheitsfälle testen die Erststartbestätigung, den Rückfall, einen harten Abbruch nach dem dauerhaften Journal und das Verbot einer Bestätigung bei fehlender Alt-Sicherung.
- [ ] **Neue Tests und alle acht Gesamtprüfläufe auf einem eingefrorenen Commit erfolgreich belegen.** Bei Änderungen Manifeste und Dateiindex erneut synchronisieren.
- [ ] **Restliches Refactoring:** `install_legacy_parity()`, `install_parity_completion()` und Legacy-Sortier-/Skalierungsbrücken nur nach separaten Gleichwertigkeitsprüfungen ablösen.
- [ ] **Restliches Update-Gate:** Sicherung auch dann von einem unabhängig installierten Starter erreichen, wenn die neue Python-Laufzeit oder `debug_launcher.py` vor dem ersten Import kaputt ist. Dafür produktiven A/B-Controller als primären Aufrufpfad nutzen oder gleichwertigen externen Starter schaffen.
- [ ] **Visuelle Endbewertung:** vollständige Einzelbildsichtung aller 126 Aufnahmen, echte KDE-/Kubuntu-Sichtabnahme wie vereinbart erst am fertigen Kandidaten. Ein grüner Tastaturtest ersetzt dies nicht.

### Aktuelle Zwischenbilanz der drei Arbeitsschritte

- [x] Visueller 200-%-Befund: Historische Expertenleiste überdeckte den Ausgabebereich. Automatische Öffnung abgestellt, manuelle Menüfunktion erhalten. Produktionsseite scrollbar; neue vollständige Screenshot-Abnahme offen.

- [x] 42 technische Fälle mit 126 Aufnahmen auf Commit `3144447` grün. **Visuell nicht bestanden:** bei 800×600 und 200 % überlappen und verschwinden Titel, Ressourcenfelder und Arbeitsinhalte.
- [x] Ausgabe-Einstellungen in die zweite Arbeitsseite verschoben; kompakte Menütaste und geringere Kopflast bei >=150 % eingebaut. Der verschärfte Qt-Test sucht jetzt auch abgeschnittene Titel und zu flache Arbeitsseiten. **Neue Sichtprüfung erforderlich.**
- [x] Zwei Plugin-Dialogroutinen aus Import-Zeit-Methodenersetzung in direkte Qt-Klassenbindungen überführt. **Weitere Legacy-Doppelstrukturen offen.**
- [x] Lokalen Linux-Update-Ordnerwechsel atomar gemacht; drei Testfälle beenden echte Unterprozesse vor/nach dem Wechsel und nach der Sicherung. **Persistenter Wiederanlauf vor dem GUI-Start umgesetzt; Erststart-Rückfall nach einem späteren Programmfehler noch offen. CI-Nachweis für den neuen Stand ausstehend.**
- [x] Nach 42/42 erfolgreicher Geometrieprüfung neue Bilder gesehen: In Schritt 2 sprang die Anzeige wegen Tastaturfokus zur Expertenkontrolle statt zu den Ausgabe-Grundeinstellungen. Fokus und Anfangsposition korrigiert, zusätzliche 42-Fälle-Prüfregel hinzugefügt. **Erneuten Bildsatz prüfen.**
- [ ] Nach jedem Quellcode-Update 42er-Sichtprüfung, Gesamtregression, Release-Manifest und Git-Dateiindex auf exakt einem Commit wiederholen.

## Fokus (ältere Arbeitsnotizen – zeitlich einordnen)

**Zielplattform:** Kubuntu 26.04 LTS · KDE Plasma · natives Wayland · PySide6/Qt 6.

Der Langzeitrender und die frühere Kubuntu-Basisabnahme sind dokumentiert. **Die reale Prüfung bei 125 % am 06.10.2026 hat jedoch einen echten Layoutfehler sichtbar gemacht: zu viele Hauptbereiche waren gleichzeitig eingeblendet. Dieser Befund wird mit getrennten Arbeitsseiten behoben und muss danach neu abgenommen werden.**

## P0 – jetzt

### Konsolidierung und Benutzerpaket

- [x] PR-Bestand bereinigt: #247, #248 und #250 geschlossen; nur #246 bleibt offen.
- [x] CI auf `2ae2ae5`: 8/8 GitHub-Prüfläufe erfolgreich.
- [x] Frisch gebautes ZIP entpackt und kontrolliert: **7 Hauptordnerdateien**, Kommando-Hilfe funktioniert.
- [ ] Offline-Erstinstallation und tatsächlichen grafischen Qt-Start **aus demselben entpackten Paket** automatisiert nachweisen.
- [ ] Geänderte Dokumentation und Manifest/Index auf einem neuen unveränderten Commit erneut vollständig prüfen.
- [ ] Danach separate Entscheidung über die Integration von #246 nach `main`. Keine vorzeitige Stable-Freigabe.



### 1. Kubuntu-/Wayland-Sichtabnahme — OFFEN

- [x] Basisabnahme vom 29.09.2026 unter `diagnostics/release_readiness/KUBUNTU_OPERATOR_ACCEPTANCE_2026-09-29.json` erhalten.
- [x] Realen 125-%-Befund vom 06.10.2026 dokumentiert: abgeschnittene Texte, zu flache Listen und unnötiges Hauptbereich-Scrollen.
- [x] Hauptablauf in eigene Seiten für Dateien, Ausgabe und Produktion getrennt; Projekt/Hilfe/Diagnose verdrängen den Arbeitsbereich nicht mehr.
- [x] PR #230 ist historisch in `main` übernommen; alte Prüfungen sind keine neue Freigabe für PR #240.
- [x] Strukturmigration #246: CI-Prüfungen auf Commit `2ae2ae5` vollständig grün, inklusive entpacktem ZIP mit 7 Hauptordnerdateien.
- [ ] Korrigierten Stand real bei 100 %, 125 %, 150 % und 200 % prüfen: kein Clipping, keine Überlagerung, alle Hauptschalter sichtbar, Fokus sichtbar, Listen ausreichend hoch, keine Hauptseiten-Scrollleiste.
- [ ] Sortierung prüfen: reine Ansichtssortierung darf die Produktionspaarung nicht ändern; Übernahme nur nach ausdrücklichem Klick.
- [ ] Erst nach dieser Sichtabnahme `physical_kubuntu_26_04_wayland` wieder auf `passed` setzen.

### 2. Realer Langzeitrender — GRÜN

- [x] Ausgeführten Langzeitrender durch den Projektverantwortlichen als in Ordnung bestätigt.
- [x] Kanonisches Gate `large_media_soak` auf `passed` gesetzt.
- [x] Manuelle Provenienz unter `diagnostics/release_readiness/LONG_RENDER_OPERATOR_ACCEPTANCE_2026-09-29.json` dokumentiert.
- [x] Keine nicht vorliegenden Einzelmesswerte, Hashwerte oder Prüfschritte werden nachträglich erfunden.

## Stable-Finalisierung – ein reales UI-Gate offen

- [x] Expliziten Operator-Freigabevertrag als fail-closed Alternative zum klassischen Nachweispfad implementieren; keine Messwerte werden rekonstruiert.
- [ ] PR #246 erst nach aktuellem Commit-Gate und gesonderter Integrationsentscheidung nach `main` übernehmen; physische Kubuntu-Abnahme erst am finalen Releasekandidaten.
- [ ] Reale 100/125/150/200-%-Sichtabnahme dokumentieren und Release-Evidence erneut ableiten.
- [ ] Danach Stable 2.8.3 in getrennter Arbeitskopie erzeugen, deterministisch doppelt paketieren, Stable-Branch/Tag und GitHub-Release veröffentlichen.

## Repository-Schutz und Ordnung

- [x] `main` ist durch das aktive Ruleset **„Design manifest contract“** geschützt.
- [x] **Design manifest contract** und **Release contract sync** sind verpflichtende GitHub-Actions-Prüfungen.
- [x] Externe GitHub Actions sind durch einen SHA-Pinning-Vertrag gegen bewegliche Tags/Branches geschützt.
- [x] Reine technische Referenzdokumente sind unter `docs/reference/` gebündelt; Start-, Release- und Vertragsdateien bleiben im Hauptverzeichnis.
- [ ] Weitere schwere CI-Gates nur separat und risikobasiert als Pflichtchecks bewerten; Qt6-/Wayland- und Langzeitrender-Gates nicht beiläufig hochstufen.

## Danach – Qt-Migration abschließen

Diese Arbeiten bleiben bis zur realen Zielsystemabnahme zurückgestellt:

- [ ] Entscheiden, ob der kanonische Startpfad vollständig auf Qt Phase 3 umgeschaltet werden kann.
- [ ] Verbleibende Tk-/Legacy-UI-Pfade auf tatsächliche Restverwendung prüfen.
- [ ] Nicht mehr benötigte Legacy-Teile separat und mit Regressionstest entfernen.
- [ ] Projekt-, Diagnose-, Vorschau- und Diashow-Funktionen auf dem realen Zielsystem vollständig durchlaufen.

## Wartbarkeit

- [ ] Neue rein interne historische Nachweise unter `docs/archive/` ablegen; freigegebene Release-Unterlagen im Hauptverzeichnis nicht nachträglich verschieben.
- [ ] Keine parallele CI-Matrix einführen, solange der Einzielvertrag Kubuntu 26.04 / Wayland gilt.
- [ ] Nach Plattformänderungen `config/contracts/PLATFORM_SUPPORT.json`, Stable-Abnahmevertrag, Nutzeranleitungen und CI gemeinsam gegen Drift prüfen.
- [ ] Pro Entwicklungsiteration höchstens **zwei Umsetzungsschritte**, danach Kurzabnahme und vollständiges Gate.

## Abschlussregel

**Der Langzeitrender bleibt fachlich grün; die physische UI-Sichtabnahme ist nach dem realen 125-%-Befund und der daraus folgenden Layoutkorrektur offen.** Stable darf erst nach der neuen 100/125/150/200-%-Abnahme promotet werden. Vorhandene Evidenz wird nicht rückwirkend umgedeutet oder künstlich aktualisiert.
