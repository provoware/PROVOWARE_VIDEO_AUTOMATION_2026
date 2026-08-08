# VideoBatch Fast – Umsetzungs- und Erfolgsprüfplan

**Plan-ID:** `VB-DESIGN-2026-01`
**Ausgangsbasis:** synchronisierter `main`-Stand `049376fc8273a17f97d8b211d550ec8e9b6be4ca`
**Arbeitsbranch:** `agent/canonical-design-manifest-20260806`
**Ziel:** Die kanonische Dashboard-Referenz wird schrittweise, testbar und ohne Funktionsverlust in VideoBatch Fast übernommen.

## 1. Verbindliche Arbeitsregeln

1. Jede Iteration liefert mindestens eine vollständig nutzbare Umsetzung; sichtbare Fragmente sind unzulässig.
2. Jeder Checkpoint endet mit automatischer Prüfung, visueller Gegenprüfung und dokumentiertem Ergebnis.
3. Fehler werden innerhalb desselben Checkpoints korrigiert. Ein roter Checkpoint darf nicht übersprungen werden.
4. Bestehende Render-, Sicherheits-, Offline- und Releaseverträge dürfen nicht abgeschwächt werden.
5. Layoutänderungen müssen bei 1024×680, 1366×768, 1440×900 und 1920×1080 nutzbar bleiben.
6. `VIDEOBATCH_CANONICAL_UI_REFERENCE.svg` ist das primäre Bildmuster; das Textmanifest ist die technisch präzisere Instanz.
7. Noch nicht produktiv implementierte Funktionen werden sichtbar gekennzeichnet und deaktiviert. Attrappen, die einen funktionsfähigen Zustand vortäuschen, sind unzulässig.
8. Jeder Checkpoint muss den unveränderten Zugang zu allen bereits vorhandenen VideoBatch-Funktionen nachweisen.

## 2. Nummerierter Plan mit Checkpoints

### Checkpoint 0 – Ausgangsbasis einfrieren

**Umsetzung:** Main-Commit, Version, offene PR-Abhängigkeiten und Qualitätsverträge erfassen; Designarbeit auf eigenem Branch durchführen.

**Erfolgsprüfung:** Branch basiert auf dem dokumentierten Main-Commit; keine Produktionsdatei wird vor der Bestandsaufnahme verändert.

**Exit-Kriterium:** reproduzierbare Ausgangsbasis dokumentiert.

### Checkpoint 1 – Kanonisches Grafik-Manifest und Designvertrag

**Umsetzung:** Textmanifest, Referenzbild, Poster, Designtokens und Validator integrieren; vier Theme-Namen und drei Schriftprofile verbindlich definieren.

**Erfolgsprüfung:** JSON syntaktisch und semantisch gültig; Referenzdateien hashgesichert und offline; Theme-IDs entsprechen den vorhandenen Ressourcen; Schriftprofile sind 90 %, 105 % und 125 %; Vertragsprüfungen grün.

**Exit-Kriterium:** Designvertrag ist im Projekt verbindlich und automatisiert prüfbar.

### Checkpoint 2 – Modernes Anwendungsskelett

**Umsetzung:** feste linke Navigation, kompakter Top-Header, KPI-Zeile und Aktionsleiste einführen; bestehende Funktionsseiten vollständig erreichbar halten; Shell modularisieren.

**Teilprüfungen:**
- **2.1 Shell-Vertrag:** Navigation, Header, KPI-Zeile und Aktionsleiste sind eigenständige Module.
- **2.2 Funktionserhalt:** Start, Medien, Vorschau, Effekte/Einstellungen, Produktion/Queue und Hilfe bleiben vollständig eingebunden.
- **2.3 Primäraktionen:** Projekt, Audioimport, Medienimport, Effekte/Einstellungen, Queue-Start und Ausgabeordner verwenden unverändert die vorhandenen Funktionen.
- **2.4 Responsive Härtung:** Die Aktionsleiste wechselt bei schmalem Arbeitsbereich kontrolliert in mehrere Zeilen.
- **2.5 Tastaturzugang:** Seitenwechsel fokussiert den Arbeitsbereich; Suche öffnet definierte Funktionsseiten.
- **2.6 Ehrlicher Funktionsstatus:** Die Startzeituhr war bis Checkpoint 5 ausdrücklich deaktiviert; seit Welle 19 ist sie nach abgeschlossenem Systemvertrag produktiv freigegeben.
- **2.7 Pflicht-Gate:** Das Grafik-Manifest und die Anwendungsshell werden bei jedem PR und jedem Push nach `main` fail-closed geprüft.

**Erfolgsprüfung:** Maus- und Tastaturnavigation vollständig; kein bestehender Befehl verloren; Mindestfenster 1024×680 bleibt bedienbar; alle Shell-Module syntaktisch gültig; Manifestvalidator und Shellvertrag grün; CI-Gate bleibt read-only.

