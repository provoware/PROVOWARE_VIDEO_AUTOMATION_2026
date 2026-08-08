# Welle 18 – Real Stable-Gate Execution & Promotion Rehearsal

## Ergebnis

Welle 18 schließt die noch offenen physischen/externalen Stable-Gates **nicht künstlich**. Sie macht deren reale Ausführung auf geeigneter Hardware reproduzierbar, fortsetzbar und strikt an denselben unveränderten Release Candidate gebunden.

## Wesentliche Befunde und Korrekturen

1. Der bisherige `stable_release.sh`-Pfad verlangte Quality-Evidence mit `offline=true`, während `toolchain.py gate --run-external` den externen Runner ohne `--offline` startete. Dieser interne Vertragsbruch wurde beseitigt; der freigaberelevante externe Qualitätslauf wird nun mit Netzwerksperre ausgeführt.
2. `pip-audit` benötigt zusätzlich aktuelle Vulnerability-Daten. Welle 18 trennt deshalb eingefrorene Tool-Binaries vom Advisory-Datensatz: dedizierter `pip-audit`-HTTP-Cache wird nach dem Wheelhouse online vorbereitet und gehasht; der finale Gate-Lauf erfolgt danach offline gegen diesen Cache.
3. Eine persistente Operator-Sitzung bindet jede Phase an `candidate_id`, `manifest_sha256` und `source_sha256`. Nach Quell-/Manifeständerung ist die Sitzung stale und wird blockiert.
4. Bereits aufgezeichnete Evidence-Artefakte werden bei jedem Session-Load erneut auf Existenz, Größe und SHA-256 geprüft. Manipulierte Evidence kann keine Folgephase freischalten.
5. Für das Zielsystem wird ausschließlich eine reale KDE-X11-Sitzung verlangt; Wayland ist kein Stable-Gate. Xvfb/CI kann keine physische Evidence exportieren.
6. Pro Desktop-Sitzung werden Summary-Evidence, Raw-Desktop-Report und Screenshot separat konserviert.
7. Der Langzeitrender bindet `long_render.json`, den unveränderten Vertragsdatensatz und den vollständigen `final-report.json`.
8. Die Promotion-Rehearsal akzeptiert ausschließlich source-/manifestgebundene Quality- und Physical-Evidence, erzeugt temporär eine Stable-Arbeitskopie und verlangt zwei byteidentische Stable-Pakete. Sie veröffentlicht bewusst kein Stable-Artefakt.
9. Das portable Operator-Kit enthält den manifestierten Kandidaten, Candidate Identity, Dokumentation und einen einzigen sicheren Einstiegspunkt `RUN_OPERATOR.sh`.

## Feste Operator-Reihenfolge

`toolchain → quality → desktop_x11 → long_render → promotion_rehearsal`

## Aktueller Nachweisstand

- Finale Welle-18-Regression: 600/600 Tests bestanden.
- Coverage des Anwendungskerns: 81,93 % Lines / 66,43 % Branches / 78,78 % kombiniert; Vertrag 80/65 bestanden.
- Interne Codequalität: 0 Befunde; maximale Komplexität 29.
- Architektur: 0 Befunde.
- Ereignisarchitektur/-register: 0 Befunde.
- Reale externe Toolchain-/KDE-/Soak-Evidence auf diesem Host: nicht behauptet.

## Offene Stable-Gates

Die sechs kanonischen externen/physischen Stable-Gates bleiben offen, bis das Operator-Kit auf geeigneter Hardware vollständig durchlaufen wurde:

- Ruff 0.16.1
- MyPy 2.3.0
- Bandit 1.9.4
- pip-audit 2.10.1
- physische KDE-X11-Abnahme
- realer 96-Job-Large-Media-/Slow-Target-Soak
