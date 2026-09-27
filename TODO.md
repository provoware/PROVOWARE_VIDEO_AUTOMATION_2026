# TODO – Stable-Finalisierung 2.8.3-rc24

## Fokus

**Zielplattform:** Kubuntu 26.04 LTS · KDE Plasma · natives Wayland · PySide6/Qt 6.

Der automatisierte Repository-, Release-, Qt6- und Qualitätsstand ist grün. Es bleiben bewusst nur **zwei reale P0-Freigaben**, die CI nicht ersetzen kann.

## P0 – jetzt

### 1. Physische Kubuntu-Abnahme

- [ ] `KUBUNTU_26_04_QT_ABNAHME.sh` auf dem echten Kubuntu-26.04-Plasma-Wayland-Zielrechner ausführen.
- [ ] Oberfläche, Vorschau, Skalierung, Tastaturbedienung und normalen Startpfad real prüfen.
- [ ] Sichtfreigabe nur bei vollständig gutem Ergebnis bestätigen.
- [ ] Erzeugten Nachweis `kubuntu_26_04_wayland.json` auf Kandidat und Manifest-Hash prüfen.

### 2. Realer Langzeitrender

- [ ] Vertrag aus `docs/LONG_RENDER_2.8.3-rc24.md` mit großer Medienauswahl ausführen.
- [ ] Langsames externes USB-Ziel verwenden.
- [ ] Checkpoint/Wiederaufnahme, Ein-/Ausgabeintegrität und vollständige Hashprüfung real bestehen.
- [ ] Erzeugten Nachweis `long_render.json` auf denselben Kandidaten und Manifest-Hash prüfen.

## Stable-Finalisierung – erst nach beiden P0-Gates

- [ ] Beide realen Nachweise gemeinsam mit `scripts/validate_stable_acceptance.py` prüfen.
- [ ] CI und Release-/Manifest-Vertrag auf demselben Kandidaten erneut vollständig grün bestätigen.
- [ ] Erst danach den Stable-Kanal in einem getrennten, reproduzierbaren Schritt freigeben.

## Repository-Schutz und Ordnung

- [x] `main` ist durch das aktive Ruleset **„Design manifest contract“** geschützt.
- [x] **Design manifest contract** und **Release contract sync** sind verpflichtende GitHub-Actions-Prüfungen.
- [x] Externe GitHub Actions sind durch einen SHA-Pinning-Vertrag gegen bewegliche Tags/Branches geschützt.
- [x] Reine technische Referenzdokumente sind unter `docs/reference/` gebündelt; Start-, Release- und Vertragsdateien bleiben im Hauptverzeichnis.
- [ ] Weitere schwere CI-Gates nur separat und risikobasiert als Pflichtchecks bewerten; Qt6-/Wayland- und Langzeitrender-Gates nicht beiläufig hochstufen.

## Danach – Qt-Migration abschließen

Diese Arbeiten bleiben bis zur realen Zielsystemabnahme zurückgestellt:

- [ ] Entscheiden, ob der kanonische Startpfad vollständig auf Qt Phase 3 umgeschaltet werden kann.
- [ ] Verbleibende Tk-/Legacy-UI-Pfade auf tatsächliche Restverwendung prüfen.
- [ ] Nicht mehr benötigte Legacy-Teile separat und mit Regressionstest entfernen.
- [ ] Projekt-, Diagnose-, Vorschau- und Diashow-Funktionen auf dem realen Zielsystem vollständig durchlaufen.

## Wartbarkeit

- [ ] Neue rein interne historische Nachweise unter `docs/archive/` ablegen; freigegebene Release-Unterlagen im Hauptverzeichnis nicht nachträglich verschieben.
- [ ] Keine parallele CI-Matrix einführen, solange der Einzielvertrag Kubuntu 26.04 / Wayland gilt.
- [ ] Nach Plattformänderungen `PLATFORM_SUPPORT.json`, Stable-Abnahmevertrag, Nutzeranleitungen und CI gemeinsam gegen Drift prüfen.
- [ ] Pro Entwicklungsiteration höchstens **zwei Umsetzungsschritte**, danach Kurzabnahme und vollständiges Gate.

## Abschlussregel

Automatisierte CI und headless Weston sind notwendige technische Nachweise, aber kein Ersatz für die physische Kubuntu-26.04-Plasma-Wayland-Abnahme. **Stable bleibt gesperrt, bis beide realen P0-Nachweise gültig vorliegen.**
