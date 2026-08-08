# VideoBatch Fast – professionelle Gesamtanalyse und Umsetzungsplan

Stand: 2026-08-07
Basis: Projektquellstand plus `VIDEOBATCH_BILDVERGLEICH_CHECKLISTE_2026-08-07.txt`
Ziel: fehlerfreier RC-Kandidat mit belastbarer Soll-/Ist-Bildvergleichsauswertung.

## 1. Grobe Outline

1. **P0 – vertikale Informationsarchitektur**
   Header, KPI-Zone und Aktionsleiste mussten deutlich verdichtet werden. Der produktive Bereich erhält wieder Vorrang vor Diagnoseprosa.
2. **P0 – echte Hauptarbeitsfläche**
   Quellen/Projekt, Render Queue und Job Details werden als primäre drei Zonen direkt im Dashboard aufgebaut; Scheduler liegt darunter.
3. **P0 – visuelle Regression korrigieren**
   Der Screenshot-Runner testete zuvor die historische `VideoBatchFastUI`; er verwendet jetzt die tatsächlich gestartete `CanonicalVideoBatchFastUI`.
4. **P0 – Bildvergleich methodisch erweitern**
   Unterschiedliche Screenshotgrößen werden relativ normalisiert. Neben Mittelwert und dHash werden RMSE, geänderte Fläche, Kantendifferenz, Seitenverhältnis und Differenz-Bounding-Box ausgewertet.
5. **P1 – kompakte Topbar**
   Suchfeld, echte FFmpeg-/GPU-/Cache-Badges sowie Hilfe/Einstellungen liegen in einer Zeile. Theme-/Fontauswahl ist aus der Primärtopbar entfernt.
6. **P1 – KPI-Karten**
   Diagnoseursachen und Zeitstempel wurden aus der Primärkarte entfernt; Karten sind kompakter und semantisch akzentuiert.
7. **P1 – Sidebar / Actionbar / Footer**
   Navigation, gesperrter Scheduler, Quickactions und echte Systemmetriken wurden verdichtet und visuell konsolidiert.
8. **P1 – Queue und Jobdetails**
   Queue besitzt ein erweitertes reales Spaltenmodell; Jobdetails sind in Vorschau/Effekte/Ausgabe/Zeitplan gegliedert.
9. **Repository-Konsistenz**
   Veraltete Start-, Release-, Unicode- und Dokumentationsverträge wurden auf den tatsächlichen RC-Stand gebracht.
10. **Abschluss**
    446 automatisierte Tests bestehen unter Xvfb. Physische KDE-X11-/Wayland-Screenshotabnahme und die zwei im Checklistenkopf genannten Originalbilder bleiben externe Nachweise.

---

# 2. Faktenbasierte Bestandsanalyse

## 2.1 Tatsächlicher GUI-Einstieg

- `src/videobatch_fast/canonical_ui.py` definiert `CanonicalVideoBatchFastUI`.
- Die Klasse kombiniert Shell-, Dashboard-, KPI-, Debug-, Help-/Status- und historische UI-Mixins.
- Die reale visuelle Regression muss daher diese Klasse instanziieren.
- **Früherer Fehler:** `scripts/capture_visual_scenarios.py` erzeugte die historische `VideoBatchFastUI`; dadurch konnten visuelle Tests bestehen, obwohl die reale Canonical-Oberfläche abwich.
- **Fix:** `capture_scenario()` verwendet jetzt `CanonicalVideoBatchFastUI(root)`.

## 2.2 Vertikale Shell-Architektur

### Positionen nach Fix

- `src/videobatch_fast/canonical_shell_workspace.py:15` – `_build_ui()`; native Menüleiste wird im Canonical-Shell-Pfad nicht mehr aufgebaut.
- `src/videobatch_fast/canonical_shell_chrome.py:186` – kompakter Shell-Header.
- `src/videobatch_fast/canonical_shell_chrome.py:261` – KPI-Zone.
- `src/videobatch_fast/canonical_shell_chrome.py:414` – kompakte Actionbar.
- `src/videobatch_fast/canonical_dashboard_mixin.py:59` – Hauptdashboard.

### Ergebnis

Die Layoutreihenfolge entspricht jetzt fachlich dem Ziel:

`Topbar → KPI → Actionbar → Quellen / Queue / Jobdetails → Scheduler → Footer`

Damit ist der frühere zusätzliche sichtbare „Start/2x2-Workflow“-Layer nicht mehr die visuelle Primärarchitektur.

## 2.3 Header

### Relevante Positionen

