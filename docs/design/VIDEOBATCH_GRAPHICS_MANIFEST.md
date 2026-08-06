# VideoBatch Fast – verbindliches Grafik-Manifest

**Manifest-ID:** `VB-GFX-1.0`  
**Gültig ab:** 06.08.2026  
**Status:** verbindlich und dauerhaft  
**Kanonisches Bildmuster:** [`VIDEOBATCH_CANONICAL_UI_REFERENCE.svg`](./VIDEOBATCH_CANONICAL_UI_REFERENCE.svg)  
**Visuelle Übersicht:** [`VIDEOBATCH_GRAPHICS_MANIFEST_POSTER.svg`](./VIDEOBATCH_GRAPHICS_MANIFEST_POSTER.svg)  
**Maschinenvertrag:** [`VIDEOBATCH_DESIGN_TOKENS.json`](./VIDEOBATCH_DESIGN_TOKENS.json)

## 1. Zweck und Rangfolge

Dieses Manifest definiert das absolute Layout, Design und Erscheinungsbild von VideoBatch Fast. Jede sichtbare Weiterentwicklung muss sich daran ausrichten. Bei Widersprüchen gilt:

1. funktionale Sicherheit und Datenintegrität,
2. dieses Textmanifest,
3. maschinenlesbare Designtokens,
4. kanonisches UI-Bildmuster,
5. Poster und ältere Screenshots.

Das Bildmuster ist kein pixelgenauer Zwang für dynamische Inhalte. Verbindlich sind Zonierung, Informationshierarchie, Komponentenfamilien, Dichte, Kontrast, Statuslogik und visuelles Gewicht.

## 2. Leitprinzipien

- **Modern und professionell:** dunkle, ruhige Grundflächen; präzise Akzente; keine dekorative Überladung.
- **Projektbezogen:** Anordnung folgt `Medien → Auftrag → Queue → Vorschau → Ausgabe → Nachweis`.
- **Luftig statt gequetscht:** klare Abstände, maximal eine Hauptaussage je Karte, kontrollierte Scrollbereiche.
- **Hoher Kontrast:** normale Texte mindestens 4,5:1; große Texte mindestens 3:1.
- **Konsistente Formen:** wiederkehrende Radien, Rahmenstärken und Höhen.
- **Klare Zustände:** wartend, aktiv, erfolgreich, Warnung, Fehler und inaktiv werden nie nur durch Farbe codiert.
- **Keine Attrappen:** Kennzahlen und Statuswerte stammen aus realem Zustand.

## 3. Pflicht-Layoutstruktur

### 3.1 Desktop-Zonen

1. **Linke Sidebar:** 220–248 px; Marke, Navigation, Systemstatus.
2. **Top-Header:** 56–68 px; Suche, Laufzeitstatus, Hilfe, Einstellungen.
3. **KPI-Zeile:** vier Karten `Medien`, `Queue`, `Effekte`, `Startzeituhr`.
4. **Aktionsleiste:** 48–56 px; eine Primäraktion, danach Sekundäraktionen.
5. **Hauptarbeitsbereich:** drei Spalten mit ungefähr `22 % / 48 % / 30 %`.
6. **Scheduler-Bereich:** unter Queue und Details; bei Platzmangel als eigener Bereich erreichbar.
7. **Footer-Statusleiste:** 36–44 px; CPU, RAM, FFmpeg, GPU, Cache, Projektordner, Backup, Gesamtstatus.

### 3.2 Responsive Regeln

- Ab 1440 px: vollständige Dreispaltenansicht.
- 1180–1439 px: linke Projektspalte einklappbar; Details mindestens 320 px.
- 1024–1179 px: Queue und Details zweispaltig; Quellen als Schublade.
- Unter 1024 px: kontrolliertes Scrollen zwingend.
- Kein Primärschalter darf unter einem Fensterrand verschwinden.

## 4. Raster, Dichte und Abstände

- Grundraster: 8 px; Zwischenschritte 4 px.
- Außenrand Hauptfläche: 16–24 px.
- Kartenabstand: 12–16 px.
- Karteninnenabstand: 16 / 20 / 24 px.
- Tabellenzeile: kompakt 40 px, Standard 48 px, groß 56 px.
- Mindestbedienhöhe: 40 px; Primärbedienung Standard 44 px.
- Gruppen werden bevorzugt durch Abstand statt zusätzliche Rahmen getrennt.

## 5. Formensystem

- Eingaben und Standardschalter: Radius 10 px.
- Karten und größere Gruppen: Radius 16 px.
- große Dialoge/Drawer: Radius 20–24 px.
- Chips und Statuspillen: Radius 999 px.
- Standardrahmen: 1 px; Fokusrahmen: 2 px.
- Schatten nur zur Hierarchie; maximal drei Elevationsebenen.

## 6. Komponentenregeln

### Sidebar

Aktiver Eintrag besitzt Akzentfläche, Icon und Text. Hover ist deutlich schwächer. Navigation bleibt fest; nur der Inhaltsbereich scrollt.

### Karten

Karten enthalten Titel, Kernwert/Status, kurze Erläuterung und höchstens eine Hauptaktion. KPI-Karten teilen Maße, Radien und Typografie.

### Schalter

