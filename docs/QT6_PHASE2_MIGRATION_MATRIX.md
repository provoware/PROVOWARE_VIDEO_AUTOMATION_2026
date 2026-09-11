# Qt 6 Phase 2 – Inventar, Migrationsmatrix und Validierungsplan

Stand: 2026-09-10  
Branch: `feature/qt6-ui-phase1`  
Ziel: Die in Phase 2 festgelegten Bedienbereiche vollständig nativ mit PySide6/Qt 6 bereitstellen, ohne den stabilen `main`-Startpfad vorzeitig zu ersetzen.

## 1. Sicherheits- und Migrationsprinzip

1. Der verifizierte FFmpeg-/Job-/Recovery-Core wird nicht neu erfunden.
2. Tk wird nur an der UI-Grenze ersetzt.
3. Lang laufende FFprobe-/FFmpeg-/Waveform-/Verzeichnisscan-Arbeit bleibt außerhalb des Qt-GUI-Threads.
4. Originaldateien werden durch die Qt-Migration nicht verändert.
5. Der Legacy-Tk-Pfad bleibt bis zur vollständigen Gesamtparität als Rückfallpfad vorhanden.
6. Ein Qt-Bereich gilt erst als fertig, wenn Syntax-, Tk-Freiheits-, Core-Anbindungs- und Repository-Gates bestanden sind.

## 2. Vollständiges Funktionsinventar

| Nr. | Funktionsbereich | Bestehende Kernmodule | Bisherige UI-Bindung | Qt-Stand |
|---:|---|---|---|---|
| 1 | Programmstart / Laufzeitprüfung | `runner.py`, `probe.py` | `canonical_ui.py`, `ui.py` | Phase 1 vorhanden |
| 2 | Audio-/Medienlisten, Drag & Drop | Core-Dateipfade | `ui_media_panels_mixin.py` | Phase 1 vorhanden |
| 3 | Medienbrowser / Mehrfachauswahl | `incremental_directory.py`, `media_dialog_support.py` | `media_import_dialog.py`, `thumbnail_grid.py` | **Phase 2 Qt umgesetzt** |
| 4 | Auswahl-/Live-Vorschau | `preview_service.py`, `selection_preview_controller.py` | `ui_selection_preview_mixin.py` | **Phase 2 Qt umgesetzt** |
| 5 | Paarbildung / Auftragsplanung | `jobs.py`, `models.py` | Tabellenansicht | Phase 1 vorhanden |
| 6 | Schnellmodi / FFmpeg-Befehl | `quick_modes.py`, `command_builder.py` | Einstellungen | Phase 1 vorhanden |
| 7 | Verarbeitung / Fortschritt / Abbruch | `runner.py`, `runner_process.py`, `app_events.py` | Status-/Fortschrittsanzeige | Phase 1 vorhanden |
| 8 | Diashow je Audio | `slideshow.py`, `jobs.py` | `ui_slideshow_mixin.py` | **Phase 2 Qt umgesetzt** |
| 9 | Bildreihenfolge / manuelles Sortieren | `slideshow_sequence.py` | `slideshow_editor.py` | **Phase 2 Qt umgesetzt** |
| 10 | Start-/Endanker | `slideshow_sequence.py` | `slideshow_editor.py` | **Phase 2 Qt umgesetzt** |
| 11 | Überblendungen | `slideshow.py` | `ui_slideshow_mixin.py` | **Phase 2 Qt umgesetzt** |
| 12 | Waveform | `audio_waveform.py` | `slideshow_editor.py` | **Phase 2 Qt/QPainter umgesetzt** |
| 13 | Szenenmarker / Szenensync | `audio_waveform.py`, `slideshow.py` | `ui_slideshow_mixin.py` | **Phase 2 Qt umgesetzt** |
| 14 | Plugin-Freigabedialoge | Plugin-Core | `workflow_dialogs.py` | **Phase 2 Qt umgesetzt** |
| 15 | Update-Entscheidungsdialog | Update-Core | `workflow_dialogs.py` | **Phase 2 Qt umgesetzt** |
| 16 | Recovery-Entscheidungsdialog | Recovery-Core | `workflow_dialogs.py` | **Phase 2 Qt umgesetzt** |
| 17 | Ablage-/Archiv-Prüfdialog | Archiv-Core | `workflow_dialogs.py` | **Phase 2 Qt umgesetzt** |
| 18 | Visuelle Freigabe | Approval-Core | `workflow_dialogs.py` | **Phase 2 Qt umgesetzt** |
| 19 | Projekt laden/speichern / Autosave | Projektmodule | `ui_dashboard_project_mixin.py` | spätere Qt-Parität |
| 20 | Plugin-Verwaltung / Sandbox-Workflow | Pluginmodule | mehrere Legacy-UI-Bereiche | spätere Qt-Parität |
| 21 | Update-Ausführung | Updatemodule | `ui_services_mixin.py` | spätere Qt-Parität |
| 22 | Archiv-Ausführung | Archivmodule | `ui_services_mixin.py` | spätere Qt-Parität |
| 23 | Diagnose / Assurance / Fault-Lab | Diagnosemodule | Legacy-UI | spätere Qt-Parität |
| 24 | Vollständige Workspace-/Dashboard-Navigation | UI-Komposition | `ui_workspace_grid_mixin.py`, `ui_components.py` | spätere Qt-Parität |
| 25 | Theme-/Schrift-/Barrierefreiheitsparität | UI-Konfiguration | Tk-Theme/Legacy | Qt-Basis vorhanden, Vollparität später |
| 26 | Release-/Bootstrap-/Paketierung | Skripte/CI | UI-unabhängig | unverändert weiterverwenden |