- `canonical_shell_chrome.py:186-233` – Aufbau.
- `canonical_shell_chrome.py:235-251` – responsive Ein-Zeilen-Geometrie.
- `canonical_shell_chrome.py:253-259` – reale FFmpeg-/GPU-/Cachewerte.

### Umgesetzt

- keine Canonical-native helle Menüleiste,
- kompakte Identität,
- Suche in der Topbar,
- Systembadges aus realer Diagnose,
- Hilfe-/Einstellungen-Schalter,
- Theme und Font nicht mehr dauerhaft im Header.

### Noch offen

- echtes lokales Markenlogo statt Unicode-Play-Symbol,
- optional lokaler Profil-/Avatarindikator,
- physische 125-%-KDE-Gegenprobe.

## 2.4 KPI-Zone

### Positionen

- `canonical_shell_chrome.py:261-360` – kompakte Karten und responsive Spalten.
- `canonical_kpi_detail_mixin.py:85` – reale KPI-Datenaufbereitung.

### Fix

- dauerhafte Ursache/Timestamp-Prosa wird nicht mehr in der primären Karte gepackt,
- Medien/Queue/Effekte/Scheduler erhalten semantische Zustände,
- Kartenaktionen sind kleiner,
- Scheduler bleibt ehrlich gesperrt.

### Teilweise offen

Die Checkliste verlangt sehr spezifische Untermetriken wie Bilder/Videos/Audio bzw. Wartend/Abgeschlossen. Die aktuelle Implementierung ist bereits kompakt, aber nicht jede Ziel-Unterkachel ist vollständig als eigene Komponente umgesetzt.

## 2.5 Hauptdashboard

### Positionen

- `canonical_dashboard_mixin.py:103` – Quellen & Projekt.
- `canonical_dashboard_mixin.py:194` – Render Queue.
- `canonical_dashboard_detail_mixin.py:11` – Job Details.
- `canonical_dashboard_detail_mixin.py:70` – Scheduler.
- `canonical_dashboard_mixin.py:322` – responsive Layoutmodi.

### Fix

- Quellenfilter nach Typ,
- Queue-Spalten: Job, Modus, Effekt, Zeitplan, Status, Fortschritt, Ausgabe,
- Jobdetailtabs: Vorschau, Effekte, Ausgabe, Zeitplan,
- Schedulerstatus ohne Fake-Zeit,
- drei primäre Arbeitszonen,
- globaler Dashboardscroll wird im Drei-Spalten-Modus nicht als Standardlayout missbraucht.

## 2.6 Footer und Systemzustand

- `canonical_help_status_mixin.py:122` – Footer.
- `canonical_help_status_mixin.py:143` – Metrikaktualisierung.
- `system_metrics.py:94` – reale CPU/RAM/Cache/FFmpeg/GPU-Ermittlung.

Der Footer verwendet echte Systemdaten statt Musterwerte.

---

# 3. Bildvergleich – technische Tiefenanalyse

## 3.1 Warum der alte Vergleich unzureichend war

Ein bloßes Resize beider Bilder auf dieselbe Pixelgröße kann geometrische Abweichungen verschleiern oder künstlich erzeugen. Die Checkliste verlangt ausdrücklich proportionale Bewertung, weil IST und SOLL unterschiedliche Screenshotbreiten besitzen.

## 3.2 Neue Vergleichskette

Datei: `src/videobatch_fast/visual_regression.py`

1. EXIF-Orientierung normalisieren (`_prepared`, Zeile 31).
2. RGB/Alpha deterministisch normalisieren.
3. Beide Screenshots auf einen gemeinsamen **relativen Viewport-Canvas 960×540** abbilden (`_relative_canvas`, Zeile 43).
4. Mittlere absolute Bilddifferenz bestimmen.
5. Normalisierte RMSE bestimmen.
6. Anteil sichtbar geänderter Pixel ermitteln.
7. Relative Bounding-Box des Unterschieds bestimmen.
8. Kantendifferenz via `FIND_EDGES` bestimmen.
9. dHash/Hamming-Distanz als groben Wahrnehmungsfingerprint ermitteln.
10. Seitenverhältnis-Differenz separat melden.
11. Differenzbild aus dem normalisierten Vergleich erzeugen.

CLI: `scripts/compare_screenshots.py` erzeugt TXT, JSON und Differenz-PNG.

## 3.3 Ergebnisinterpretation

