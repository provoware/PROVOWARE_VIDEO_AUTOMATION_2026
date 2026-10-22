# PROVOWARE-Raster V1 – Wiederverwendung ohne VideoBatch

Dieser Ordner enthält eine **eigenständige Python-Bibliothek ohne Zusatzpakete**. Sie gehört logisch zum PROVOWARE-Standard, nicht zur Videoverarbeitung. Sie berechnet aus **800×600 Referenzfläche** und **120×80 Feinraster** relative Koordinaten und entscheidet anhand des tatsächlich verfügbaren Inhaltsplatzes, ob Bereiche **gleich breit nebeneinander** oder **untereinander** liegen.

## In anderen Python-Projekten verwenden

1. Den vollständigen Ordner `src/provoware_grid/` unverändert in das neue Projekt unter `src/` übernehmen.
2. Dort `PYTHONPATH=src python -m provoware_grid` ausführen. Der Befehl prüft die Referenzmatrix **ohne Netzwerk, Qt oder Videodateien**.
3. In eigenem Code:
   ```python
   from provoware_grid import choose_columns, grid_area
   columns = choose_columns(800 - 20, zoom_percent=110, panel_min_width=320)
   position = grid_area(1, 1, 60, 40)  # x=0, y=0, Breite=0,5, Höhe=0,5
   ```
4. Die Darstellung erfolgt anschließend mit HTML/CSS, Qt oder einem anderen Fenstersystem. Die Bibliothek selbst zeichnet nichts.

**Wichtig:** `grid_area` liefert **relative Verhältnisse**, keine fixen Pixelpositionen. `choose_columns` schützt Mindestbreiten, auch wenn große Schrift aktiv ist. Ein 800×600-Fenster bleibt nur bedienbar, wenn die Oberfläche bei Platzmangel vertikal scrollen kann. Dieses Modul garantiert weder Textmessungen noch vollständige visuelle Barrierefreiheit ohne tatsächlichen Renderer.

**Gemeinsamer Vertrag:** `config/contracts/PROVOWARE_RESPONSIVE_GRID_V1.json`.  
**Fachstandard:** `docs/design/PROVOWARE_RESPONSIVE_GRID_V1.md`.  
**Offline-HTML-Beispiel:** `visual_inspection/provoware_grid_reference.html`.

## Versionierung und Kompatibilität

Die öffentliche API (`grid_area`, `nearest_zoom`, `choose_columns`, `evaluate_matrix`) wird durch eigenständige Tests kontrolliert. Eine Änderung des Rasters, der Eingabeprüfung oder des Spaltenverhaltens verlangt einen dokumentierten Versionswechsel und neue Regressionstests. Qt ist ausschließlich ein **Adapter**, kein Teil dieses Moduls.
