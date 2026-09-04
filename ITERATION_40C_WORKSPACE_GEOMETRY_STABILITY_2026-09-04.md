# Iteration 40C · Workspace Geometry Stability

## Ausgangsbefund
Im realen Queue-/Produktions-Screenshot waren die oberen Workflowkarten scheinbar leer bzw. angeschnitten. Tabellenkörper und Scrollleisten dominierten, während Kartenkopf und erste Zeilen außerhalb des sichtbaren Ankers lagen.

## Ursache
`ScrollableWorkflowGrid.refresh()` rief während des Widget-Aufbaus synchron `update_idletasks()` auf. Zusammen mit dynamischen KPI-`wraplength`-Änderungen auf Karten-`<Configure>` konnte dadurch eine Geometrie-Rückkopplung entstehen. Zusätzlich blieb die vertikale Scrollposition eines Workflowtabs bei normaler Navigation erhalten.

## Korrektur
- Workflow-Refresh ohne rekursives Leeren der globalen Tk-Idle-Queue.
- KPI-Wraps idempotent aus der stabilen Zeilenbreite statt aus rückgekoppelten Kartenbreiten.
- Deterministischer Top-Anker bei normaler Shell-Navigation.
- Gezielte Unterkarten-Sprünge bleiben unverändert möglich.

## Nicht verändert
Renderlogik, Queue-Aufträge, Medienverarbeitung, FFmpeg-Kommandos und Recovery-Fachlogik.

## Stable-Status
Keine Stable-Freigabe: Coverage 80/65, physische KDE-X11/Wayland-Abnahme und realer Large-Media-/Slow-Target-Soak bleiben eigenständige Gates.
