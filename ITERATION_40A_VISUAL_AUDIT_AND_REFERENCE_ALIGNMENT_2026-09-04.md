# Iteration 40A · Gesamtprojekt-Audit und Reference-Aligned Visual Polish

Datum: 2026-09-04  
Produkt: PROVOWARE VideoBatch Fast  
Ausgangsbasis: Iteration 39B, `ffe050744128963942db2f413a7b18c6a344063c`  
Arbeitsbranch: `iteration/40a-reference-aligned-visual-polish-20260904`

## Ziel

Das aktuelle Projekt wird nicht nach persönlichem Geschmack umgestaltet, sondern gegen die im Repository bereits versionierten Orientierungsvorlagen geprüft. Sichtbare Änderungen bleiben auf die aktuelle Tk-Produktoberfläche begrenzt und dürfen weder Video-/Batchlogik noch die geplante PySide6/QML-Architektur vorwegnehmen.

## Verbindliche Referenzreihenfolge

1. `docs/design/VIDEOBATCH_CANONICAL_UI_REFERENCE.svg` – primäre kanonische Bildreferenz laut Umsetzungsplan.
2. `docs/design/VIDEOBATCH_DESIGN_TOKENS.json` – technische Maße, Breakpoints, Theme- und Schriftverträge.
3. `registries/UI_BLUEPRINT.json` – laienoptimierte Hierarchie und semantische Palette.
4. `resources/reference/laienmodus_einfach_reference.png` plus Analyse – ursprüngliche Einsteigerreferenz.
5. vorhandene visuelle Baselines – Regressionsevidence, aber keine automatische Designautorität bei nachweislich veraltetem Capture-Harness.

## Aktueller Gesamtzustand

### Architektur

- aktive Anwendung: `CanonicalVideoBatchFastUI` über `src/videobatch_fast/app.py`;
- kanonische Shell modular in Dashboard, Chrome, Workspace, Window, Help/Status und KPI-Mixins getrennt;
- 39B hat Tk-spezifische Shell-Komponenten bewusst als spätere Qt-Neubauten klassifiziert;
- deshalb werden in 40A keine neuen Tk-Abstraktionsschulden oder Layoutframeworks eingeführt.

### Funktionale Qualität

- letzter 39B-Nachweis: 483 Tests bestanden, 2 übersprungen, 0 fehlgeschlagen;
- Architektur-Audit: 0 Befunde, größte Python-Datei 699 Zeilen;
- Stable weiterhin blockiert durch 80/65-Coverage sowie physische KDE-X11-/Wayland- und Slow-Target-Soak-Gates.

### Visuelle Stärken

- feste semantische Navigation;
- responsiver Header;
- vier reale KPI-Karten;
- responsive Aktionsleiste;
- dreistufiges Dashboardlayout;
- vier Theme-IDs und drei Schriftprofile;
- Kontrasthelfer für Textfarben;
- sichtbare Fokus-/Statuskonzepte;
- getrennte Einsteiger- und Produktionsbereiche;
- keine vorgetäuschte Schedulerfunktion.

## Gefundene visuelle Inkonsistenzen

### 1. Standard-Theme war falsch benannt

Die kanonische Shell nennt die stabile Theme-ID `neon_gravity` bereits **Midnight Blue**. `theme.py` und die eigentliche Ressource zeigten jedoch weiterhin **Neon Gravity**. Dadurch konnten verschiedene Oberflächen desselben Programms unterschiedliche Namen für denselben gespeicherten Wert anzeigen.

**40A-Korrektur:** öffentliche Theme-Namen in `theme.py` exakt an `CANONICAL_THEME_LABELS` angeglichen; stabile IDs bleiben unverändert.

### 2. Standardpalette war nicht mehr die kanonische Palette

Vor 40A nutzte das Standard-Theme eine violett-schwarze Palette (`#070611`, `#131126`, `#20183B`). Die primäre SVG-Referenz verwendet dagegen ein tiefes Navy-System (`#061426`, `#07172A`, `#0A1D32`, `#0D2747`) mit klaren blauen Ebenen.

**40A-Korrektur:** Standardpalette auf die in der SVG tatsächlich vorkommenden Kernfarben zurückgeführt.

### 3. Primäraktion wechselte beim Hover semantisch die Farbe

Der primäre Button war gelb bzw. nach 40A blau, sein bisheriger `active`-Zustand verwendete jedoch `status_warning`. Eine normale Zeigerbewegung konnte dadurch optisch wie eine Warnung wirken.

**40A-Korrektur:** Hover/Active nutzt nun den selektierten Blauzustand; Fokus nutzt den Cyan-Fokuszustand. Warnfarben bleiben echten Warnlagen vorbehalten.

### 4. Fokus war bei Standardbuttons nicht als Randvertrag abgesichert

**40A-Korrektur:** `TButton` und `Accent.TButton` erhalten im Fokus explizit die Informations-/Fokusfarbe als Rand bzw. Fokuszustand.

### 5. Einsteigerreferenz und kanonische Produktionsreferenz besitzen unterschiedliche Grundstimmungen

