# Iteration 39A · A33-Lineage-Rebase & Packaging-Hygiene

Datum: 2026-09-04  
Produkt: PROVOWARE VideoBatch Fast  
Produktversion: 2.8.3-rc24  
Status der Iteration: technisch abgeschlossen; Stable weiterhin blockiert

## Ziel

A33 auf den kanonischen A32.2-Head rebasen und anschließend Paketierung, Werkzeugkette, Regression, Coverage, Architektur und Manifest auf einem gemeinsamen Entwicklungsstand prüfen.

## Lineage

- kanonische A32.2-Basis: `8755d5333b2f53ff8080655f8af39727db9b8c48`
- ursprünglicher A33-Head: `71db290cbe5ffd0bfdf76c06f1de5b00dc6318b8`
- A33 vor Rebase: 18 Commits voraus, 1 Commit hinter der kanonischen Basis
- mechanischer Rebase: PR #100, Rebase-Merge ausschließlich in die 39A-Arbeitsbranch
- Ergebnis nach Rebase: 18 Commits voraus, 0 Commits hinter; Merge-Base exakt `8755d533...`
- `main` wurde nicht verändert
- PR #84 wurde nicht nach `main` gemergt

## Packaging-Hygiene

Der gemeinsame Release-Dateivertrag schließt jetzt insbesondere aus:

- `Backup/`
- `__pycache__/`
- `.pytest_cache/`
- `.mypy_cache/`
- `.ruff_cache/`
- `*.pyc` und `*.pyo`
- Coverage-Zwischendateien
- bestehende Build-, Diagnose- und Archivpfade

Der A33-Paketworkflow verwendet nicht mehr `zip -qr` über den Arbeitsbaum, sondern den vorhandenen manifestgeführten deterministischen Packager `scripts/package_release.py` plus `scripts/verify_release_zip.py`.

Im validierten CI-Lauf wurde das ZIP zweimal unabhängig erzeugt und byteweise verglichen. Der explizite Paket-Hygienescanner meldete: keine Backups, Caches oder Bytecode-Dateien.

## Werkzeugkette

Der Workflow installiert die kanonisch festgelegten Werkzeugversionen aus `requirements-toolchain.lock` und prüft sie zur Laufzeit:

- Coverage 7.13.3
- Pytest 9.0.2
- pytest-cov 7.0.0
- Ruff 0.16.1
- MyPy 2.3.0
- Bandit 1.9.4
- pip-audit 2.10.1

Hinweis: Diese Iteration fixiert und verifiziert die kanonischen Werkzeugversionen. Transitive Python-Abhängigkeiten werden weiterhin durch den Resolver aufgelöst; ein vollständiger Hash-Lock des gesamten transitiven Graphen ist ein separater Härtungsschritt und wird hier nicht fälschlich behauptet.

## Regression

Referenzlauf: GitHub Actions Run `33827615114` auf Commit `d787b824688b73de1a96c6cfa2ce7bd276728486`.

- Fokusregression: 47/47 bestanden
- Vollregression: 477 bestanden
- übersprungen: 2
- fehlgeschlagen: 0
- Coverage-instrumentierte Vollregression: ebenfalls 477 bestanden / 2 übersprungen

Ein während 39A gefundener Installer-Testfehler wurde auf eine CI-Umgebungsverschmutzung durch globales `scripts/` im `PYTHONPATH` zurückgeführt. Der Workflow wurde auf `PYTHONPATH=<repo>/src` zurückgeführt und der Isolationsvertrag als Regressionstest fixiert. Produktlogik musste dafür nicht geändert werden.

## Coverage

Der ältere kombinierte Pytest-Fail-Under-Wert wird im Messschritt neutralisiert, damit die Messung vollständig geschrieben wird. Die eigentliche Release-Governance bleibt unverändert und wird separat mit `scripts/coverage_policy.py coverage.json 80 65` erzwungen.

Gemessen:

- Zeilenabdeckung: **73,16 %** / Mindestwert 80,00 % → FAIL
- Branch-Abdeckung: **58,82 %** / Mindestwert 65,00 % → FAIL
- kombinierte Darstellung: 70,32 %

Die Schwellen wurden nicht abgesenkt. Der Coverage-Gate bleibt absichtlich rot.

Auffällige große Testlücken liegen insbesondere in Tk-/Shell-nahen UI-Modulen, darunter `canonical_dashboard_mixin.py`, `canonical_shell_chrome.py`, `canonical_shell_workspace.py`, `canonical_kpi_detail_mixin.py`, `canonical_help_status_mixin.py` sowie in `long_render_target.py`. Das ist für die folgende Core-vs.-Tk-Transferentscheidung relevant, wird aber nicht in diese Hygieneiteration hineingezogen.

## Architektur

- Module: 115
- Funktionen: 1.139
- Klassen: 140
- größte Python-Datei: `ui_workspace_grid_mixin.py` mit 699 Zeilen
- Architektur-Befunde: 0
- harte Projektregel unter 1.000 Zeilen pro Python-Datei: eingehalten

## Manifest und Paket

Im Referenzlauf vor Einfügen dieses Abschlussberichts:

- Release-Manifest: PASS
- Nutzdateien: 449
- unregistrierte Nutzdateien: 0
- Release-ZIP-Verifikation: PASS
- deterministischer Zweitbau: PASS
- Paket-Hygiene: PASS

Nach dieser Dokumentationsänderung muss das Manifest auf dem finalen 39A-Head erneut erzeugt und geprüft werden; erst dieses Ergebnis ist der endgültige 39A-Paketstand.

## Stable-Status

Stable bleibt ausdrücklich blockiert durch:

1. Coverage-Vertrag 80/65
2. physische Kubuntu/KDE-Abnahme unter realem X11 und Wayland
3. Large-Media-/Long-Render-Soak auf langsamem externem Ziel

Iteration 39A schließt keinen dieser drei Stable-Gates künstlich.

## Nächster fachlicher Schritt

Auf Basis der nun sauberen Lineage wird eine Transfermatrix erstellt: wiederverwendbarer Core/Startup/Fault-Hardening versus Tk-spezifische UI. Nur die fachlich unabhängigen und ausreichend testbaren Komponenten sollen anschließend gezielt in die PySide6/QML-Linie übernommen werden.
