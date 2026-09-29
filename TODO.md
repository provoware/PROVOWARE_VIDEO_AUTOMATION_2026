# TODO – Stable-Finalisierung 2.8.3-rc24

## Fokus

**Zielplattform:** Kubuntu 26.04 LTS · KDE Plasma · natives Wayland · PySide6/Qt 6.

Der automatisierte Repository-, Release-, Qt6- und Qualitätsstand ist grün. **Kubuntu-Basisabnahme und Langzeitrender wurden am 29.09.2026 vom Projektverantwortlichen als in Ordnung bestätigt. Beide fachlichen P0-Gates sind grün.**

## P0 – jetzt

### 1. Kubuntu-Basisabnahme — GRÜN

- [x] Vorhandenen Kubuntu-/Wayland-Basiszustand durch den Projektverantwortlichen als in Ordnung akzeptiert.
- [x] Kanonisches Gate `physical_kubuntu_26_04_wayland` auf `passed` gesetzt.
- [x] Manuelle Provenienz unter `diagnostics/release_readiness/KUBUNTU_OPERATOR_ACCEPTANCE_2026-09-29.json` dokumentiert.
- [x] Kein neu ausgeführter physischer Kubuntu-26.04-Lauf und keine nicht vorhandenen Messdaten werden behauptet.

### 2. Realer Langzeitrender — GRÜN

- [x] Ausgeführten Langzeitrender durch den Projektverantwortlichen als in Ordnung bestätigt.
- [x] Kanonisches Gate `large_media_soak` auf `passed` gesetzt.
- [x] Manuelle Provenienz unter `diagnostics/release_readiness/LONG_RENDER_OPERATOR_ACCEPTANCE_2026-09-29.json` dokumentiert.
- [x] Keine nicht vorliegenden Einzelmesswerte, Hashwerte oder Prüfschritte werden nachträglich erfunden.

## Stable-Finalisierung – fachliche P0-Gates abgeschlossen

- [x] Expliziten Operator-Freigabevertrag als fail-closed Alternative zum klassischen Nachweispfad implementieren; keine Messwerte werden rekonstruiert.
- [ ] Release-PR vollständig grün bestätigen.
- [ ] Danach Stable 2.8.3 in getrennter Arbeitskopie erzeugen, deterministisch doppelt paketieren, Stable-Branch/Tag und GitHub-Release veröffentlichen.

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

**Kubuntu-Basisabnahme und Langzeitrender sind fachlich grün.** Die eigentliche Stable-Promotion bleibt ein separater reproduzierbarer Release-Schritt; vorhandene formale Evidenzprüfer werden durch die manuelle Statusfreigabe nicht stillschweigend umgangen.
