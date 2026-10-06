# TODO – Stable-Finalisierung 2.8.3-rc24

## Fokus

**Zielplattform:** Kubuntu 26.04 LTS · KDE Plasma · natives Wayland · PySide6/Qt 6.

Der Langzeitrender und die frühere Kubuntu-Basisabnahme sind dokumentiert. **Die reale Prüfung bei 125 % am 06.10.2026 hat jedoch einen echten Layoutfehler sichtbar gemacht: zu viele Hauptbereiche waren gleichzeitig eingeblendet. Dieser Befund wird mit getrennten Arbeitsseiten behoben und muss danach neu abgenommen werden.**

## P0 – jetzt

### 1. Kubuntu-/Wayland-Sichtabnahme — OFFEN

- [x] Basisabnahme vom 29.09.2026 unter `diagnostics/release_readiness/KUBUNTU_OPERATOR_ACCEPTANCE_2026-09-29.json` erhalten.
- [x] Realen 125-%-Befund vom 06.10.2026 dokumentiert: abgeschnittene Texte, zu flache Listen und unnötiges Hauptbereich-Scrollen.
- [x] Hauptablauf in eigene Seiten für Dateien, Ausgabe und Produktion getrennt; Projekt/Hilfe/Diagnose verdrängen den Arbeitsbereich nicht mehr.
- [ ] PR #230 vollständig durch Repository-, Release-, Qt- und Wayland-Gates bringen.
- [ ] Korrigierten Stand real bei 100 %, 125 %, 150 % und 200 % prüfen: kein Clipping, keine Überlagerung, alle Hauptschalter sichtbar, Fokus sichtbar, Listen ausreichend hoch, keine Hauptseiten-Scrollleiste.
- [ ] Sortierung prüfen: reine Ansichtssortierung darf die Produktionspaarung nicht ändern; Übernahme nur nach ausdrücklichem Klick.
- [ ] Erst nach dieser Sichtabnahme `physical_kubuntu_26_04_wayland` wieder auf `passed` setzen.

### 2. Realer Langzeitrender — GRÜN

- [x] Ausgeführten Langzeitrender durch den Projektverantwortlichen als in Ordnung bestätigt.
- [x] Kanonisches Gate `large_media_soak` auf `passed` gesetzt.
- [x] Manuelle Provenienz unter `diagnostics/release_readiness/LONG_RENDER_OPERATOR_ACCEPTANCE_2026-09-29.json` dokumentiert.
- [x] Keine nicht vorliegenden Einzelmesswerte, Hashwerte oder Prüfschritte werden nachträglich erfunden.

## Stable-Finalisierung – ein reales UI-Gate offen

- [x] Expliziten Operator-Freigabevertrag als fail-closed Alternative zum klassischen Nachweispfad implementieren; keine Messwerte werden rekonstruiert.
- [ ] PR #230 auf dem finalen unveränderten Head vollständig grün bestätigen.
- [ ] Reale 100/125/150/200-%-Sichtabnahme dokumentieren und Release-Evidence erneut ableiten.
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

**Der Langzeitrender bleibt fachlich grün; die physische UI-Sichtabnahme ist nach dem realen 125-%-Befund und der daraus folgenden Layoutkorrektur offen.** Stable darf erst nach der neuen 100/125/150/200-%-Abnahme promotet werden. Vorhandene Evidenz wird nicht rückwirkend umgedeutet oder künstlich aktualisiert.