**Ergebnis vom 6. August 2026:**
- Branch kontrolliert durch echten Zwei-Eltern-Merge auf `main`-SHA `049376fc…` synchronisiert
- Abstammung danach `ahead`, `behind_by = 0`, Merge-Base entspricht exakt `main`
- Release-Manifest nach dem Merge deterministisch regeneriert und geprüft
- Designvertrag und Release-Manifest auf Prüf-Head `33c07d0d…` bestanden
- Ubuntu 22.04 X11 bestanden
- Ubuntu 22.04 Wayland bestanden
- Ubuntu 24.04 X11 bestanden
- Ubuntu 24.04 Wayland bestanden
- realer Tk-Start bei 1024×680 bestanden
- alle sechs vorhandenen Funktionsseiten, vier Themes und drei Schriftprofile durchgeschaltet

**Exit-Kriterium:** erfüllt. Die neue Shell ist vollständig nutzbar, rückwärtskompatibel und gegen den aktuellen `main`-Stand geprüft.

### Checkpoint 3 – Dashboard und KPI-Karten

**Umsetzung:** Karten `Medien`, `Queue`, `Effekte` und `Startzeituhr` produktiv an reale Zustände anbinden.

**Iteration 3.1 – reale Zustände und Bereichsaktionen:**
- eigenständiger, rein testbarer KPI-Zustandsvertrag
- getrennte Zustände `empty`, `ready`, `loading`, `success`, `warning`, `error` und `disabled`
- Medienkarte berücksichtigt Audio-/Medienzahl, fehlende Gegenstücke, nicht erreichbare Quellen und laufende Medienaufgaben
- Queuekarte berücksichtigt vorbereitete Jobs, laufende Produktion, abgeschlossene und fehlgeschlagene Ergebnisse
- Effektkarte reagiert auf Effekt, Übergang und Schnellmodus
- Medien-, Queue- und Effektkarte öffnen den jeweils korrekten vorhandenen Arbeitsbereich
- Startzeituhr war bis Checkpoint 5 sichtbar und technisch deaktiviert; Welle 19 schaltet sie erst nach Preflight und systemd-User-Readiness frei
- KPI-Werte werden ereignisgesteuert und zusätzlich in einem begrenzten Ein-Sekunden-Takt aktualisiert

**Erfolgsprüfung:** Zahlen aktualisieren sich nach Import, Queue-Änderung und Effektwahl; Kartenaktionen öffnen den korrekten Bereich; Leer-, Lade-, Warn-, Fehler- und Erfolgslagen sind getrennt; Schedulerstatus täuscht keine noch nicht vorhandene Funktion vor.

**Status:** Iteration 3.1 implementiert; Release-Manifest-Synchronisierung und Vierfachmatrix laufen noch.

**Exit-Kriterium:** vier Karten liefern reale Daten und vollständige, dem jeweiligen Implementierungsstand entsprechende Aktionen.

### Checkpoint 4 – Dreispaltiger Hauptarbeitsbereich

**Umsetzung:** links Quellen/Projekt, mittig Render-Queue, rechts Vorschau/Details; persistente Spaltenbreiten; kontrollierter Zwei-/Einspaltenmodus bei wenig Platz.

**Erfolgsprüfung:** Drag-, Fokus-, Auswahl- und Scrollverhalten stabil; 120 schnelle Auswahlwechsel ohne Absturz; Kernaktionen bei jeder Schriftgröße erreichbar.

**Exit-Kriterium:** produktiver Hauptworkflow ohne Inhaltsverlust.

### Checkpoint 5 – Startzeituhr und geplanter Renderstart

**Umsetzung:** Datum/Uhrzeit, Leerlaufoption, Energieprofil, Wachhalteoption, Abschlussaktion und persistente Planung.

**Erfolgsprüfung:** Neustart, Sommerzeit, vergangene Zeitpunkte und Doppelstartschutz getestet; realer verzögerter Testauftrag startet genau einmal und wird protokolliert.

**Exit-Kriterium:** Startzeituhr arbeitet sicher, persistent und nachvollziehbar.

**Ergebnis Welle 19 vom 8. August 2026:** erfüllt. Persistente `systemd --user`-Planung, semantischer Render-Fingerprint, Stale-Schutz, begrenztes Verspätungsfenster, optionales `systemd-inhibit`, headless Worker und getrennte Energieaktionsauswertung sind implementiert; 609/609 Gesamtregressionstests bestanden.

### Checkpoint 6 – RenderProof sichtbar integrieren

**Umsetzung:** gewählter Look, Ersatzmodus und fehlender Nachweis getrennt darstellen; Prüfdatei, MP4-Metadaten und Effektvertrag aus Jobdetails öffnen.

**Erfolgsprüfung:** Erfolg nur bei übereinstimmendem Auftrag, Filtergraph, Ausgabe und Nachweis; manipulierte oder fehlende Nachweise werden fail-closed erkannt.

