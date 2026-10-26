# VideoBatch – QA- und Refactoring-Umsetzung vom 20.10.2026

**Status:** Entwicklungsstand; keine Stable-Freigabe und keine physische Endabnahme.  
**Basis:** PR #252, Commit `3e5862fadfcbcd50d2370017dd6e0b90f4c570df`.  
**Arbeitszweig:** `work/videobatch-audit-qa-ui-recovery-20261020`.

## Umgesetzt

1. **Kleine Fenster:** Das Qt-Mindestfenstermaß wurde von 980×640 auf 800×600 gesenkt. Kopfbereich und Ressourcen-/Fortschrittsanzeige erhalten eigene volle Rasterreihen; das Einstellungsfeld bleibt vertikal scrollbar.
2. **Schaltflächen:** Die neue `ResponsiveControlRow` ordnet zusammengehörige Aktionen dynamisch horizontal oder vertikal an. Die Dateiauswahl, die Übernahme der Produktionsreihenfolge, die Produktionsaktionen und die Ergebnisaktionen teilen die gleiche Regel. Ein begrenzter vertikaler Scrollbereich hält Produktionsaktionen bei großer Schrift erreichbar.
3. **Prüfcode:** Veraltete Annahmen zur früheren Einstellungs-Zweispaltenansicht werden durch Prüfungen der sechs tatsächlich vorhandenen Qt-Felder ersetzt. Die sieben Schriftstufen werden für den Schaltflächenumbruch parametrisiert. Die bestehende 42-Fälle-Rastermatrix bleibt erhalten.
4. **Update-Sicherheit:** Update-Sicherungen bekommen eindeutige Namen und werden vor dem Umschalten weder gelöscht noch überschrieben. Fehler beim Austausch oder beim anschließenden Synchronisieren führen zum Versuch, die alte Installation zurückzusetzen. Fehler-Einspritztests prüfen diese Pfade.

## Explizite Grenzen

- Eine **statische Quelltextprüfung** oder der **Qt-Offscreen-Test** ersetzt keine Sichtabnahme der vollständig gestarteten Oberfläche.
- Die 42 Fälle (sechs Fensterformate × sieben Schriftstufen) sind derzeit für die **Rasterberechnung** abgebildet; ein vollständiger grafischer 42-Fälle-Screenshotnachweis aller Seiten und Bedienelemente steht aus.
- Die bisherige Qt-/Tk-Parität nutzt an mehreren Stellen nachträglich installierte Methoden. Sie wird absichtlich nicht ohne Funktionsvergleich entfernt. Zu bereinigen sind insbesondere `qt_phase3_components.py`, `qt_legacy_parity.py`, `qt_legacy_parity_completion.py` und alte `ui*_mixin.py`-Bausteine.
- Die Update-Korrektur garantiert keine Wiederherstellung nach einem plötzlichen Stromausfall zwischen zwei Dateisystem-Umbenennungen. Dafür ist ein **separater Transaktions-Wiederanlauf beim nächsten Start** mit persistentem Journal und Fehlereinspritzung erforderlich.
- Jede Änderung an Programm- und Testdateien erfordert die anschließende **Neugenerierung des Release-Manifests und des Git-Dateiindex** auf genau dem letzten Commit; nicht mit historischen RC24-Belegen verwechseln.
- Die automatische Gesamtprüfung muss für **einen einzigen unveränderten Commit** nachgewiesen werden, inklusive Qt6/Wayland, FFmpeg, Installation/Start aus frisch entpacktem ZIP, Update-Rückfall und Sicherheitsverträgen. Es liegt für diesen neuen Arbeitszweig noch kein solcher Abschlussnachweis vor.

## Refactoring-Reihenfolge

**R1 – Erfassen:** Alle aktiven Aufrufketten zu Tk-/Legacy-Adaptern systematisch verfolgen und mit realen Qt-Bedienfunktionen vergleichen. `__main__.py` und der produktive Bootstrap starten Qt Phase 3; das ist kein Beleg, dass Legacy-Adapter entbehrlich sind.

