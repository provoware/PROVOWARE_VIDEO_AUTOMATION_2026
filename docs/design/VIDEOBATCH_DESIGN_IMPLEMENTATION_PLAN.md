# VideoBatch Fast – Umsetzungs- und Erfolgsprüfplan

**Plan-ID:** `VB-DESIGN-2026-01`  
**Ausgangsbasis:** geprüfter `main`-Stand `0e0214404886457d3b073565c3157e5458c6b8bb`  
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
- **2.6 Ehrlicher Funktionsstatus:** Die Startzeituhr ist sichtbar, aber bis Checkpoint 5 ausdrücklich deaktiviert.  
- **2.7 Pflicht-Gate:** Das Grafik-Manifest und die Anwendungsshell werden bei jedem PR und jedem Push nach `main` fail-closed geprüft.

**Erfolgsprüfung:** Maus- und Tastaturnavigation vollständig; kein bestehender Befehl verloren; Mindestfenster 1024×680 bleibt bedienbar; alle Shell-Module syntaktisch gültig; Manifestvalidator und Shellvertrag grün; CI-Gate bleibt read-only.

**Exit-Kriterium:** neue Shell vollständig nutzbar und rückwärtskompatibel; Repository-Prüfungen sind grün.

### Checkpoint 3 – Dashboard und KPI-Karten

**Umsetzung:** Karten `Medien`, `Queue`, `Effekte` und `Startzeituhr` produktiv an reale Zustände anbinden.

**Erfolgsprüfung:** Zahlen aktualisieren sich nach Import, Queue-Änderung und Effektwahl; Kartenaktionen öffnen den korrekten Bereich; Leer-, Lade-, Fehler- und Erfolgslagen sind getrennt.

**Exit-Kriterium:** vier Karten liefern reale Daten und vollständige Aktionen.

### Checkpoint 4 – Dreispaltiger Hauptarbeitsbereich

**Umsetzung:** links Quellen/Projekt, mittig Render-Queue, rechts Vorschau/Details; persistente Spaltenbreiten; kontrollierter Zwei-/Einspaltenmodus bei wenig Platz.

**Erfolgsprüfung:** Drag-, Fokus-, Auswahl- und Scrollverhalten stabil; 120 schnelle Auswahlwechsel ohne Absturz; Kernaktionen bei jeder Schriftgröße erreichbar.

**Exit-Kriterium:** produktiver Hauptworkflow ohne Inhaltsverlust.

### Checkpoint 5 – Startzeituhr und geplanter Renderstart

**Umsetzung:** Datum/Uhrzeit, Leerlaufoption, Energieprofil, Wachhalteoption, Abschlussaktion und persistente Planung.

**Erfolgsprüfung:** Neustart, Sommerzeit, vergangene Zeitpunkte und Doppelstartschutz getestet; realer verzögerter Testauftrag startet genau einmal und wird protokolliert.

**Exit-Kriterium:** Startzeituhr arbeitet sicher, persistent und nachvollziehbar.

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

**Erfolgsprüfung:** Pflichtzonen vorhanden und überlappungsfrei; Abweichungen begründet oder korrigiert; KDE-X11-/Wayland-Sichtprüfung dokumentiert.

**Exit-Kriterium:** Referenzabgleich und physische Sichtprüfung bestanden.

### Checkpoint 10 – Abschluss- und Releaseprüfung

**Umsetzung:** Unit-, Integrations-, visuelle, Architektur-, Sicherheits- und Offline-Gates; Ubuntu 22.04/24.04 × X11/Wayland sowie Langzeitrender.

**Erfolgsprüfung:** keine roten, fehlenden, übersprungenen oder veralteten Nachweise; Manifest, Artefaktinhalt und Release-Dokumente stimmen überein.

**Exit-Kriterium:** freigabefähiger RC-Stand; Stable bleibt bis zu allen physischen Gates gesperrt.

## 3. Checkpoint-Protokoll

| Checkpoint | Status | Ergebnis | Nachweis |
|---:|---|---|---|
| 0 | abgeschlossen | Main-Basis `0e021440…` und isolierter Arbeitsbranch dokumentiert | Branch-Basis und Vergleich |
| 1 | abgeschlossen | Manifest, Referenzen, Tokens und fail-closed Validator integriert | Designvertragsprüfung |
| 2 | Prüfung läuft | Modulare Shell, vollständiger Seitenzugang, reale Primäraktionen, responsive Aktionsleiste und permanentes CI-Gate implementiert | Shellvertrag, Compileall, GitHub Actions |
| 3–10 | offen | Umsetzung erst nach grünem Vorgänger | jeweiliger Prüfbericht |

## 4. Checkpoint-2-Dateivertrag

| Datei | Aufgabe |
|---|---|
| `src/videobatch_fast/canonical_shell_contract.py` | verbindliche Navigation, Theme-Namen und Schriftprofile |
| `src/videobatch_fast/canonical_shell_chrome.py` | Sidebar, Top-Header, KPI-Zeile und responsive Aktionsleiste |
| `src/videobatch_fast/canonical_shell_workspace.py` | Einbettung sämtlicher bestehender Funktionsseiten und Seitenrouting |
| `src/videobatch_fast/canonical_ui.py` | kanonische UI-Klasse und Anwendungseinstieg |
| `src/videobatch_fast/app.py` | Auswahl der kanonischen Shell beim normalen Programmstart |
| `tests/test_canonical_application_shell_contract.py` | Funktionserhalt, Navigation, Primäraktionen, Themes und Schriftprofile |
| `.github/workflows/design-manifest-gate.yml` | verpflichtender read-only Vertragslauf für PR und `main` |
| `scripts/validate_design_manifest.py` | fail-closed Prüfung von Manifest, Shell und CI-Gate |
