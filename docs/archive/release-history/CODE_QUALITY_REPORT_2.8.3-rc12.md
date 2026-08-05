# Codequalitätsbericht 2.8.3-rc13

## Automatisierte Ergebnisse

| Gate | Ergebnis |
|---|---:|
| Python-Tests | 198/198 bestanden |
| Zeilenabdeckung | 81,84 % |
| Branch-Abdeckung | 66,91 % |
| interne Qualitätsbefunde | 0 |
| maximale Komplexität | 28/30 |
| Textressourcenvertrag | bestanden |
| Versionsvertrag | bestanden |
| Fehlerlabor | 12/12 bestanden |
| Anwendungssimulation | 12/12 bestanden |
| visuelle Regression | 16/16 bestanden |
| portable Manifestprüfung | bestanden |
| portable Runtime-Smokeprüfung | bestanden |
| portable UI-Bereitschaft | bestanden |

## Externe Qualitätswerkzeuge

Ruff 0.16.1, MyPy 2.3.0, Bandit 1.9.4 und pip-audit 2.10.1 sind exakt gebunden und für Stable verpflichtend. In der isolierten Buildumgebung waren ihre Wheels nicht vorhanden; diese vier Gates werden daher nicht als ausgeführt behauptet.

- byteidentische portable Doppelpaketierung: bestanden
