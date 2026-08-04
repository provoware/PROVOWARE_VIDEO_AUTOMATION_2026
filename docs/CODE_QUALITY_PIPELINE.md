# Verbindliche Codequalitätsstrecke

## In jedem `test.sh`

- isolierte Python-Kompilierung
- Registry- und Architekturprüfung
- interner AST-Sicherheitscheck
- Komplexitäts- und Dateigrößenlimit
- pytest-cov mit Mindestabdeckung
- Anwendungssimulation
- GUI-Roundtrip
- isolierte visuelle Regression
- Release-Manifest vor und nach der Prüfung

## In `quality.sh` zusätzlich zwingend

- Ruff 0.16.1
- MyPy 2.3.0
- Bandit 1.9.4
- pip-audit 2.10.1

Die Versionen stehen exakt in `requirements-quality.lock`. Fehlt ein Werkzeug, scheitert `quality.sh` sichtbar.