**R2 – Ersetzen:** Ein einzelnes, bereits gleichwertiges Teilmodul nach direkten Funktions- und Wiederherstellungstests ablösen. Methodenersetzung beim Import und mehrere Zustandsquellen vermeiden, ohne vorhandene Projektformate zu verändern.

**R3 – Prüfen:** Nach jeder Entfernung die vollständige Quellcode-, Paket- und Startprüfung erneut ausführen. Kein massenhaftes Löschen von Altmodulen auf Verdacht.

## Freigabevertrag / verbleibende Schritte

- [ ] Design-/Release-Index auf finalem Commit erzeugen und verifizieren.
- [ ] Sämtliche automatisierten Prüfungen einschließlich zuvor nicht ausgeführter älterer Qt-Tests auf einem unveränderten Commit grün.
- [ ] Visuelle Mess- und Screenshotmatrix auf vollständig gestarteter Qt-Oberfläche: 800×600, 1024×768, 1280×720, 1366×768, 1920×1080, 2560×1440; jeweils 80/100/110/125/150/175/200 %.
- [ ] Ungewollte horizontale Überläufe, unlesbare oder verdeckte Schalter, unerreichbaren Tastaturfokus und mögliche Endlosschleifen beim Layoutwechsel reparieren.
- [ ] Absturz- und Stromausfall-Recovery bei Update-Umschaltung vollständig entwickeln und prüfen.
- [ ] Qt-/Tk-Migrationsrest mit messbarer Funktionsparität schrittweise beseitigen.
- [ ] Freeze, einmalige physische Kubuntu-26.04/KDE/Wayland-Abnahme bei 100/125/150/200 %, reale Videos/FFmpeg und Langzeitrender.
- [ ] Erst danach eine Stable-Freigabe erwägen.

**Qualitätsprinzip:** Ein grüner CI-Teiltest ist kein Beleg für den vollständigen Releasevertrag. Fehlende Nachweise bleiben ausdrücklich offen.


## Fortsetzung: Integritäts- und Qualitätsaudit vom 25.10.2026

**Ausgangsstand:** `3424a60676b4768653ef7f8d4cdd45c0c31f78e6`.
**Scope:** die im Audit reproduzierten Integritätsfehler, vorhandene fehlgeschlagene Qualitätsverträge, dazugehörige Regressionstests und Dokumentation. Kein Versionswechsel, keine Stable-Freigabe. Ein Executor; alle Fehlereinspritzungen ausschließlich in temporären Testordnern.

### Befund → Korrektur → Nachweis

