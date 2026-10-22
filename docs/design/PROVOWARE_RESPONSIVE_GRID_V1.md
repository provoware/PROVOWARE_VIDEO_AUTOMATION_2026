# PROVOWARE – responsiver Rasterstandard V1

**Entwicklungsstand:** Referenzvertrag, **keine** Stable-Freigabe.  
**Geltungsziel:** wiederverwendbares Gestaltungssystem für PROVOWARE-Anwendungen; erster Pilot: VideoBatch.

## 1. Verbindliche Entscheidung

- **Kleinste Referenz-Arbeitsfläche:** 800 × 600 **CSS-Pixel im nutzbaren Fensterinhalt**, nicht pauschal die physische Monitorauflösung.
- **Feinraster:** 120 Spalten × 80 Zeilen, also 9.600 theoretische Koordinatenzellen.
- Am Referenzformat entspricht eine Zelle rechnerisch 6,667 × 7,5 Pixel. Diese Werte sind **keine Mindest- oder Festgrößen von Bedienelementen**.
- Das Raster ist ein **relatives Koordinaten- und Ausrichtungsmodell**. Keine Funktion erhält eine unveränderliche X-/Y-Position.
- Die verfügbare Fläche, die tatsächliche Mindestbreite des Inhalts und die Schriftgröße entscheiden über die Anordnung.

## 2. Vier Ebenen

1. **Fenster:** misst nur den verfügbaren inneren Inhaltsbereich. Titelleisten, Bildschirm-Skalierung und Dockleisten werden nicht fälschlich als verfügbare Arbeitsfläche behandelt.
2. **Hauptbereiche:** gruppieren Dashboard, Dateilisten, Produktion, Vorschau und Einstellungen. Gleichberechtigte Bereiche erhalten gleich große Anteile, wenn der Inhalt das zulässt.
3. **Feinraster:** ermöglicht detaillierte Abstände, Ausrichtung und relative Größen innerhalb der Bereiche, ohne winzige Bedienelemente zu erzwingen.
4. **Umbruch und Sicherheit:** unterschreitet ein Bereich seine nutzbare Mindestgröße, werden Spalten zu Zeilen. Lange Inhalte scrollen vertikal in der passenden Zone. Wesentliche Aktionen dürfen nicht abgeschnitten oder verdeckt werden.

Ein 800×600-Fenster muss **bedienbar** bleiben; es muss nicht jedes Detail eines maximal vergrößerten Dashboards gleichzeitig zeigen.

## 3. Größen- und Inhaltsregeln

- Zwei Hauptkarten brauchen je nach Schrift und tatsächlichem Inhalt mindestens etwa 320–360 CSS-Pixel. Ein horizontaler Zwischenraum von mindestens 12 Pixeln gehört dazu. Der Grenzwert ergibt sich **aus dem Inhalt**, nicht aus einer starren Bildschirmauflösung.
- Steigt die Schriftgröße, wächst die benötigte Mindestbreite proportional; darunter wird automatisch untereinander angeordnet.
- Verbindliche Schrift-/Ansichtsoptionen: **80 / 100 / 110 / 125 / 150 / 175 / 200 %**, Ausgangspunkt **110 %**.
- Bedienziele sollen für Desktop- und Tastaturnutzung gut erreichbar bleiben; **40 CSS-Pixel** sind eine empfohlene Zielhöhe, keine bereits in sämtlichen Bestandsoberflächen erreichte Abnahme.
- Bei wenig Platz werden Zusatzinformationen einklappbar oder wandern in einen eigenen vertikal scrollbaren Abschnitt; Pflichtaktionen bleiben erreichbar.
- **Kein horizontaler Seitenlauf** für das Hauptlayout. Tabellen oder Medien können gesonderte, eindeutig gekennzeichnete Bedienregeln besitzen.
- Skalierung der Inhalte ist **nicht** bloß proportionale Vergrößerung sämtlicher Schaltflächen: Zusätzliche Fensterfläche kommt in erster Linie Listen, Vorschauen und Arbeitsflächen zugute.

## 4. Mess- und Prüfkette

Die Referenzoberfläche liegt unter `visual_inspection/provoware_grid_reference.html`. Sie ist eine **offline lauffähige HTML-Layoutprobe** mit Rastereinblendung und Schriftverstellung, keine echte Videobearbeitungsoberfläche.

