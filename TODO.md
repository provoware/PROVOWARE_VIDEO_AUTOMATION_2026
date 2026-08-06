# Offene Punkte nach RC24-Finalbereinigung

## Aktueller Schwerpunkt: Musterabgleich und robuste Desktop-Oberfläche

Die kanonische Referenz ist `docs/design/VIDEOBATCH_CANONICAL_UI_REFERENCE.svg`. Die folgenden Punkte stammen aus dem direkten Vergleich zwischen Referenz, Designmanifest und aktueller Tk-Oberfläche sowie aus der gemeldeten realen KDE-Darstellung.

### P0 – sichtbare Layoutfehler und Blocker

- [ ] **UI-P0-001 – Kanonisches Dashboard statt alter Einzelseite:** Das Muster zeigt Quellen, Render-Queue und Jobdetails gleichzeitig im Verhältnis ungefähr `22 % / 48 % / 30 %`. Aktuell öffnet das Dashboard nur die alte Startseite in einem versteckten Notebook. Abnahme: Das Dashboard besitzt einen echten, datenangebundenen Drei-Spalten-Arbeitsbereich; die bisherigen Fachseiten bleiben separat erreichbar.
- [ ] **UI-P0-002 – Kontrolliertes vertikales Scrollen:** Bei geringer Fensterhöhe oder großer Schrift verschwinden untere Bereiche beziehungsweise rutschen unter andere Elemente. Abnahme: Das Dashboard besitzt einen eigenen Scrollbereich; Primäraktionen, Details und Status bleiben ohne Überlagerung erreichbar.
- [ ] **UI-P0-003 – Responsive Spaltenumschaltung:** Die Referenz verlangt drei Spalten ab großer Breite, zwei Spalten im mittleren Bereich und kontrolliertes Stapeln bei kleiner Breite. Aktuell bleibt die alte Seitenstruktur unverändert. Abnahme: Drei definierte Layoutstufen ohne negative Breiten, abgeschnittene Karten oder überlagerte Widgets.
- [ ] **UI-P0-004 – Kopfzeile auf Referenzhöhe verdichten:** Das Muster verwendet eine flache Top-Zeile. Aktuell erzeugen Identität, Designhinweis, Theme-/Schriftwahl, Suche und Suchhinweis mehrere Höhenebenen. Abnahme: kompakte Kopfzeile; Zusatzbedienung bricht kontrolliert um und überdeckt keine Suche oder Titel.
- [ ] **UI-P0-005 – KPI-Karten gegen Schriftüberlauf härten:** Feste `wraplength`-Werte und zusätzliche Aktionsschalter erzeugen bei 125 % oder hoher KDE-Skalierung zu kleine Karten. Abnahme: dynamische Textbreite, definierte Mindesthöhe, gleiche Kartenhöhe und keine abgeschnittenen Statuszeilen.
- [ ] **UI-P0-006 – Aktionsleiste nach realer Wunschbreite umbrechen:** Der bisherige feste Grenzwert berücksichtigt weder DPI noch Schriftprofil. Abnahme: Spaltenzahl wird aus verfügbarer Breite und angeforderter Schalterbreite berechnet; kein Schalter liegt unter einem anderen.
- [ ] **UI-P0-007 – Hilfeeinstiege responsiv anordnen:** Fünf feste Spalten führen auf kleineren Fenstern zu gequetschten oder abgeschnittenen Beschriftungen. Abnahme: automatische Anordnung mit ein, zwei oder drei Spalten und vollständiger Tastaturerreichbarkeit.
- [ ] **UI-P0-008 – Mindestgrößen und gespeicherte Geometrie begrenzen:** Eine alte oder zu kleine gespeicherte Fenstergeometrie kann das Layout außerhalb des nutzbaren Bildschirms öffnen. Abnahme: Geometrie wird auf Bildschirmgrenzen und sinnvolle Mindestmaße normalisiert.
- [ ] **TC-P0-001 – Lokale Prüfung nicht durch fehlendes Wheelhouse blockieren:** `verify_release.sh` scheitert trotz vorhandener Qualitätsumgebung an einem nicht mitgelieferten `TOOLCHAIN_WHEELHOUSE_MANIFEST.json`. Abnahme: lokale Qualitätsprüfung kann eine bereits bestätigte Umgebung verwenden; nur eine ausdrücklich strenge reproduzierbare Releaseprüfung verlangt das komplette Wheelhouse.
- [ ] **TC-P0-002 – Verständliche Wheelhouse-Diagnose:** Ein Quellarchiv enthält bewusst keine Wheels, die Fehlermeldung wirkt jedoch wie eine beschädigte Installation. Abnahme: Ausgabe erklärt den Unterschied zwischen lokaler Prüfung, optionalem Online-Aufbau und reproduzierbarer Stable-Freigabe.