1. **F1 / bestätigt: konkurrierende Archivdatei gelöscht.** Die Fehlerbereinigung löscht kein mehrdeutiges Veröffentlichungsziel mehr. Das unveränderte Original und eine gegebenenfalls fremde Zieldatei bleiben erhalten. Negativtest: `ArchiveIntegrityTests.test_competing_archive_target_survives_publish_failure`.
2. **F2 / bestätigt: Journal autorisiert fremde Löschpfade.** `archive_recovery.py` prüft Schema, Transaktionskennung, Größen-/Hashformat und verwaltete Zielbereiche. Symbolische Journalverknüpfungen werden abgewiesen. Recovery klassifiziert und schreibt nur das eigene Journal; Quellen, temporäre Dateien und Reservierungen werden nicht aus Journalangaben gelöscht. Ungültige Journale bleiben bytegleich erhalten. Dies ist eine bewusst konservative Wiederherstellungsgrenze.
3. **F3 / bestätigt: aktive Reservierung nach 24 Stunden verdrängt.** Eine gehaltene `flock`-Sperre und lebende Eigentümer verhindern Übernahme unabhängig vom Alter. Eine eindeutige Eigentümerkennung verhindert, dass ein alter Auftrag den Marker eines Nachfolgers entfernt. Frische, noch unvollständig geschriebene Marker werden nicht übernommen. Ein zusätzlicher Test verwendet einen zweiten Python-Prozess.
4. **F4 / bestätigt: Qualitätsgate nutzt alte Lockpfade.** Die Registry verwendet dieselben `config/requirements/`-Pfade wie der Toolchainvertrag. Das Gate prüft Python-Mindestversion, Ruff-/Mypy-Zielversion, Coverage-Vorgabe und Lockpfade auf Drift. Die fachlichen Grenzwerte wurden nicht abgesenkt; zusätzliche Ruff-Regeln prüfen dynamische Code- und unsichere Prozessaufrufe.
5. **F5 / bestätigt: gewachsene Module und hohe Komplexität.** Bestehende Funktionsgrenzen bleiben erhalten; Layoutaufbau, Produktionsereignisse, Projektpersistenz, Updateinstallation und Storageprüfung liegen in zusammenhängenden Hilfsfunktionen. Keine zusätzliche Mixin-Schicht und keine Änderung der Methodenauflösung. Neue Produktmodule bleiben unter 250 Zeilen. Bestehende Legacy-Limits wurden nur abgesenkt oder nach Unterschreiten der Regelgrenze entfernt.
6. **F6 / bestätigt: schreibender Konfigurationsimport.** `default_project_file()` berechnet nur noch den Pfad. Das Anlegen von Verzeichnissen bleibt eine explizite Lade-/Speicheraktion. Ein frischer Unterprozess prüft, dass ein Konfigurationsimport keinen `mkdir` ausführt.
7. **F7 / bestätigt: ältere Testverträge verfolgen verlegte Dateien nicht.** Testpfade, isolierte Fixture-Verzeichnisse und die gesperrte Pillow-Version sind aktualisiert. Statische Qt-Verträge folgen den tatsächlichen Kompositionsdateien über `tests/qt_source_contracts.py`; dynamische Qt-Tests bleiben unabhängig davon bestehen. Sichtbare Ausgabeoptionen bleiben maßgeblich gegenüber versteckten Legacy-Werten. Fensterspezifische Farbschemata werden am Fenster geprüft.
8. **F8 / bestätigt: Dokumentations- und Berichtspfaddrift.** STATUS wird mit dem vorhandenen Generator synchronisiert; aktuelle Entwicklerbefehle zeigen auf `scripts/`. Der Hygieneprüfer schreibt seinen Standardbericht in den Diagnoseordner statt als neunte Hauptordnerdatei. Der Qt-Workflow liest die Paketversion aus `VERSION.json`.

**Technische Notwendigkeit des größeren Gesamtumfangs:** Das Audit umfasst mehrere unabhängige, vorher fehlgeschlagene Verträge. Die Extraktionen wurden pro Verantwortung vorgenommen; eine einzige kosmetische Aufteilung oder das Erhöhen der Dateilimits hätte die Regressionsursachen nicht behoben. Öffentliche Aufrufgrenzen bleiben als Delegation erhalten, einschließlich der durch vorhandene Tests verwendeten Update-Abhängigkeiten.

### Tatsächlich ausgeführte Entwicklungsnachweise

- Neue Integritäts-, Import- und Policy-Negativtests: 19 bestanden.
- Fokussierte Qt-/Persistenz-/Vertragsintegration: 53 bestanden.
- Echte FFmpeg-Produktion, Effekte und Schnellmodi: 12 bestanden.
- Automatische Qt-Offscreen-Matrix: 42 Größen-/Schriftkombinationen, 126 Screenshots; vorhandene Geometrieprüfungen bestanden.
- Qt-Tastaturmatrix: 54 fokussierte Bedienelemente, keine gemeldeten Probleme.
- Architekturprüfung und internes Qualitätsgate: keine Befunde nach der Korrektur; bestehende erlaubte Legacy-Schulden bleiben sichtbar.
- Laufzeit-Abhängigkeitsaudit: für die acht exakt gesperrten Laufzeitpakete keine bekannten Schwachstellen gemeldet. Dies ist eine zeitpunktbezogene Advisory-Abfrage.
- Frische Laufzeitumgebung aus 51 lokal bereitgestellten, hashgeprüften Wheels offline installiert; Paketindex deaktiviert. Importprüfung bestätigt Qt 6.11.2, cryptography 50.0.0 und Pillow 13.0.0. Geprüft ist die Abhängigkeitsinstallation aus vorhandenem Cache, nicht eine Offline-Erstinstallation des ausgelieferten ZIP auf Kubuntu.