**Pflichtmatrix** (Fenster-Inhaltsbreiten × Schriftstufen):

| Inhaltfläche | Zweck |
|---|---|
| 800×600 | minimale Referenz, sämtliche wesentlichen Aktionen erreichbar |
| 1024×768 | kleine Laptops / nicht maximierte Fenster |
| 1280×720 | geringe Höhe und mittlere Breite |
| 1366×768 | üblicher Laptop |
| 1920×1080 | großer Bildschirm |
| 2560×1440 | große/hochauflösende Ansicht |

Bei jeder dieser Größen die sieben Schriftstufen prüfen. Automatische Kontrollen sollen Textüberläufe, Überdeckungen, horizontales Scrollen, Mindestgrößenverletzungen, nicht erreichbare Schaltflächen und Umbruchlogik melden. **Screenshots und die visuelle menschliche Gegenprüfung ergänzen diese Messwerte**, ersetzen sie nicht.

Ein vollständiger HTML-Browserdurchlauf ist erst dann als bestanden zu kennzeichnen, wenn tatsächlich DOM-Geometrie und Screenshots erhoben wurden; die reine Vertragsprüfung ist ausdrücklich **kein** visueller Nachweis.

## 5. Abgleich mit bestehenden VideoBatch-Verträgen

Die vorhandenen Datei `docs/design/VIDEOBATCH_DESIGN_TOKENS.json` und ältere Tk-Layoutprofile enthalten bewusst noch die vorherigen Mindestgrößen und Schriftprofile. Der hier definierte Standard **überschreibt sie nicht stillschweigend**. Bestehende Renderer, Installations-, Offline- und Releaseverträge bleiben unangetastet.

**Migration in getrennten Schritten:**

1. Referenzvertrag und HTML-Beispiel mit automatischer struktureller Vertragsprüfung einführen.
2. Browsermessung mit reproduzierbaren Bildschirmgrößen und Screenshots ergänzen; visuelle Fehler korrigieren.
3. Qt-Bereiche nach dem nachgewiesenen Raster ausrichten, realen Layout- und Funktionstest ausführen und erst danach den jeweiligen alten Vertrag bewusst ersetzen.

Historische RC24-Nachweise bleiben unverändert; die persönliche Kubuntu-Endabnahme erfolgt separat.

## 6. Implementierung der ersten Qt-Stufe und projektübergreifende Bausteine

**Getrennte Bibliothek:** `src/provoware_grid/` enthält die vollständig Qt- und VideoBatch-unabhängige Berechnung der relativen 120×80-Rasterflächen, Schriftstufen, Mindestbreiten und der 42 Standard-Matrixfälle. Es gibt eine einfache Befehlszeile:

```bash
PYTHONPATH=src python -m provoware_grid
PYTHONPATH=src python -m provoware_grid --width 800 --height 600 --zoom 200
```

Für HTML-Projekte enthält derselbe Ordner die wiederverwendbare Datei `grid-v1.css`, die im Offline-Beispiel eingebunden ist. Die Bibliothek hat **keinen** Import von Qt, VideoBatch, Browsern oder Netzwerkmodulen. Die Anwendung kann dieses Paket als Kopie unter `src/` in andere Projekte übernehmen, ohne deren Produktionslogik mitzubringen.

**VideoBatch-Adapter:** `src/videobatch_fast/qt_source_panel.py` nutzt `choose_columns` für die Dateilisten; `qt_adaptive_settings.py` verwendet die identische Rechenregel für die sechs Grundeinstellungen. Die Einstellungsoberfläche bricht bei großen Schriften in einzelne Gruppen um und bleibt vertikal scrollbar, während alle bisherigen Steuerelemente und ihre Verbindungen bestehen bleiben. `qt_main_layout.py` übergibt denselben Schrift-Zoom an beide Adapter.

**Grenzen des Nachweises:** Die reine Rastermatrix bestätigt mathematische Mindestbreitenregeln, nicht die tatsächlich gemessenen Textbreiten. Die Qt-Prüfkette enthält ergänzende Fenstergeometrietests und den echten Wayland-Start. Bei 800×600 und besonders 200 % darf vertikales Scrollen nötig sein. Die vollständige screenshotgestützte Sichtprüfung auf dem realen Kubuntu-Monitor bleibt eine eigene Abnahme. Bestehende ältere Tk-Layoutverträge sind nicht stillschweigend umgestellt.
