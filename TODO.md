# TODO – Stable-Finalisierung 2.8.3-rc24

## Fokus

**Zielplattform:** Kubuntu 26.04 LTS · KDE Plasma · natives Wayland · PySide6/Qt 6.

Der automatisierte Repository-, Release-, Qt6- und Qualitätsstand ist grün. Die Kubuntu-Basisabnahme wurde am **29.09.2026** vom Projektverantwortlichen manuell auf grün gesetzt. Als einziges reales P0-Gate bleibt der Langzeitrender offen.

## P0 – jetzt

### 1. Kubuntu-Basisabnahme — GRÜN

- [x] Vorhandenen Kubuntu-/Wayland-Basiszustand durch den Projektverantwortlichen als in Ordnung akzeptiert.
- [x] Kanonisches Gate `physical_kubuntu_26_04_wayland` auf `passed` gesetzt.
- [x] Manuelle Provenienz unter `diagnostics/release_readiness/KUBUNTU_OPERATOR_ACCEPTANCE_2026-09-29.json` dokumentiert.
- [x] Kein neu ausgeführter physischer Kubuntu-26.04-Lauf und keine nicht vorhandenen Messdaten werden behauptet.

### 2. Realer Langzeitrender

- [ ] Vertrag aus `docs/LONG_RENDER_2.8.3-rc24.md` mit großer Medienauswahl ausführen.
- [ ] Langsames externes USB-Ziel verwenden.
- [ ] Checkpoint/Wiederaufnahme, Ein-/Ausgabeintegrität und vollständige Hashprüfung real bestehen.
- [ ] Erzeugten Nachweis `long_render.json` auf denselben Kandidaten und Manifest-Hash prüfen.

## Stable-Finalisierung – nach dem verbleibenden P0-Gate

- [ ] Langzeitrender-Nachweis prüfen; der bestehende Strict-Validator verlangt zusätzlich weiterhin formale Kubuntu-26.04-Evidenz und bleibt deshalb bewusst fail-closed.
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

Die Kubuntu-Basisabnahme ist durch ausdrückliche manuelle Projektfreigabe grün. **Stable bleibt gesperrt, bis der reale Langzeitrender gültig vorliegt und der finale Stable-Promotionspfad seine formalen Evidenzregeln erfüllt.**