Die abschließende Gesamtregression, Coverage-Messung, Paketextraktion und Manifestprüfung werden am endgültigen Kandidaten separat protokolliert. Frühere fehlgeschlagene Läufe gelten ausdrücklich nicht als PASS. Historische RC24-Nachweise bleiben unverändert.

### Coverage und verbleibende Abnahme

Die Kernmessung umfasst `videobatch_fast` und `provoware_grid`; der Plugin-Host ist nicht mehr pauschal ausgeschlossen. Die Registry bleibt maßgeblich für mindestens 80 % Zeilen- und 65 % Zweigabdeckung; die eigenständige Coverage-Standardprüfung verwendet zusätzlich die synchronisierte kombinierte 80-%-Vorgabe. UI-/Legacy-Ausschlüsse bleiben offengelegt. Qt-Laufzeitmessungen und Größen-/Tastaturmatrizen werden separat ausgewiesen und nicht als vollständige Produktabdeckung bezeichnet.

**Offen:** reale Kubuntu-26.04/KDE/Wayland-Abnahme bei 100/125/150/200 %, grafischer Erststart aus dem frisch entpackten Paket, physische Offline-Erstinstallation und Langzeitrender am eingefrorenen Kandidaten. Die im Container nicht ausführbare echte Plugin-OS-Isolation wird nicht durch übersprungene Tests als bestanden ausgegeben. Die vollständige Entfernung der Legacy-Oberfläche bleibt ein eigener Migrationsschritt mit Funktionsvergleich.

**Rückweg:** der Ausgangscommit bleibt erhalten; Änderungen sind als lokaler Branch und Patch nachvollziehbar. Nach einer fehlgeschlagenen Archivierung bleiben unbestätigte Dateien und Marker zur Diagnose erhalten. Sie sind keine automatische Löschfreigabe; zunächst Quelle, Ziel, Prüfsumme und aktive Prozesse kontrollieren.


### Ergänzende Abschlussvalidierung

Der ZIP-Prüfer wurde beim realen Pakettest mit einem `KeyError` für das kompakte Manifest reproduziert. Er prüft nun Schema 2 und 3 anhand der tatsächlichen ZIP-Dateien einschließlich Hashes, Modi und kanonischer Pfade. Zehn Negativ-/Positivfälle sichern Manipulation, fremde Wurzel und Traversalpfade ab.

Ein separat entpackter virtueller X-Server ermöglicht die bestehenden Tk-Tests im Container, ohne die Produktinstallation zu verändern. Die Auswahltest-Fixture legt ihr ausdrücklich ausgewähltes Projekt an; die Sperre gegen verschwundene Benutzerprojekte bleibt unverändert. Weitere 17 gezielte Tests prüfen Datenträger-, Schreibschutz-, Kapazitäts-, Geschwindigkeits- und Ressourcengrenzen des Langrender-Vertrags. Sie prüfen Richtlinien unter kontrollierter Fehlereinspritzung und bestätigen keine physische Hardware. Zwölf zusätzliche Plugin-Host-Tests prüfen Eingabeprotokoll, eingeschränkte Python-Builtins und die Ausführungssperre bei fehlender Isolation; die OS-Sandbox-Abnahme bleibt davon getrennt.