- **Mean diff**: mittlere absolute Farb-/Helligkeitsabweichung.
- **RMSE**: stärkeres Gewicht großer Abweichungen.
- **Changed pixel ratio**: wie viel der Oberfläche praktisch verändert ist.
- **Edge difference**: besonders hilfreich für verschobene Karten, Zeilen, Rahmen und Typografie.
- **dHash**: schneller globaler Wahrnehmungsvergleich.
- **Aspect delta**: verhindert falsche Gleichsetzung stark anderer Viewportproportionen.
- **Diff bbox**: zeigt, in welchem relativen Oberflächenbereich die Hauptabweichung liegt.

## 3.4 Wichtige Grenze

Die beiden im Kopf der Checkliste benannten Originaldateien
`Bildschirmfoto_2026-08-07_00-44-54.png` und
`5211edce-e218-4fea-a20e-6c152c59d48b(1).png`
sind nicht als Binärbilder im bereitgestellten Projektarchiv enthalten. Daher darf für genau dieses Paar **kein erfundener numerischer Pixelwert** angegeben werden. Die Checklistenmessungen werden als fachliche Sollvorgabe verwendet; der Vergleichsengine-Fix ist vorbereitet, sobald beide Originalbilder vorliegen.

---

# 4. Checklistenstatus – Soll/Ist-Mapping

Legende:
- **UMGESETZT** = Codeänderung vorhanden und automatisiert abgesichert.
- **TEILWEISE** = Zielstruktur vorhanden, konkrete Detailfunktion oder physische Sichtabnahme fehlt.
- **OFFEN** = noch nicht implementiert oder nur mit realem Zielsystem abschließbar.

## 4.1 P0 – Struktur / Geometrie

| IDs | Status | Umsetzung / Aktion |
|---|---|---|
| UI-001–002 | UMGESETZT | Canonical Shell baut die native Menüleiste nicht mehr auf (`canonical_shell_workspace.py:15`). |
| UI-003–005 | UMGESETZT/physisch offen | Header/KPI/Actionbar verdichtet; echte Pixelabnahme auf KDE noch offen. |
| UI-006–010 | UMGESETZT | Hauptdashboard direkt mit Quellen/Queue/Details; Drei-Spalten-Modus priorisiert. |
| UI-011 | UMGESETZT | Zoom nicht mehr als dominierende Dashboard-Hauptzeile. |
| UI-012 | UMGESETZT | Responsive Breiten-/Höhenlogik vorhanden; physische Profile weiterhin abnehmen. |

## 4.2 Header UI-013–019

- UI-013: **UMGESETZT** – Entwicklervertragsbezeichnung nicht als Primärheader.
- UI-014: **UMGESETZT** – Suche kompakt in Topbar.
- UI-015: **TEILWEISE** – Tooltip vorhanden; echtes Lupenicon/visuelle Placeholder-Perfektion noch offen.
- UI-016: **UMGESETZT** – reale FFmpeg/GPU/Cache-Badges.
- UI-017: **TEILWEISE** – Hilfe/Einstellungen vorhanden; Notification/Profile nicht vollständig.
- UI-018: **UMGESETZT** – Theme/Font aus Primärheader entfernt.
- UI-019: **OFFEN P2** – generischer lokaler Profilbutton optional.

## 4.3 Sidebar UI-020–027

- UI-020: **OFFEN P1** – lokales Markenicon statt `▶`.
- UI-021: **UMGESETZT** – kompakter Titelblock.
- UI-022: **TEILWEISE** – aktive Navigation über Theme neu kalibriert; physische Zielnähe offen.
- UI-023: **OFFEN P1** – konsistentes Offline-Line-Iconset.
- UI-024: **UMGESETZT** – Scheduler normal strukturiert, ehrlich mit Lock gesperrt.
- UI-025: **UMGESETZT** – Spacer hat keine sichtbare Sonderrahmenfunktion.
- UI-026: **TEILWEISE** – echte Systemmetriken existieren im Footer/Header, noch nicht vollständig in Sidebar gespiegelt.
- UI-027: **TEILWEISE** – reale Version vorhanden, separater Releasebadge optional.

## 4.4 KPI UI-028–036

- UI-028: **UMGESETZT** – semantische, subtilere Kartentokens.
- UI-029–032: **TEILWEISE** – kompakte reale KPI-Struktur, Ziel-Untermetriken noch nicht komplett 1:1.
- UI-033–034: **UMGESETZT** – Ursache/Timestamp aus Primärkarte entfernt.
- UI-035–036: **UMGESETZT** – kompakte Actions und semantische Farbakzente.

## 4.5 Actionbar UI-037–040

