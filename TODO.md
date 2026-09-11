# TODO – aktueller Arbeitsplan

## Zielplattform

**Kubuntu 26.04 LTS · KDE Plasma · natives Wayland · PySide6/Qt 6** ist der einzige aktive GUI-Zielpfad. X11, XWayland als GUI-Transport sowie Ubuntu 22.04/24.04 gehören nur noch zur Historie.

## Aktueller Stand

- [x] Qt6-/Wayland-Bereinigung aus PR #128 integriert.
- [x] Beschädigtes Release-Manifest und fehlende Phase-2-Dokumentklassifizierung über PR #130 repariert.
- [x] Release-Contract-Drift-Schutz und automatische Stable-Nachweisexporte über PR #131 integriert.
- [x] Release-Manifest nach PR #131 über PR #132 reproduzierbar synchronisiert und auf demselben Prüfstand grün bestätigt.
- [x] Repository-Preflight, Manifestvertrag, Qt6-Wayland-Orchestrierung und Langzeitrender-Probelauf auf dem Abschlussstand grün bestätigt.
- [ ] Physische Start- und Sichtabnahme auf dem echten Kubuntu-26.04-Plasma-Wayland-Zielrechner durchführen.
- [ ] Realen Langzeitrender mit großer Medienauswahl auf einem langsamen externen USB-Ziel vollständig durchführen.

## P0 – die zwei verbleibenden Stable-Gates

### 1. Physische Kubuntu-Abnahme

- [ ] `KUBUNTU_26_04_QT_ABNAHME.sh` auf dem Zielrechner ausführen.
- [ ] Oberfläche, Vorschau, Skalierung und Bedienbarkeit real prüfen und die Sichtfreigabe nur bei vollständig gutem Ergebnis bestätigen.
- [ ] Der erfolgreiche Lauf erzeugt `kubuntu_26_04_wayland.json` automatisch und bindet ihn an Kandidat und Manifest-Hash.

### 2. Realer Langzeitrender

- [ ] Den Vertrag aus `docs/LONG_RENDER_2.8.3-rc24.md` mit großer Medienauswahl und langsamem externen USB-Ziel ausführen.
- [ ] Wiederaufnahme, Eingabe-/Ausgabeintegrität und vollständige Hashprüfung real bestehen.
- [ ] Der erfolgreiche physische Lauf erzeugt `long_render.json` automatisch und bindet ihn an denselben Kandidaten und Manifest-Hash.

### 3. Stable-Finalisierung

- [ ] Beide automatischen Nachweise gemeinsam mit `scripts/validate_stable_acceptance.py` prüfen.
- [ ] Erst bei zwei gültigen realen Nachweisen und weiterhin grüner CI den Stable-Kanal in einem getrennten, reproduzierbaren Schritt freigeben.

## Repository-Schutz

- [ ] GitHub-Schutz für `main` aktivieren und die zentralen Prüfungen als Pflichtprüfungen festlegen. Dieser Kontoschutz kann von der aktuell verbundenen GitHub-Schnittstelle nicht administrativ eingeschaltet werden und bleibt deshalb als sichtbare manuelle Aufgabe bestehen.

## Danach – Qt-Migration abschließen

- [ ] Nach realer Zielsystemabnahme entscheiden, ob der kanonische Startpfad vollständig auf Qt Phase 3 umgeschaltet werden kann.
- [ ] Erst danach verbleibende Tk-/Legacy-UI-Pfade auf tatsächliche Restverwendung prüfen und nicht mehr benötigte Teile separat entfernen.
- [ ] Projekt-, Diagnose-, Vorschau- und Diashow-Funktionen auf dem realen Zielsystem einmal vollständig durchlaufen.

## Wartbarkeit

- [ ] Historische Nachweise weiterhin nur unter `docs/archive/` ablegen; keine alten Prüfstände zurück in den aktiven Release-Satz kopieren.
- [ ] Keine neue parallele CI-Matrix einführen, solange der Einzielvertrag Kubuntu 26.04 / Wayland gilt.
- [ ] Nach jeder Plattformänderung `PLATFORM_SUPPORT.json`, Stable-Abnahmevertrag, Nutzeranleitungen und CI gemeinsam gegen Drift prüfen.

## Abschlussregel

Automatisierte CI und headless Weston sind notwendige technische Gates, aber kein Ersatz für die physische Kubuntu-26.04-Plasma-Wayland-Abnahme. Stable bleibt bis zur realen Zielsystemprüfung und zum realen Langzeitrender gesperrt.
