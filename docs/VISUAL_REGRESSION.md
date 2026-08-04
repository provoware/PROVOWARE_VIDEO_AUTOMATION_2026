# Visuelle Regression

VideoBatch Fast prüft acht Referenzszenarien: vier für das Startdashboard und vier für den Arbeitsbereich.

```bash
xvfb-run -a -s '-screen 0 2560x1440x24' env PYTHONPATH=src \
  python scripts/capture_visual_scenarios.py
```

Eine beabsichtigte Änderung wird nur nach manueller Sichtprüfung übernommen:

```bash
python scripts/capture_visual_scenarios.py --accept-baselines
```

Referenzen werden nie automatisch ersetzt.