- Primär: gefüllter Akzent, maximal einmal je Aktionsgruppe.
- Sekundär: dunkle Fläche mit Rahmen.
- Tertiär: textnah und zurückhaltend.
- Destruktiv: Rot plus eindeutiger Text.
- Deaktiviert: sichtbar inaktiv und mit erklärbarem Grund.

### Eingaben

Beschriftung steht oberhalb oder eindeutig links. Fokus, Fehler und deaktiviert sind getrennte Zustände. Helle Felder erzwingen dunkle Schrift; dunkle Felder helle Schrift.

### Tabellen und Queue

Thumbnail, Name und Kerndaten bilden eine Einheit. Status und Fortschritt sind getrennt. Ausgabeziele werden verkürzt angezeigt, bleiben per Tooltip vollständig zugänglich.

### Vorschau und Details

Vorschau standardmäßig 16:9. Darunter Tabs `Vorschau`, `Effekte`, `Ausgabe`, `Zeitplan`. Änderungen erfolgen im Detailbereich; die Queue bleibt sichtbar.

### RenderProof

- **Bestanden:** gewählter Look, Filtergraph, MP4-Kennung und Prüfdatei stimmen überein.
- **Ersatzmodus:** Ausgabe gültig, ursprünglicher Look ersetzt.
- **Nicht bestätigt:** Nachweis fehlt, ist widersprüchlich oder manipuliert.

## 7. Startzeituhr

Die Startzeituhr ist Pflichtmodul. Sie enthält Datum, Uhrzeit, Aktivschalter, Leerlaufoption, Wachhalteoption, Energieprofil, Abschlussaktion, geschätzte Dauer und Auftragszahl.

Sicherheitsregeln:

1. Kein Start ohne gültige Queue und beschreibbares Ziel.
2. Vergangene Zeitpunkte erfordern neue Bestätigung.
3. Pro Planung genau ein Start; Sperre gegen Doppelstart.
4. Planung wird persistent gespeichert und nach Neustart verständlich angezeigt.
5. Fehler erhalten einen sichtbaren Lösungsweg; Eingaben bleiben erhalten.

## 8. Vier integrierte Farbthemes

Interne IDs bleiben kompatibel:

| Interne ID | Anzeigename | Charakter |
|---|---|---|
| `neon_gravity` | Midnight Blue | Standard, ruhig, blau/cyan |
| `acid_paper` | Emerald Tech | technisch, grün/türkis |
| `toxic_candy` | Violet Pulse | kreativ, violett/magenta |
| `ultraviolet` | Amber Graphite | warm, graphit/amber |

Jedes Theme liefert Primär-, Sekundär-, Akzent-, Erfolgs-, Warn-, Fehler-, Auswahl-, Hover- und Inaktivfarben. Statusbedeutungen bleiben konsistent.

## 9. Schriftgrößenprofile

| Profil | Skalierung | Zweck |
|---|---:|---|
| Kompakt | 90 % | mehr Inhalt bei voller Bedienbarkeit |
| Standard | 105 % | verbindlicher Standard |
| Groß | 125 % | maximale Lesbarkeit |

Die Profile müssen direkt erreichbar, ohne Neustart wirksam und persistent sein.

## 10. Typografie

Primärfamilie ist eine lokal verfügbare Sans-Serif-Schrift; unter Linux bevorzugt `DejaVu Sans`.

- Display: 32/40, semibold.
- H1: 24/32, semibold.
- H2: 20/28, semibold.
- H3/Kartentitel: 16/24, semibold.
- Fließtext: 14/20, regular.
- Zusatztext: 12/16, regular.
- Labels/Chips: 10–12/14–16, medium.

## 11. Statussystem

- Erfolg: Grün plus Haken/Text.
- Information: Blau/Cyan plus Infoicon.
- Warnung: Amber plus Warnsymbol.
- In Bearbeitung: Blau/Violett plus Fortschritt.
- Fehler: Rot plus Fehlertext und Lösung.
- Inaktiv: Grau plus deaktivierter Zustand.

## 12. Pflichtmodule

Dashboard, Medienverwaltung, Render-Queue, Vorschau, Effekte, Startzeituhr, RenderProof, Diagnose, Backup, Projektordner und Einstellungen sind vollständig erreichbar.

## 13. Iterationsvertrag

Jede zukünftige Iteration muss:

1. mindestens eine vollständige, funktionsfähige Umsetzung liefern,
2. vor Abschluss gegen dieses Manifest geprüft werden,
3. Abweichungen innerhalb der Iteration korrigieren,
4. automatisierte Tests und einen visuellen Checkpoint enthalten,
5. Fortschritt, erledigte und offene Punkte ausweisen.

Ein bloßes Mockup oder eine nicht angebundene Oberfläche zählt nicht als Umsetzung.

## 14. Referenzintegrität

- Kanonisches UI-SVG SHA-256: `7e610f9c0e97205dbddd5eea0e8f87ba6547adbc8dae126a1095779ea13500d2`
- Manifest-Poster-SVG SHA-256: `f4a4b10eb8df9eca7bbfa1ea7500f5ee494a5b408fb50810ba087e06a0cf0684`
- Beide SVG-Dateien sind vollständig lokal, vektorbasiert und enthalten keine externen Ressourcen oder Netzverweise.
- Änderungen an Referenzen erfordern neue Manifestversion, Prüfsummen und dokumentierte Freigabe.