## 3. Tk → Qt Migrationsmatrix für Phase 2

| Legacy | Qt-Ersatz | Strategie |
|---|---|---|
| Tk `Canvas` Vorschau | `QLabel` + `QPixmap` | gecachte FFmpeg-PNGs direkt anzeigen |
| Tk Preview-Worker | `SelectionPreviewController` + Qt `Signal` | bestehenden threadsicheren Controller wiederverwenden |
| `ThumbnailOrderStrip(ttk.Frame/Canvas)` | `QListWidget` IconMode + InternalMove | Drag & Drop nativ, Anker bleiben geschützt |
| `WaveformSceneView(ttk.Frame/Canvas)` | `QWidget.paintEvent()` + `QPainter` | Peaks und Marker ohne Tk zeichnen |
| Tk Diashow-Mixin | `SlideshowPanel` | Zustand/Bedienung in eigenem Qt-Baustein |
| Tk `Toplevel` / `ttk` Dialoge | `QDialog` | modal, skalierbar, native Buttons/Checkboxen |
| Tk Medienimport | `QDialog` + inkrementeller Scan + `QListWidget` | kein Blockieren des GUI-Threads |
| Tk Messagebox | `QMessageBox` | native Qt-Fehler-/Hinweisdialoge |

## 4. Nummerierte Umsetzung Phase 2

### 4.1 Vorschau
- `PreviewPanel`
- asynchron über bestehenden `SelectionPreviewController`
- stale-request Schutz über Token
- Bild/Video via gecachtem FFmpeg-PNG
- Audio als Metadatenansicht
- skalierende `QPixmap`-Darstellung
- kontrolliertes Shutdown des Preview-Workers

### 4.2 Diashow
- Paarweise / „Alle Bilder je Audio“
- A–Z, Aufnahmezeit, Zufall, Umkehren
- manuelles Drag & Drop
- Start-/Endanker
- Übergangspresets aus bestehendem `slideshow.py`
- reale `build_jobs(..., scene_analyses=...)`-Anbindung

### 4.3 Waveform und Szenenanalyse
- bestehendes `analyze_audio()` bleibt Core
- Analyse außerhalb GUI-Thread
- `QPainter` statt Tk Canvas
- Intro / Beat / Ruhe / Drop / Outro sichtbar
- Szenensync wird an `BatchOptions.slideshow_scene_sync` weitergegeben

### 4.4 Spezialdialoge
- `GuidedDecisionDialog`
- Plugin-Freigabe
- Plugin Approve/Revoke/Cancel
- Update-Assistent
- Recovery
- Ablageprüfung
- visuelle Freigabe
- Qt-Medienbrowser für Audio sowie Bild/Video

## 5. Validierung

Pflichtgates:

1. Python-AST / Compile: alle Phase-2-Dateien syntaktisch gültig.
2. Tk-Freiheit: kein `tkinter`, `ImageTk`, `Toplevel`, `mainloop` in Phase-2-Modulen.
3. Core-Wiederverwendung:
   - `SelectionPreviewController`
   - `analyze_audio`
   - `slideshow_sequence`
   - `build_jobs`
   - `scan_directory_batches`
4. Szenensync-Vertrag: `scene_analyses` wird beim Jobaufbau übergeben.
5. Dialog-Parität: alle vier Factory-Dialoge plus zwei Spezialklassen vorhanden.
6. Repository-Preflight: Compile, Ruff, MyPy/Bandit/pip-audit, Manifest.
7. Zielplattform-CI: Ubuntu-26.04-Basis mit KDE-/Wayland-Laufzeitteilmenge und nativem Qt-Wayland-Backend.
8. Reale Qt-GUI-Prüfung auf Kubuntu 26.04 Plasma Wayland bleibt ein eigener Desktop-Gate und darf nicht durch reine Headless-/Core-CI ersetzt werden.

## 6. Abgrenzung

Phase 2 schließt die ausdrücklich geplanten Bereiche **Vorschau, Diashow, Waveform/Szenenanalyse und Spezialdialoge einschließlich Medienbrowser** im nativen Qt-Pfad. Sie löscht die alten Tk-Dateien noch nicht. Projektverwaltung, komplette Workspace-Navigation, Diagnoseoberflächen und weitere seltene Legacy-UI-Funktionen werden erst nach eigener Qt-Parität aus dem Rückfallpfad entfernt.
