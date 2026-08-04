# Kubuntu-Kompatibilitätsmatrix – automatische Ergebnisdokumentation

Der Workflow `.github/workflows/kubuntu-build-matrix.yml` prüft VideoBatch Fast 2.8.3-rc24 auf vier Kombinationen:

- Ubuntu 22.04 / X11
- Ubuntu 22.04 / Wayland
- Ubuntu 24.04 / X11
- Ubuntu 24.04 / Wayland

## Ablauf

1. Jeder Matrix-Job schreibt einen maschinenlesbaren Statusnachweis.
2. Alle Einzel- und Diagnoseartefakte werden auch bei Fehlern hochgeladen.
3. Ein Abschlussjob sammelt die vier Statusdateien.
4. Der Abschlussjob erstellt `KUBUNTU_MATRIX_SUMMARY.json` und `KUBUNTU_MATRIX_SUMMARY.md`.
5. Das Ergebnis wird automatisch in Issue #12 veröffentlicht.
6. Issue #12 wird ausschließlich geschlossen, wenn alle vier Kombinationen erfolgreich sind.

Die Artefakte werden 30 Tage aufbewahrt. Eine manuelle Run-ID oder Actions-URL muss nicht mehr kopiert werden.
