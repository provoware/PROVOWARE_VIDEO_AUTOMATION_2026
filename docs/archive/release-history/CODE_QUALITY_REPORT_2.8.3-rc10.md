# Codequalitätsbericht 2.8.3-rc10

## Ergebnis

| Gate | Ergebnis |
|---|---:|
| Python-Tests | 183/183 |
| Zeilenabdeckung | 80,43 % |
| Branch-Abdeckung | 65,99 % |
| Anwendungssimulationen | 12/12 |
| visuelle Szenarien | 16/16 |
| Registryprüfung | bestanden |
| Versionskonsistenz | bestanden |
| isolierte Kompilierung | bestanden |
| Textressourcenvertrag | bestanden |
| Architekturbefunde | 0 |
| interne Qualitätsbefunde | 0 |
| maximale Komplexität | 28/30 |
| größte Python-Datei | 606/700 Zeilen |

## Neue qualitätsrelevante Verträge

- `STARTUP_CONTRACT.json`
- getrennte inhaltsadressierte Laufzeit- und Qualitätsumgebungen
- reales FFmpeg-AAC-Smoke-Gate
- Runtime-Hash-Lockfile zusätzlich zum vollständigen Toolchain-Lockfile
- Start bleibt unabhängig von Releasewerkzeugen
- virtuelle Umgebungen dürfen nach ihrer Erzeugung nicht verschoben werden

## Externe Werkzeuge

Ruff 0.16.1, MyPy 2.3.0, Bandit 1.9.4 und pip-audit 2.10.1 bleiben exakt gebunden und sind für Release und Stable verpflichtend. Sie sind ausdrücklich kein Startkriterium der Anwendung.
