# Anzeigeprofilgebundene Rasterzustände

## Ziel

Das 2×2-Arbeitsraster wird projektbezogen gespeichert. Unterschiedliche Fensterauflösungen und UI-Zoomstufen erhalten getrennte Zustände.

## Profilkennung

```text
<Anwendungsbreite>x<Anwendungshöhe>@<UI-Zoom>
```

Beispiele:

```text
1280x720@100
1920x1080@100
1920x1080@140
```

Die Anwendungsgröße wird statt einer globalen Desktopgröße verwendet. Dadurch funktionieren Profile auch bei nicht maximierten Fenstern, mehreren Monitoren und virtuellen Testanzeigen zuverlässig.

## Gespeicherte Werte

Es werden keine starren Pixelpositionen gespeichert. Das Projekt speichert vier normalisierte Verhältnisse:

- `root_vertical` – Arbeitsraster zu Debug-Footer
- `grid_vertical` – obere zu untere Rasterzeile
- `top_horizontal` – Dateien zu Vorschau
- `bottom_horizontal` – Assistent zu Produktion

## Selbstheilung

Ein Profil wird automatisch verworfen und durch geprüfte Standardverhältnisse ersetzt, wenn:

- der Layoutvertrag geändert wurde,
- ein Verhältnis fehlt,
- ein Wert keine endliche Zahl ist,
- eine Rasterzelle praktisch kollabieren würde,
- Mindestgrößen für das aktuelle Fenster nicht eingehalten werden,
- die Profilkennung nicht zu Auflösung und Zoom passt.

Die Reparatur wird als verständliches Ereignis protokolliert. Originalprojekt und Mediendateien bleiben unberührt.

## Getestete Standardprofile

- kompakt: 1280×720 und 1366×768
- standard: bis 1920×1080
- groß: oberhalb 1920×1080

Die Profile werden in `registries/WORKSPACE_LAYOUT_REGISTRY.json` versioniert.
