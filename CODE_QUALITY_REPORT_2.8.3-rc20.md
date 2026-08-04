# Code-Qualitätsbericht 2.8.3-rc20

## Geprüfter Stand

- 245/245 Python-Tests bestanden
- 78,59 % vollständige Paketabdeckung inklusive GUI-Module
- Branch-Coverage ist in der Gesamtmessung enthalten
- 16/16 visuelle Szenarien bestanden
- 0 Registrybefunde
- 0 Architekturbefunde
- 0 interne Qualitätsbefunde
- maximale Komplexität 28
- größte Python-Datei: ui.py mit 694 Zeilen

## Neue Pflichtregressionen

- Drag-and-drop-Reihenfolge mit geschütztem Start- und Abschlussbild
- reproduzierbare Zufallsreihenfolge
- EXIF-Aufnahmedatum mit sicherem Dateidatum-Fallback
- lokale Wellenformanalyse und persistent validierter Cache
- Szenenmarken für Intro, Beat-Einsatz, ruhige Phase, Drop und Outro
- Szenenkopplung mit exakter Audiodauer
- sehr kurze Audios mit vielen Bildern erzeugen strikt monotone Grenzen
- Thumbnail- und Wellenform-GUI unter Xvfb
- vollständiger Textressourcenvertrag auch für den Diashoweditor
- ungültige Projekt-Sortierzustände werden normalisiert

## Externe Werkzeuge

Ruff 0.16.1, MyPy 2.3.0, Bandit 1.9.4 und pip-audit 2.10.1 bleiben fest gebunden. Der reale Lauf konnte in dieser Buildumgebung nicht ausgeführt werden, weil das isolierte Paketgateway keine passende Distribution bereitstellte. Dieser Punkt bleibt offen und wird nicht als bestanden dargestellt.
