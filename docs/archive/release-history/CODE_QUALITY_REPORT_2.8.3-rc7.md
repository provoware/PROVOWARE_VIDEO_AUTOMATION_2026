# Codequalitätsbericht 2.8.3-rc9

| Gate | Ergebnis |
|---|---:|
| Python-Tests | 166/166 bestanden |
| RC7-Härtungstests | 11/11 bestanden |
| Zeilenabdeckung | 80,55 % · 3297/4093 |
| Branch-Abdeckung | 65,84 % · 694/1054 |
| kombinierte Coverage | 77,54 % |
| Anwendungssimulationen | 12/12 |
| visuelle Referenzen | 16/16 |
| GUI-Rasterprofil-Roundtrip | bestanden |
| Textressourcenvertrag | bestanden |
| Versionsvertrag | bestanden |
| Registrybefunde | 0 |
| Architekturbefunde | 0 |
| interne Qualitätsbefunde | 0 |
| maximale Funktionskomplexität | 28/30 |
| größte Quelldatei | 588/700 Zeilen |

## Neu verbindlich

- Branch-Coverage ist aktiviert.
- Qualitätsgate verlangt mindestens 80 % Zeilen- und 65 % Branch-Abdeckung.
- statische sichtbare UI-Texte müssen ausgelagert sein.
- dauerhafte Zustandsänderungen verwenden zentrale atomare Schreibpfade.
- Wiederherstellung, Einzelinstanzschutz und kontrolliertes Thread-Shutdown sind als Architekturverträge dokumentiert.

## Externe Gates

Ruff 0.16.1, MyPy 2.3.0, Bandit 1.9.4 und pip-audit 2.10.1 sind exakt gebunden. Ihre reale Ausführung ist auf diesem Buildhost wegen fehlender DNS-Verbindung nicht möglich und wird nicht als bestanden ausgegeben.