- UI-037: **UMGESETZT** – kompakter Headerframe.
- UI-038: **UMGESETZT** – Zielreihenfolge reduziert.
- UI-039: **TEILWEISE** – Backup sichtbar aber absichtlich disabled, solange keine echte Projektaktion freigegeben ist.
- UI-040: **UMGESETZT** – semantische Buttonhierarchie.

## 4.6 Hauptarbeitsbereich UI-041–058

- UI-041: **UMGESETZT** – 18/51/31 Gewichtsmodell.
- UI-042–043: **UMGESETZT** – Quellenliste und Medientypfilter.
- UI-044: **OFFEN P2** – Tags nur implementieren, wenn echtes Tagdatenmodell vorhanden/freigegeben.
- UI-045–046: **UMGESETZT** – Queue-Tabelle und Zielspalten.
- UI-047: **OFFEN P1** – Queue-Thumbnails.
- UI-048–050: **TEILWEISE** – Status/Progress real vorhanden; Kopf-/Filterdetails können weiter verfeinert werden.
- UI-051: **OFFEN P2** – Pagination/Virtualisierung erst bei real großer Queue.
- UI-052–054: **UMGESETZT** – Jobdetails + Tabs + Vorschauzone.
- UI-055: **TEILWEISE** – Preview-Öffnung vorhanden; vollständige Transportleiste nicht im Dashboard dupliziert.
- UI-056–058: **UMGESETZT/TEILWEISE** – Effekte, Ausgabe und RenderProof angebunden; Detailtiefe weiter ausbaubar.

## 4.7 Scheduler UI-059–063

- UI-059: **UMGESETZT** – breite Schedulerkarte vorhanden.
- UI-060: **OFFEN P2** – Uhrgrafik.
- UI-061: **TEILWEISE** – gesperrter Zeitplan ehrlich sichtbar, konkrete Felder fehlen.
- UI-062–063: **OFFEN P2** – erst nach verifizierter Scheduler-Systemintegration.

## 4.8 Footer UI-064–071

- UI-064: **UMGESETZT** – kompakte Metrikbar statt langer Guidance.
- UI-065–069: **UMGESETZT** – CPU, RAM, FFmpeg/GPU, Cache, Projektpfad aus realen Daten.
- UI-070: **OFFEN P2** – echte Backuphistorie.
- UI-071: **TEILWEISE** – realer Gesamtstatus vorhanden, Aggregationslogik kann noch strenger werden.

## 4.9 Stil UI-072–081

- UI-072–074: **UMGESETZT** – Navy/Blue/Violet/Green/Amber-System im Theme.
- UI-075–079: **UMGESETZT/physisch offen** – kompaktere Typografie, weniger Rahmen, Spacingtokens; Screenshotabnahme nötig.
- UI-080: **UMGESETZT** – StatusPill-Stil vorhanden.
- UI-081: **OFFEN P1** – konsistentes Offline-Iconset bleibt größter sichtbarer Detailrest.

---

# 5. Repository-/Fehleranalyse und Fixes

## 5.1 Baseline vor Fix

- 424 Tests bestanden.
- 17 Fehler im direkten Headless-Lauf.
- 8 davon waren ausschließlich fehlende Tk-Anzeige (`TclError`).
- 9 waren echte veraltete Repository-/Releaseverträge.

## 5.2 Reparierte Inkonsistenzen

1. Launcher-Verträge auf tatsächlichen Startpfad synchronisiert.
2. Unicode-Testfixture korrekt als `bühne_äöü_测试.png` hergestellt.
3. fehlenden RC-Qualitätsversuchsbericht ergänzt.
4. Release-Dateivertrag mit vorhandenen `_save_`-Dateien synchronisiert.
5. Dokumentationstests an Canonical-Help-Modul angepasst.
6. dynamische GitHub-Dispatch-Verträge aktualisiert.
7. Architekturgrenze eingehalten durch Extraktion von `canonical_dashboard_detail_mixin.py`.
8. visuellen Runner auf reale Canonical-App umgestellt.
9. neue Bildvergleichsmetriken und Regressionstests ergänzt.

## 5.3 Aktueller automatisierter Stand

`PYTHONPATH=src xvfb-run -a python -m pytest -q`

**446 Tests bestanden.**

Architekturaudit:

- 115+ produktive Module,
- größte geprüfte Datei unter dem Architekturbudget,
- 0 Architekturbefunde.

---

# 6. Vollständiger nummerierter Umsetzungsplan ab aktuellem Stand

## 6.1 P0 – reale Bildreferenzen und Geometrieabnahme