Die Kernabdeckung wurde durch diese tatsächlichen Prüfungen erhöht. Keine weiteren GUI-Module wurden ausgeschlossen und die aktuelle kombinierte 80-%-Vorgabe bleibt bestehen. Beide bestehenden Testrunner messen auch das unabhängige Rasterpaket und lesen die unveränderten Mindestwerte 80 % Zeilen / 65 % Zweige aus der Registry. Positiv- und Negativtests bestätigen, dass diese Vorgaben mit den früher ausdrücklich übergebenen Mindestwerten übereinstimmen.

Die gesamte Prüfungsumgebung ist Debian 13 mit Python 3.12 und Qt-Offscreen beziehungsweise virtuellem X11. Sie ersetzt ausdrücklich keine Kubuntu-/Wayland-Endabnahme. Die vollständigen Laufprotokolle, Messdateien, ein Prüf-ZIP und der Patch werden außerhalb des produktiven Baums im Audit-Arbeitsbereich geführt; die finale Manifestprüfung bleibt lesend.


### Protokollierter Abschlussstand

**Geprüfte Codequelle:** `d1b4057d17c941e706ed36dd9dc8bbd571c22436`. Der nachfolgende Abschlusseintrag ändert ausschließlich Dokumentation und daraus abgeleitete Manifest-/Indexdaten.

- Der vorhandene lokale Sammelrunner wurde mit exakt installierter Offline-Quality-Umgebung, virtuellem X11 und isolierten Benutzerpfaden ausgeführt. Ruff, Mypy, Bandit, pip-audit, die internen Gates und die gesamte Pytest-Suite bestanden: **843 bestanden, 2 übersprungen, 7 Subtests bestanden**.
- Kernmessung: **83,60 % Zeilen**, **69,27 % Zweige**, **80,58 % kombiniert**. Alle aktuellen Mindestwerte sind erfüllt. Zusätzliche Ausschlüsse oder abgesenkte Grenzwerte wurden dafür nicht eingeführt.
- Getrennte Qt-Messung: **64,46 % Zeilen / 36,48 % Zweige** bei 70 Qt-Tests und der Offscreen-Matrix. Für diese separate Messgröße wird keine erfundene Freigabeschwelle behauptet.
- Release-ZIP: **562 Quelldateien plus Manifest**, Hash-/Modusprüfung bestanden. Frisches Entpacken, anschließende Manifestprüfung und CLI-Hilfe bestanden; **sieben direkte Hauptordnerdateien**.
- **Der vollständige lokale Sammellauf ist trotzdem NICHT bestanden:** Sein abschließender historischer Tk-Layout-Rundlauf überschreitet das Zeitlimit. Ein zusätzlicher Stacktrace zeigt wiederholte Idle-/Geometrieverarbeitung. Derselbe Hänger wurde am unveränderten Ausgangscommit `3424a60676b4768653ef7f8d4cdd45c0c31f78e6` mit identischer Debian-13-/Tk-9-Umgebung reproduziert. Die erprobten Legacy-Layoutänderungen lösten den gesamten Hänger nicht und wurden verworfen. Der vorher belegte Tk-Code bleibt erhalten; es wird kein unbelegter UI-Umbau ausgeliefert.

**Weiterhin offen:** Prüfung des Legacy-Rundlaufs auf seinem passenden Tk-/X11-Zielsystem; reale Qt-/Kubuntu-/Wayland-Endabnahme, grafischer Paket-Erststart und physischer Offline-Erststart; echte OS-Plugin-Isolation in einer unterstützenden Umgebung; Langzeitrender. Ein lokaler Test- oder Paketnachweis ist weder eine Stable-Freigabe noch ein Ersatz dieser Prüfungen.

