# Verknüpfte visuelle HTML-Prüfung

## Dateien
- `visual_inspection/index.html` – vollständig offline nutzbare Prüfoberfläche
- `VISUAL_INSPECTION_MANIFEST.json` – maschinenlesbarer aktueller Prüflauf
- `registries/VISUAL_INSPECTION_REGISTRY.json` – dauerhafter Erzeugungs- und Verknüpfungsvertrag
- `registries/VISUAL_REGRESSION_REGISTRY.json` – Szenarien und Grenzwerte

## Funktionen
- Filter nach Dashboard, Arbeitsbereich, Dialogen und offenen Befunden
- Referenz-, Ist- und Differenzbilder
- Pflichttexte und Vergleichswerte
- direkte Links zu JSON-Manifest und Prüfregistry
- eingebetteter Manifest-Snapshot für Offline-Nutzung

## Erzeugung
```bash
PYTHONPATH=src python scripts/build_visual_inspection.py
```
