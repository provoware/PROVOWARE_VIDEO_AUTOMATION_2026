# TODO – aktueller Arbeitsplan

## Zielplattform

**Kubuntu 26.04 LTS · KDE Plasma · natives Wayland · PySide6/Qt 6** ist der einzige aktive GUI-Zielpfad. X11, XWayland als GUI-Transport sowie Ubuntu 22.04/24.04 gehören nur noch zur Historie.

## P0 – vor Merge von PR #128

- [x] Alte 22.04/24.04-×-X11/Wayland-Matrix-Infrastruktur aus dem aktiven Repo entfernt.
- [x] Qt-Phase-2-Smoke auf den aktuellen Tabnamen `Weitere Werkzeuge` synchronisiert.
- [x] Stable-Abnahmevertrag auf Kubuntu 26.04 Plasma Wayland + Langzeitrender reduziert.
- [ ] Alle GitHub-CI-Gates auf dem finalen Bereinigungs-Commit grün bestätigen.
- [ ] Reale Start- und Sichtabnahme mit `KUBUNTU_26_04_QT_ABNAHME.sh` auf dem Zielrechner durchführen.
- [ ] Befunde aus der realen Abnahme nur als kleine reproduzierbare Folgepatches korrigieren.

## P1 – Stable-Gates

- [ ] `kubuntu_26_04_wayland.json` für den unveränderten finalen Kandidaten erzeugen und mit `scripts/validate_stable_acceptance.py` prüfen.
- [ ] Realen Langzeitrender mit großer Medienauswahl und langsamem externem Ziel durchführen.
- [ ] `long_render.json` für denselben Kandidaten und denselben Manifest-Hash erzeugen.
- [ ] Erst wenn beide Nachweise grün sind, Stable-Finalisierung zulassen.

## P1 – Qt-Migration abschließen

- [ ] Nach realer Zielsystemabnahme entscheiden, ob der kanonische Startpfad vollständig auf Qt Phase 3 umgeschaltet werden kann.
- [ ] Erst danach verbleibende Tk-/Legacy-UI-Pfade auf tatsächliche Restverwendung prüfen und nicht mehr benötigte Teile separat entfernen.
- [ ] Projekt-, Diagnose-, Vorschau- und Diashow-Funktionen auf dem realen Zielsystem einmal vollständig durchlaufen.

## P2 – Wartbarkeit

- [ ] Historische Nachweise weiterhin nur unter `docs/archive/` ablegen; keine alten Prüfstände zurück in den aktiven Release-Satz kopieren.
- [ ] Keine neue parallele CI-Matrix einführen, solange der Einzielvertrag Kubuntu 26.04 / Wayland gilt.
- [ ] Nach jeder Plattformänderung `PLATFORM_SUPPORT.json`, Stable-Abnahmevertrag, Nutzeranleitungen und CI gemeinsam gegen Drift prüfen.

## Abschlussregel

Automatisierte CI und headless Weston sind notwendige technische Gates, aber kein Ersatz für die physische Kubuntu-26.04-Plasma-Wayland-Abnahme. Stable bleibt bis zur realen Zielsystemprüfung und zum realen Langzeitrender gesperrt.