**Exit-Kriterium:** jeder fertige Job besitzt einen sichtbaren Nachweisstatus.

### Checkpoint 7 – Vier Farbthemes und Schriftgrößen vollständig härten

**Umsetzung:** Midnight Blue, Emerald Tech, Violet Pulse und Amber Graphite tokenbasiert; Kompakt, Standard und Groß wirken auf Typografie, Zeilenhöhen und Abstände; persistent und ohne Neustart.

**Erfolgsprüfung:** Kontrastprüfung; 12 visuelle Kombinationen aus vier Themes × drei Schriftgrößen; keine unlesbaren Feld-/Textkombinationen.

**Exit-Kriterium:** alle 12 Kombinationen technisch und visuell bestanden.

### Checkpoint 8 – Barrierefreiheit und responsive Härtung

**Umsetzung:** Fokusreihenfolge, sichtbarer Fokus, Shortcuts, Tooltips, Statusansagen und zentrale Scroll-/Zoomgrenzen.

**Erfolgsprüfung:** Kernworkflow ohne Maus; Fokus bleibt sichtbar; große Schrift ohne abgeschnittene Primäraktionen.

**Exit-Kriterium:** Tastatur- und Sichtbarkeitsszenarien grün.

### Checkpoint 9 – Visueller Manifest-Abgleich

**Umsetzung:** Screenshots für Referenzauflösungen, Themes und Schriftgrößen; Abweichungsbericht nach Layoutzonen.

**Erfolgsprüfung:** Pflichtzonen vorhanden und überlappungsfrei; Abweichungen begründet oder korrigiert; KDE-X11-Sichtprüfung dokumentiert.

**Exit-Kriterium:** Referenzabgleich und physische Sichtprüfung bestanden.

### Checkpoint 10 – Abschluss- und Releaseprüfung

**Umsetzung:** Unit-, Integrations-, visuelle, Architektur-, Sicherheits- und Offline-Gates; Ubuntu 22.04/24.04 × X11 sowie Langzeitrender.

**Erfolgsprüfung:** keine roten, fehlenden, übersprungenen oder veralteten Nachweise; Manifest, Artefaktinhalt und Release-Dokumente stimmen überein.

**Exit-Kriterium:** freigabefähiger RC-Stand; Stable bleibt bis zu allen physischen Gates gesperrt.

## 3. Checkpoint-Protokoll

| Checkpoint | Status | Ergebnis | Nachweis |
|---:|---|---|---|
| 0 | abgeschlossen | Main-Basis dokumentiert und Branch isoliert | Branch-Basis und Vergleich |
| 1 | abgeschlossen | Manifest, Referenzen, Tokens und fail-closed Validator integriert | Designvertragsprüfung |
| 2 | **PASSED** | Shell auf aktuellen `main` synchronisiert und vollständig erneut geprüft | Design-Run `31112872982`; Matrix-Run `31112872882`; `behind_by = 0` |
| 3 | **IN PROGRESS** | Iteration 3.1: reale KPI-Zustände und Bereichsaktionen implementiert | KPI-Vertrag, Design-Gate und Vierfachmatrix |
| 4–10 | offen | Umsetzung erst nach grünem Vorgänger | jeweiliger Prüfbericht |

## 4. Kanonischer Dateivertrag

| Datei | Aufgabe |
|---|---|
| `src/videobatch_fast/canonical_kpi.py` | reiner Zustandsvertrag für Medien, Queue, Effekte und Scheduler |
| `src/videobatch_fast/canonical_shell_contract.py` | verbindliche Navigation, Theme-Namen und Schriftprofile |
| `src/videobatch_fast/canonical_shell_chrome.py` | Sidebar, Top-Header, KPI-Karten und responsive Aktionsleiste |
| `src/videobatch_fast/canonical_shell_workspace.py` | Einbettung sämtlicher Funktionsseiten, Routing und Livebindung |
| `src/videobatch_fast/canonical_ui.py` | kanonische UI-Klasse und Anwendungseinstieg |
| `src/videobatch_fast/app.py` | Auswahl der kanonischen Shell beim normalen Programmstart |
| `tests/test_canonical_application_shell_contract.py` | Funktionserhalt, Navigation, Aktionen, Themes und Schriftprofile |
| `tests/test_canonical_kpi_contract.py` | getrennte KPI-Zustände und ehrlicher Schedulervertrag |
| `.github/workflows/design-manifest-gate.yml` | verpflichtender read-only Vertragslauf für PR und `main` |
| `.github/workflows/checkpoint2-shell-matrix.yml` | realer Tk-Start und KPI-Bedienung unter Ubuntu 22.04/24.04 × X11 |
| `scripts/validate_design_manifest.py` | fail-closed Prüfung von Manifest, Shell, KPI-Vertrag und CI-Gate |
| `diagnostics/checkpoint2/CHECKPOINT2_RESULT.json` | maschinenlesbarer Abschlussnachweis für Checkpoint 2 |