**Kleinster nächster Schritt:** diesen Entwicklungsstand per Draft-PR überprüfen und dessen unveränderten Commit in der vorhandenen CI prüfen lassen. Danach den noch offenen Legacy-Rundlauf auf dem geeigneten Zielsystem abgleichen. Der Release-Endkandidat bleibt bis zu den tatsächlichen Abnahmen gesperrt.


### Erscheinungsbild, 26.10.2026

**Soll/Ist vor der ersten Änderung**
Referenz: tatsächlicher Qt-Offscreen-Screenshot 1366×768, 110 %, Dateien; keine externe Designvorlage.
- Struktur: vorhandene drei Arbeitsschritte und Hilfe bleiben; aktiver Reiter derzeit kaum unterscheidbar, soll eindeutig markiert sein.
- Maße/Proportionen: vorhandene responsive Geometrie, Mindestgrößen und Zoomstufen bleiben; keine neue feste Fenstergröße.
- Typografie: Titel/Abschnitt/Feld behalten Hierarchie; erklärende Beschriftungen sollen ohne schwarze Hintergrundbalken auf ihrer Karte stehen.
- Farben: dunkle Flächen derzeit mit vielen konkurrierenden hellen Rahmen; ruhigere dünne Trennlinien, dezente Nebenaktionen, gelbe Hauptaktion bleiben.
- Abstände: vorhandene Layoutabstände bleiben; Reiter erhalten gleichmäßige Innenabstände.
- Zustände: Hover, Auswahl, deaktiviert, Status und deutlicher weißer Tastaturfokus müssen unterscheidbar bleiben.
- Clipping/Überlagerung: bei 1366×768 ist der Arbeitsbereich scrollbar; keine Behauptung vollständiger Sichtbarkeit. Alle 42 Größen-/Zoomkombinationen und Tastaturmatrix erneut prüfen.

Befund beim ersten Nachherbild: fensterlokale Legacy-Themeregel `QWidget` übermalt die globale Komponentenformatierung. Auf die benannte zentrale Fläche begrenzen, damit Beschriftungen transparent und semantische Komponentenfarben wirksam werden. Dafür drei Produktdateien nötig (Stil, Themenadapter, Name der zentralen Fläche); keine Layoutgeometrie geändert.

**Umgesetzt:** transparente Beschriftungen, dünnere Karten-/Statusrahmen, zurückhaltende Standardaktionen, sichtbarer aktiver Reiter mit Akzentlinie und eigenem Hover-/Fokuszustand. Die fensterlokalen Themenregeln betreffen jetzt die benannte zentrale Fläche statt sämtliche QWidget-Unterklassen. So übermalen sie keine Eingabefelder, Statusfarben oder Kartenbeschriftungen mehr. Alle vier Themen behalten ihre Fenster-/Kartenfarben. Zusätzlicher Bildvergleich aller vier Themen deckte unzureichenden Kontrast im hellen Thema auf: Titel, Schriftgrößenbeschriftung und direkte Kartenbeschriftungen erhalten dort gezielt dunkle Textfarbe, während Status-/Aktionsfarben erhalten bleiben. Keine neue Abhängigkeit.

**Validiert:** 70 Qt-Tests bestanden; 42 Größen-/Zoomkombinationen mit 126 neuen Offscreen-Bildern bestanden; Tastaturmatrix: sechs Fälle, 54 fokussierte Bedienelemente. Vorher/Nachher bei 1366×768/110 % und Nachher bei 800×600/200 % tatsächlich angesehen. Der kleine Arbeitsbereich bleibt scrollbar; vollständige gleichzeitige Sichtbarkeit wird nicht behauptet. Ruff und Architekturprüfung bestanden. Bildartefakte im externen Audit-Arbeitsbereich `appearance-final/`.

**Offen/Risiko:** keine physische Kubuntu-/Wayland-Abnahme und keine Stable-Freigabe. Die bestehende Legacy-Tk-Prüfgrenze bleibt unverändert. Nächster Schritt: Prüfung des aktualisierten Draft-PR und visueller Abgleich auf dem Zielsystem.
