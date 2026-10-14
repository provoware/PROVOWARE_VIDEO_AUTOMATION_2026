# Verbindlicher VideoBatch-Entwicklungsplan – 14. Oktober 2026
Masterauftrag: https://github.com/provoware/PROVOWARE_VIDEO_AUTOMATION_2026/issues/234

**Status:** Geplant. Keine Implementierung, keine Stable-Freigabe. Offline-first; Originalmedien nie verändern. Ziel: Kubuntu 26.04, Plasma/Wayland, Qt/PySide6.

## A – Ausgangslage und Prüfgrundlage
A1 Startpfade und Qt-Fenster inventarisieren. A2 doppelte Tabs/Widgets und alte Layout-Defekte erfassen. A3 Basis-Screenshots bei 100/125/150/200 Prozent. A4 CI, Render- und Performance-Baseline.
**CP-A:** Reproduzierbare Befunde und priorisierte Risiken dokumentiert.

## B – Dashboard und Layout
B1 Dauerhaft sichtbare globale Leiste mit **Auflösung, Qualität, Effekt, Ausgabeordner**, erreichbar auf **jeder** Seite. B2 alte, doppelte Steuerfelder entfernen. B3 vier Seiten **Dateien | Produktion | Erweiterte Einstellungen | Werkzeuge/Diagnose**. B4 Dateiseite mit Audio-/Bild-Video-Liste und großer Vorschau; verschiebbare Trennlinien. B5 Produktionsseite mit Aufträgen, Fortschritt, Ergebnissen. B6 Spezialfunktionen separat. B7 keine wiederholten Hilfetexte/KPI-Karten, knapper Status.
**CP-B:** Keine Duplikate, alle Kernfunktionen unmittelbar erreichbar, kein horizontales Scrollen.

## C – Einstellungs- und Renderlogik
C1 Zentrales, versioniertes Zustandsmodell. C2 Auflösung Original/HD/Full HD/QHD/UHD. C3 Qualität Schnell/Ausgewogen/Hoch/Maximum unabhängig von Auflösung. C4 Effekte einschließlich Kein Effekt. C5 Ausgabeort anzeigen/ändern/öffnen und validieren. C6 Vorrang: ausdrücklich gewählte Werte > bewusst angewandte Schnellvorlage > Standard. C7 `quick_modes.py` und `processing_options_for_job` auf versteckte Überschreibung prüfen, echte Jobparameter validieren. C8 gespeicherte Profile, Migration, Defektbehandlung testen.
**CP-C:** Anzeige, Persistenz und tatsächlicher Renderauftrag stimmen überein.

## D – Medienbrowser
D1 Einheitlicher Importbrowser für alle Wege. D2 echte kleine Bilder statt nur Icon-Raster. D3 Anklicken zeigt Bild sofort groß, ohne Beschnitt. D4 Videos mit Standbild/optionaler Wiedergabe, Audio sekundär mit Infos. D5 Drei Spalten Ordner | Dateien | Vorschau; Größen einstell-/speicherbar. D6 Thumbnailgrößen, Liste/Raster, Mehrfachauswahl, Filter, Tastatur, Leertaste-Schnellansicht. D7 Hintergrundgenerierung mit Priorisierung sichtbarer Dateien, Abbruch bei Ordnerwechsel. D8 einzeilige Dateinamen, Metadaten bei Auswahl. D9 Fehlerfälle defekter Medien.
**CP-D:** Reale Bild-, Audio-, Videobeispiele, große Verzeichnisse und Bedienung getestet.

## E – SQLite-Medienindex und Cache
E1 Genau drei über XDG ermittelte Wurzeln: **Videos, Downloads, Bilder**, inkl. Unterordnern, konfigurierbar. E2 Ausschließlich unterstützte Bild-, Audio- und Videoformate indexieren; andere Dateien nicht analysieren (Verzeichniseinträge müssen trotzdem gesichtet werden). E3 `.git`, `node_modules`, `.venv`, `venv`, `__pycache__`, `build`, `dist` sowie konfigurierbare Ausschlüsse ignorieren; Ordner-Symlinks nicht verfolgen. E4 SQLite-Datenbank, Schema-Versionen, WAL, Transaktionen, Wiederaufbau. E5 separate Thumbnail-Dateien mit Versionsmerkmalen, Größenlimit und Reinigung. E6 zuletzt bekannte Dateien sofort anzeigen, aber unbestätigte Einträge kennzeichnen. E7 asynchronen Abgleich priorisiert für sichtbare Ordner ausführen (Dateigröße und mtime_ns als schnelle Merkmale). E8 inotify im Betrieb; Neustart-Abgleich für Änderungen bei ausgeschaltetem Programm. E9 keine falsche Löschung bei nicht erreichbaren Laufwerken, Fehler bei Rechten, Watcher-Überlauf, Scanabbruch, korruptem Cache abfangen. E10 Originalquellen direkt vor Rendern erneut prüfen. E11 Kalt-/Warmstarts und 1.000/10.000/100.000 Dateien inkl. Fehler-Injektion benchmarken.
**CP-E:** Schnelle GUI ohne Blockaden, begrenzte Ressourcen, nachvollziehbare Messergebnisse, keine Beschädigung von Originalen.

## F – Schrift und Barrierefreiheit
F1 Mindestens zwölf Punkt Normaltext. F2 zentrale Skalierung von Tabellen, Listen, Dialogen und Icons. F3 Fokus, Kontrast, Tastatur, sichtbare Kurzmeldungen, vollständige Namen auf Abruf. F4 flexible Bereiche und Fenstergrößen. F5 reale Kubuntu-26.04/Plasma/Wayland-Sichtprüfung bei 100/125/150/200 Prozent.
**CP-F:** Kernsteuerungen nicht abgeschnitten; wenn nötig responsive Detailansichten statt unbedienbarer Verkleinerung.

## G – Freigabe
G1 Nachweise CP-A bis CP-F sammeln. G2 Regression der Render-, Diashow- und Abbruchfunktionen. G3 reale Ausgabevideos kontrollieren. G4 README und Handbuch aktualisieren. G5 reproduzierbaren Build und CI prüfen. G6 gesonderte reale Stable-Abnahme.
**CP-G:** Alle erforderlichen Nachweise vorhanden, keine kritischen/hohen Fehler offen, ausdrückliche Freigabe.

## Agentenregeln
Phasen A → B → C → D → E → F → G als kleine, abhängige PRs umsetzen; B/C besonders eng koordinieren. Jeder PR mit Testbericht, Checkpoint, bei GUI Screenshot vorher/nachher, Rückfallweg und Verweis auf #234. Weder automatisch mergen noch Stable ohne bestandene Gates freigeben.

## Relevante vorhandene Dateien
`src/videobatch_fast/qt_workspace_layout.py`, `qt_main_layout.py`, `qt_source_panel.py`, `qt_media_import_dialog.py`, `qt_media_list.py`, `qt_theme.py`, `qt_ui_polish.py`, `quick_modes.py`. Die Symbolansicht des Importdialogs erzeugt aktuell keine echten Thumbnail-Icons; einzelne Schriftgrößen sind 8,5 bzw. 9,5 Punkt.
