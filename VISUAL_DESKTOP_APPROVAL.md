# Visuelle Desktop-Abnahme 2.8.3-rc24

Status: **physische Stable-Abnahme offen**

Die automatisierte visuelle Regression umfasst **22/22 bestandene Szenarien**. Zusätzlich steht ein expliziter physischer Desktop-Harness für KDE Plasma bereit. Er prüft pro Sitzung neun Größen-/Skalierungsprofile und exportiert Evidence nur bei gesetztem `VIDEOBATCH_PHYSICAL_ACCEPTANCE=1`, aktivem nativen Display und vollständig bestandenem Lauf.

Für Stable fehlen weiterhin zwei reale, getrennte Zielsystemnachweise:

- KDE Plasma unter X11
- KDE Plasma unter Wayland

CI, Xvfb oder ein historisch signierter älterer Stable-Stand ersetzen diese beiden physischen Abnahmen nicht. Jeder neue Nachweis ist an Kandidat, `RELEASE_MANIFEST.json` und den jeweils aktuellen Source-Fingerprint gebunden; spätere relevante Quelländerungen machen ihn automatisch ungültig.
