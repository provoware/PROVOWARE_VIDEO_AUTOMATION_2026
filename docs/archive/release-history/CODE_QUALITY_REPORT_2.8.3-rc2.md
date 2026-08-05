# Code- und Releasequalität – 2.8.3-rc2

| Prüfung | Ergebnis |
|---|---:|
| Python-Tests | 137/137 bestanden |
| Coverage | 74,43 % |
| Anwendungssimulationen | 12/12 |
| visuelle Regression | 16/16 |
| Registrybefunde | 0 |
| Architekturbefunde | 0 |
| interne Qualitätsbefunde | 0 |
| maximale Komplexität | 28/30 |
| größte Quelldatei | 584/700 Zeilen |

## Externe Pflichtgates

| Werkzeug | Fest gebundene Version | Status in dieser Buildumgebung |
|---|---:|---:|
| Ruff | 0.16.1 | blockiert – Wheel fehlt |
| MyPy | 2.3.0 | blockiert – Wheel fehlt |
| Bandit | 1.9.4 | blockiert – Wheel fehlt |
| pip-audit | 2.10.1 | blockiert – Wheel fehlt |

Die Blockade ist kein stilles Überspringen: Ohne gültiges Wheelhouse und exakte installierte Versionen endet die Releasekette rot.
