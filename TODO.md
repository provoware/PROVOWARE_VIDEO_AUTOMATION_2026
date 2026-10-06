# TODO – Stable-Finalisierung 2.8.3-rc24

## Fokus

**Zielplattform:** Kubuntu 26.04 LTS · KDE Plasma · natives Wayland · PySide6/Qt 6.

Der automatisierte Repository-, Release-, Qt6- und Qualitätsstand ist grün. **Langzeitrender und die Kubuntu-Basisabnahme vom 29.09.2026 sind dokumentiert. Nach den späteren UI-/Skalierungsänderungen ist die physische UI-Freigabe jedoch erneut offen.**

## P0 – jetzt

### 1. Kubuntu-/Wayland-Sichtabnahme — OFFEN

- [x] Basisabnahme vom 29.09.2026 unter `diagnostics/release_readiness/KUBUNTU_OPERATOR_ACCEPTANCE_2026-09-29.json` erhalten.
- [x] Automatisierte Qt-/Wayland- und Repository-Gates für den neuen UI-Stand grün.
- [ ] Geänderten UI-/Skalierungsstand aus PR #228 real auf Kubuntu 26.04 · KDE Plasma · Wayland prüfen.
- [ ] Dabei 100 %, 150 % und 200 % kontrollieren: Clipping, Fokus, Lesbarkeit, Tabellenzeilen, Statusanzeigen und Listen-Zoom.
- [ ] Erst nach dieser Sichtabnahme `physical_kubuntu_26_04_wayland` wieder auf `passed` setzen.

### 2. Realer Langzeitrender — GRÜN

- [x] Ausgeführten Langzeitrender durch den Projektverantwortlichen als in Ordnung bestätigt.
- [x] Kanonisches Gate `large_media_soak` auf `passed` gesetzt.
- [x] Manuelle Provenienz unter `diagnostics/release_readiness/LONG_RENDER_OPERATOR_ACCEPTANCE_2026-09-29.json` dokumentiert.
- [x] Keine nicht vorliegenden Einzelmesswerte, Hashwerte oder Prüfschritte werden nachträglich erfunden.

## Stable-Finalisierung – ein reales UI-Gate offen

- [x] Expliziten Operator-Freigabevertrag als fail-closed Alternative zum klassischen Nachweispfad implementieren; keine Messwerte werden rekonstruiert.
- [ ] PR #228 und den darauf aufgebauten Release-Bereinigungs-PR vollständig grün halten.
- [ ] Reale 100/150/200-%-Sichtabnahme dokumentieren und Release-Evidence erneut ableiten.
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

**Der Langzeitrender bleibt fachlich grün; die physische UI-Sichtabnahme ist wegen der späteren UI-/Skalierungsänderungen erneut offen.** Stable darf erst nach dieser erneuten Abnahme promotet werden. Vorhandene Evidenz wird nicht rückwirkend umgedeutet oder künstlich aktualisiert.
