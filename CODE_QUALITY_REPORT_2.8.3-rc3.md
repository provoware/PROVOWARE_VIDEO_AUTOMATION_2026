# Code- und Releasequalität – 2.8.3-rc3

| Prüfung | Ergebnis |
|---|---:|
| Python-Tests | 139/139 bestanden |
| Coverage | 74,43 % |
| Anwendungssimulationen | 12/12 |
| visuelle Regression | 16/16 |
| GUI-Rasterprofil-Roundtrip | bestanden |
| Registrybefunde | 0 |
| Architekturbefunde | 0 |
| interne Qualitätsbefunde | 0 |
| maximale Komplexität | 28/30 |
| größte Quelldatei | 584/700 Zeilen |

## Behobener RC2-Fehler

`quality-toolchain.sh prepare` konnte nach der Zustimmung zum Download mit `FileNotFoundError` abbrechen, wenn `scripts/verify_quality_wheelhouse.py` im entpackten Bestand fehlte. RC3 verwendet stattdessen die zentrale Prüffunktion aus `quality_wheelhouse_common.py`. Installer und Orchestrator besitzen dadurch keine Laufzeitabhängigkeit mehr vom separaten CLI-Skript.

## Externe Pflichtgates

| Werkzeug | Fest gebundene Version | Status in dieser Buildumgebung |
|---|---:|---:|
| Ruff | 0.16.1 | blockiert – Wheel fehlt |
| MyPy | 2.3.0 | blockiert – Wheel fehlt |
| Bandit | 1.9.4 | blockiert – Wheel fehlt |
| pip-audit | 2.10.1 | blockiert – Wheel fehlt |

Die isolierte Buildumgebung besitzt keine funktionierende DNS-Auflösung zu PyPI. Der reale `prepare --allow-online`-Pfad wurde bis zum kontrollierten Downloadfehler geprüft; der frühere Dateifehler tritt nicht mehr auf.
