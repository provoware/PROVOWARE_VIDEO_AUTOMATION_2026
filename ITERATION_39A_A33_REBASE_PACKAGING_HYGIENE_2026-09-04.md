# Iteration 39A · A33-Lineage-Rebase & Packaging-Hygiene

Datum: 2026-09-04  
Produkt: PROVOWARE VideoBatch Fast  
Produktversion: 2.8.3-rc24  
Status der Iteration: technisch abgeschlossen; Stable weiterhin blockiert

## Ziel

A33 auf den kanonischen A32.2-Head rebasen und anschließend Paketierung, Werkzeugkette, Regression, Coverage, Architektur, Manifest und finalen Integrations-Diff auf einem gemeinsamen Entwicklungsstand prüfen.

## Lineage

- kanonische A32.2-Basis: `8755d5333b2f53ff8080655f8af39727db9b8c48`
- ursprünglicher A33-Head: `71db290cbe5ffd0bfdf76c06f1de5b00dc6318b8`
- A33 vor Rebase: 18 Commits voraus, 1 Commit hinter der kanonischen Basis
- mechanischer Rebase: PR #100, Rebase-Merge ausschließlich in die 39A-Arbeitsbranch
- Ergebnis nach Rebase: Merge-Base exakt `8755d533...`, 0 Commits hinter
- Integrations-Child-PR: Draft PR #101 gegen `codex/a32-2-current-state-error-hardening`
- `main` wurde nicht verändert
- PR #84 wurde nicht nach `main` gemergt
- PR #101 wurde nicht gemergt

## Finaler Diff-Audit

Der vollständige PR-101-Dateiaudit fand sechs redundante Rollback-Kopien unter `Backup/A32.2_vor_A33/`. Diese waren bereits vom Release-Paket ausgeschlossen, gehörten aber nicht in eine saubere Integrations-Lineage. Sie wurden vollständig aus dem Branch entfernt.

Rückrollbarkeit erfolgt jetzt ausschließlich über:

1. Git-Historie,
2. dokumentierte kanonische Basis-SHA,
3. bestehende qualifizierte Release-/Evidence-Artefakte.

Der zentrale `Backup/`-Ausschluss bleibt defensiv bestehen, damit versehentlich neu erzeugte Sicherungskopien nicht paketiert werden.

## Packaging-Hygiene

Der gemeinsame Release-Dateivertrag schließt insbesondere aus:

- `Backup/`
- `__pycache__/`
- `.pytest_cache/`
- `.mypy_cache/`
- `.ruff_cache/`
- `*.pyc` und `*.pyo`
- Coverage-Zwischendateien
- bestehende Build-, Diagnose- und Archivpfade

Der A33-Paketworkflow verwendet den manifestgeführten deterministischen Packager `scripts/package_release.py` plus `scripts/verify_release_zip.py`. Im validierten CI-Lauf wurde das ZIP zweimal unabhängig erzeugt und byteweise verglichen. Der explizite Paket-Hygienescanner meldete keine Backups, Caches oder Bytecode-Dateien.

## Werkzeugkette

Direkt verifiziert aus `requirements-toolchain.lock`:

- Coverage 7.13.3
- Pytest 9.0.2
- pytest-cov 7.0.0
- Ruff 0.16.1
- MyPy 2.3.0
- Bandit 1.9.4
- pip-audit 2.10.1

Transitive Python-Abhängigkeiten werden weiterhin durch den Resolver aufgelöst; ein vollständiger Hash-Lock des gesamten transitiven Graphen wird nicht fälschlich behauptet.

## Regression nach finalem Backup-Cleanup

Referenzlauf: GitHub Actions Run `33831208494` auf Commit `12bfad1e92c6d6bb9992279302d2f1029c7f5848`.

- Fokusregression: 47/47 bestanden
- Vollregression: 477 bestanden
- übersprungen: 2
- fehlgeschlagen: 0
- Coverage-instrumentierte Vollregression: 477 bestanden / 2 übersprungen
- Startvertrag: PASS
- Kompilierung: PASS
- Architektur-Audit: PASS
- Manifest-Prüfung: PASS
- deterministischer Paketbau: PASS
- Artefakt-Upload: PASS

## Coverage

Die Release-Governance bleibt unverändert und wird separat mit `scripts/coverage_policy.py coverage.json 80 65` erzwungen.

Gemessen:

- Zeilenabdeckung: **73,16 %** / Mindestwert 80,00 % → FAIL
- Branch-Abdeckung: **58,82 %** / Mindestwert 65,00 % → FAIL
- kombinierte Darstellung: 70,32 %

Die Schwellen wurden nicht abgesenkt. Der Workflow endet deshalb absichtlich ausschließlich am letzten Coverage-Gate rot.

Große Testlücken liegen weiterhin insbesondere in Tk-/Shell-nahen UI-Modulen sowie in `long_render_target.py`. Diese Trennung ist ein Eingangskriterium für Iteration 39B.

## Architektur

- Module: 115
- Funktionen: 1.139
- Klassen: 140
- größte Python-Datei: `ui_workspace_grid_mixin.py` mit 699 Zeilen
- Architektur-Befunde: 0
- harte Projektregel unter 1.000 Zeilen pro Python-Datei: eingehalten

## Manifest und Paket

Der bereinigte Referenzlauf bestätigte:

- Release-Manifest-Prüfung: PASS
- kanonischer Dateisatz: 450 Nutzdateien
- Release-ZIP-Verifikation: PASS
- deterministischer Zweitbau: PASS
- Paket-Hygiene: PASS
- inneres Projekt-ZIP SHA-256: `349224aeab5451bf3bad63a5228aa75f6bcc06f0cbce16d561cd21105629f04a`

Nach dieser letzten Dokumentationsänderung wird das kanonische Manifest noch einmal auf den endgültigen 39A-Head synchronisiert und anschließend der PR-Scope erneut geprüft.

## Stable-Status

Stable bleibt ausdrücklich blockiert durch:

1. Coverage-Vertrag 80/65
2. physische Kubuntu/KDE-Abnahme unter realem X11 und Wayland
3. Large-Media-/Long-Render-Soak auf langsamem externem Ziel

Iteration 39A schließt keinen dieser drei Stable-Gates künstlich.

## Nächster fachlicher Schritt

Iteration 39B erstellt eine testbasierte Transfermatrix: direkt wiederverwendbarer Core/Startup/Fault-Hardening, adapterpflichtige Mischlogik und bewusst nicht zu portierende Tk-spezifische UI. Erst danach werden Komponenten für PySide6/QML freigegeben.