1. Die beiden Original-PNGs bereitstellen.
2. `scripts/compare_screenshots.py` mit SOLL und aktuellem Canonical-Screenshot ausführen.
3. Bericht aus Mean/RMSE/Changed/Edges/dHash/Aspect/BBox sichern.
4. Fensterprofile 1440×900, 1500×920, 1920×1080 aufnehmen.
5. Schriftprofile 90 %, 105 %, 125 % aufnehmen.
6. Geometriewächter auf tatsächliche gemessene Zielzonen kalibrieren.
7. A-001 bis A-022 einzeln mit Screenshotbeleg abhaken.

**Aufwand:** M
**Abschluss:** kein Clipping/Overlap, Hauptarbeitsbereich im oberen Drittel, Kernzonen gleichzeitig sichtbar.

## 6.2 P1 – Sidebar-Iconisierung

1. vorhandene lokale Assets inventarisieren,
2. ein einziges Offline-SVG/PNG-Iconraster definieren,
3. Unicode-Symbole ersetzen,
4. DPI-Profile 100/125/150/200 % testen,
5. Fokus-/Disabled-/Activezustände prüfen.

**Aufwand:** M

## 6.3 P1 – KPI-Zielmetriken

1. Medien nach Bild/Video/Audio aggregieren,
2. Queue nach wartend/abgeschlossen aggregieren,
3. aktives Preset + RenderProof kompakt spiegeln,
4. Scheduler-Karte strukturell vorbereiten, aber weiterhin gesperrt,
5. Primärkarte weiterhin frei von Ursache/Timestamp halten.

**Aufwand:** M

## 6.4 P1 – Queue-Detailtiefe

1. Thumbnailcache an Queuezeilen anbinden,
2. StatusPills pro Job,
3. Fortschrittsdarstellung pro Zeile,
4. Queueheader mit Suche/Filter,
5. bei real großen Queues erst dann Pagination/Virtualisierung aktivieren.

**Aufwand:** L

## 6.5 P1 – Vorschau-Transport

1. bestehende Playersteuerung wiederverwenden,
2. im Detailtab nur unterstützte Funktionen einbetten,
3. Play/Pause, Seek, Zeit und Lautstärke nur bei real verfügbarem Medium aktivieren,
4. keine zweite Zustandslogik erzeugen.

**Aufwand:** M

## 6.6 P2 – Scheduler

Erst nach Checkpoint-5-Freigabe:

1. Uhrgrafik,
2. Datum/Uhrzeit,
3. Energieoptionen,
4. geplante Ausführung,
5. Benachrichtigung,
6. Suspend/Resume-Systemtests.

**Aufwand:** XL
**Aktuell:** bewusst nicht releaseblockierend für VideoBatch ohne Schedulerfreigabe.

## 6.7 P2 – Backupstatus

1. vorhandene echte Backuphistorie anbinden,
2. letzten erfolgreichen Zeitpunkt anzeigen,
3. keine künstliche Stable-/OK-Anzeige erzeugen.

**Aufwand:** S–M

---

# 7. Release-Abnahmekriterien

Ein Releasekandidat gilt technisch erst dann als belastbar, wenn:

1. komplette Pytest-Suite unter Xvfb grün ist,
2. Architekturaudit 0 Befunde liefert,
3. Registry-/Dokumentations-/Versionsverträge grün sind,
4. Canonical-App der einzige Screenshot-Testgegenstand ist,
5. die Original-SOLL/IST-Bilder numerisch verglichen wurden,
6. A-001 bis A-022 physisch geprüft wurden,
7. kein Musterwert als Produktwert hartcodiert wurde,
8. X11-/Wayland-Abnahme auf echtem KDE erfolgt ist,
9. Langzeitrender-Gate abgeschlossen ist,
10. erst danach das finale Release-Manifest neu erzeugt wird.

---

# 8. Zweitanalyse nach den Fixes

Die erneute Gesamtanalyse ergibt:

- Die größten strukturellen P0-Abweichungen sind im Code beseitigt.
- Die visuelle Regression prüft jetzt die richtige Anwendungsklasse.
- Die Vergleichsengine ist für unterschiedlich große Screenshots deutlich belastbarer.
- Das Dashboard besitzt die Zielzonen Quellen/Queue/Details tatsächlich als Primärarchitektur.
- Es werden keine Checklisten-Musterdaten als Produktwerte erfunden.
- Die größte verbleibende Unsicherheit ist **nicht mehr Code-Stabilität**, sondern die physische Referenzabnahme gegen die zwei Originalbilder und KDE-X11/Wayland.
- Größte verbleibende sichtbare Detailpunkte: Iconset, Queue-Thumbnails, KPI-Untermetriken und optionale Schedulerdetails.
