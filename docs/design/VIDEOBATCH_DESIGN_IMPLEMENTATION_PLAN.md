# VideoBatch Fast – Umsetzungs- und Erfolgsprüfplan

**Plan-ID:** `VB-DESIGN-2026-01`  
**Ausgangsbasis:** geprüfter `main`-Stand `f03073a1f22357fc87e6e5ee90ef0a995ffdbc77`  
**Ziel:** Die kanonische Dashboard-Referenz wird schrittweise, testbar und ohne Funktionsverlust in VideoBatch Fast übernommen.

## 1. Verbindliche Arbeitsregeln

1. Jede Iteration liefert mindestens eine vollständig nutzbare Umsetzung; sichtbare Fragmente sind unzulässig.
2. Jeder Checkpoint endet mit automatischer Prüfung, visueller Gegenprüfung und dokumentiertem Ergebnis.
3. Fehler werden innerhalb desselben Checkpoints korrigiert. Ein roter Checkpoint darf nicht übersprungen werden.
4. Bestehende Render-, Sicherheits-, Offline- und Releaseverträge dürfen nicht abgeschwächt werden.
5. Layoutänderungen müssen bei 1024×680, 1366×768, 1440×900 und 1920×1080 nutzbar bleiben.
6. `VIDEOBATCH_CANONICAL_UI_REFERENCE.svg` ist das primäre Bildmuster; das Textmanifest ist die technisch präzisere Instanz.

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

**Erfolgsprüfung:** Maus- und Tastaturnavigation vollständig; kein bestehender Befehl verloren; Mindestfenster 1024×680 bleibt bedienbar.

**Exit-Kriterium:** neue Shell vollständig nutzbar und rückwärtskompatibel.

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
| 0 | abgeschlossen | Main-Basis `f03073a…` und offener Abstammungswächter PR #61 dokumentiert | Branch-Basis und Plan |
| 1 | gestartet | Manifest, Referenzen, Tokens und Validator werden integriert | fokussierte Vertragsprüfung |
| 2–10 | offen | Umsetzung erst nach grünem Vorgänger | jeweiliger Prüfbericht |