### P1 – erkennbare Unterschiede zum Muster

- [ ] **UI-P1-001 – Quellenkarte an reale Medien- und Projektdaten binden:** Anzahl Audios, Bilder/Videos, fehlende Dateien, Projektname und Ausgabeziel sichtbar machen.
- [ ] **UI-P1-002 – Queue-Tabelle im Dashboard:** Reale Jobs mit Name, Effekt/Modus, Status und Fortschritt anzeigen; keine statischen Musterwerte.
- [ ] **UI-P1-003 – Jobdetail- und Vorschaukarte:** Reale Vorschau-/Metadatenvariablen, Effekt, Auflösung, Codec und Ziel verwenden.
- [ ] **UI-P1-004 – Scheduler sichtbar, aber ehrlich deaktiviert:** Das Muster zeigt die Startzeituhr. Bis Checkpoint 5 bleibt sie sichtbar als deaktiviertes Modul mit verständlicher Begründung; kein Attrappenstart.
- [ ] **UI-P1-005 – Darstellungskarte aus dem Header in den Arbeitsbereich verschieben:** Theme und Schriftprofil sollen wie im Muster in einem eigenen kompakten Bereich verfügbar sein; der Header bleibt dadurch ruhiger.
- [ ] **UI-P1-006 – Footer auf eine kompakte Statuszeile begrenzen:** Führungstext und Systemzustand dürfen nicht mehrzeilig übereinander wachsen. Lange Hinweise werden gekürzt und vollständig per Tooltip beziehungsweise Hilfebereich zugänglich.
- [ ] **UI-P1-007 – Sidebarstatus und Navigation angleichen:** Abstände, aktive Fläche, Textkontrast und Statuskarte an das Muster annähern; Navigation bleibt fest, nur Inhalt scrollt.
- [ ] **UI-P1-008 – Typografie konsistent skalieren:** Titel, Kartenwerte, Hilfetext und Labels erhalten zentrale Größenprofile statt gemischter impliziter ttk-Standardwerte.
- [ ] **UI-P1-009 – Referenz-Hashangaben synchronisieren:** Textmanifest und Designtokens enthalten derzeit unterschiedliche SHA-256-Angaben für dieselben SVG-Referenzen. Abnahme: eine kanonische, reproduzierbar erzeugte Quelle.

### P2 – nachhaltige Absicherung

- [ ] **UI-P2-001 – Layoutvertragstests:** Statische und GUI-nahe Tests für Breakpoints, Scrollbarkeit, Mindestbreiten und vorhandene Pflichtzonen ergänzen.
- [ ] **UI-P2-002 – Reale KDE-Sichtprüfung:** Screenshots bei 1024×768, 1366×768, 1500×920 und 1920×1080 sowie bei 90 %, 105 % und 125 % Schriftprofil dokumentieren.
- [ ] **UI-P2-003 – Überlagerungswächter:** Nach `update_idletasks()` Widget-Rechtecke auf negative Größe, Überschneidung von Geschwistern und außerhalb des sichtbaren Containers liegende Primäraktionen prüfen.
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