Die ältere Einsteigerreferenz ist oliv-schwarz mit warmer Goldkontur. Die neuere kanonische Produktions-SVG ist Navy/Blue. Das ist kein Widerspruch, wenn die gemeinsame Semantik erhalten bleibt:

- dunkler, ruhiger Hintergrund;
- klare Ebenen;
- helle Haupttexte;
- gedämpfte Sekundärtexte;
- vier unterscheidbare Aktionsfarben;
- große verständliche Aktionen;
- technische Details nachgelagert.

40A priorisiert gemäß bestehendem Umsetzungsplan die kanonische SVG für die produktive Shell und erhält die vier semantischen Kachelfarben der Einsteigerreferenz.

### 6. Fixe Sidebarbreite weicht vom älteren Design-Token ab

Der Design-Token nennt 220–248 px; A33 hat die aktuelle Sidebar bewusst auf 188 px reduziert, um bei 1024/1280/1366 px mehr Nutzfläche ohne Scrollzwang zu erhalten.

**40A-Entscheidung:** nicht zurückdrehen. Die aktuelle responsive Nutzbarkeit ist höher zu gewichten als eine starre Pixelangleichung. Eine spätere QML-Shell soll diesen Wert responsiv statt fest modellieren.

### 7. Visueller Screenshot-Harness prüft noch die alte UI-Klasse

`scripts/capture_visual_scenarios.py` importiert und konstruiert aktuell `VideoBatchFastUI`, während der reale Programmeinstieg `CanonicalVideoBatchFastUI` nutzt.

**Risiko:** vorhandene Pixelbaselines können die aktive Shell nicht vollständig beweisen.

**40A-Entscheidung:** keine automatische Baseline-Akzeptanz. Der Harness-Umbau wird als eigener Folgeschritt behandelt, damit neue Referenzbilder erst nach realer Canonical-Shell-Aufnahme und bewusster visueller Abnahme entstehen.

### 8. Theme-Ressourcen trugen teilweise historische Marketingnamen

Die stabilen IDs sind korrekt und müssen für gespeicherte Einstellungen bestehen bleiben; sichtbare Namen sollen aber einheitlich sein:

- `neon_gravity` → Midnight Blue
- `acid_paper` → Emerald Tech
- `toxic_candy` → Violet Pulse
- `ultraviolet` → Amber Graphite

40A vereinheitlicht die öffentlichen Labels, ohne Konfigurationsmigration zu erzwingen.

### 9. Visuelle Checkpoints 4–10 sind im eigenen Designplan noch nicht vollständig abgeschlossen

Insbesondere dreispaltiger Produktionsworkflow, 12 Theme-/Schriftkombinationen, Accessibility-Härtung und finaler Referenzabgleich brauchen weiterhin ihre eigenen Evidence-Gates. 40A erklärt diese Punkte nicht künstlich für erledigt.

## 40A – tatsächlich implementierte sichtbare Änderung

### Midnight Blue

Neue Kernpalette:

| Rolle | Wert |
|---|---|
| Hintergrund | `#061426` |
| Oberfläche | `#0A1D32` |
| erhöhte Oberfläche | `#0D2747` |
| Toolbar | `#07172A` |
| Vorschau | `#030A12` |
| Haupttext | `#EAF2FF` |
| Sekundärtext | `#B8C9DA` |
| gedämpfter Text | `#8EA7C2` |
| feine Kontur | `#193756` |
| stärkere Kontur | `#31527A` |
| Primäraktion | `#2466E4` |
| Fokus/Information | `#43C6D7` |
| Erfolg | `#72E39B` |
| Warnung | `#E9AE42` |
| Fehler | `#FF6B86` |
| Auswahl | `#173F85` |
| Hover | `#123A76` |

Die für Layout und Einsteigerführung wichtigen vier Aktionsfarben Gold, Magenta, Grün und Blau bleiben erhalten.

## Abnahmekriterien 40A

40A gilt nur als bestanden, wenn:

1. Python-Kompilierung grün ist;
2. neue Reference-Alignment-Tests vollständig grün sind;
3. Designmanifest-Validator grün ist;
4. bestehender Canonical-Shell-Vertrag grün ist;
5. Vollregression keine neue Fehlfunktion zeigt;
6. Architektur-Audit weiterhin 0 Befunde meldet;
7. Release-Manifest nach allen Änderungen kanonisch neu erzeugt und geprüft ist;
8. Releasepaket deterministisch zweimal identisch gebaut wird;
9. kein Baseline-Bild automatisch ersetzt wird;
10. kein Merge nach 39B, PR #102, PR #84 oder `main` erfolgt.

## Empfohlener Folgepunkt

Nach 40A sollte als eigener visueller Evidence-Schritt der Screenshot-Harness auf `CanonicalVideoBatchFastUI` umgestellt und zunächst **capture-only** betrieben werden. Erst nach manueller Gegenprüfung gegen die Repo-Referenzen dürfen neue Pixelbaselines signiert werden.
