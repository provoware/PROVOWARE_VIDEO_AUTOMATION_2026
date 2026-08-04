# VideoBatch Fast 2.8.3-rc19 – Sichtbarkeit, Zoom und Auto-Diashow

## Oberfläche

- kontraststärkere Farben und deutlichere Zustände
- Strg+Mausrad zoomt jeden Hauptbereich separat
- globale Schriftsteuerung direkt im Header
- unabhängige Zoomwerte werden gespeichert

## Mehrdatei-Diashow

- ein Auftrag pro Audio
- alle ausgewählten Bilder werden in jedem Auftrag verwendet
- Audiodauer wird automatisch per FFprobe ermittelt
- Bild- und Überblendzeiten werden exakt auf die Audiodauer verteilt
- Ubuntu-kompatible feste Zeitbasis für FFmpeg-xfade
- Videos werden in diesem Bildmodus nicht stillschweigend verarbeitet, sondern sichtbar ausgelassen
