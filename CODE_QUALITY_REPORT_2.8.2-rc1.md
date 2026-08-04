# Codequalitätsbericht – 2.8.2-rc1

## Verbindliche Qualitätsstrecke

Die Releaseprüfung ist in zwei Ebenen getrennt:

1. interne, vollständig offline ausführbare Gates
2. externe, exakt gesperrte Standardwerkzeuge

## Lokal ausgeführte Gates

| Gate | Ergebnis |
|---|---:|
| isolierte Python-Kompilierung | bestanden |
| Registry-Konsistenz | bestanden |
| Architekturprüfung | 0 Befunde |
| interne AST-/Security-Prüfung | 0 Befunde |
| maximale Dateigröße | 653/700 Zeilen |
| maximale Funktionskomplexität | 44/45 |
| pytest | 115 bestanden |
| pytest-cov | 70,25 % |
| Mindestabdeckung | 69 % |
| Anwendungssimulation | 12/12 |
| visuelle Regression | 16/16 |

## Externe Gates

Konfiguriert und in `quality.sh` verpflichtend:

- Ruff
- MyPy
- Bandit
- pip-audit

Der strenge Lauf wurde ausgeführt. Er brach korrekt ab, weil diese vier Werkzeuge in der paketnetzlosen Buildumgebung nicht installiert waren. Es liegt daher kein positives externes Prüfergebnis vor.

## Reproduzierbarkeit

- Runtime- und Qualitätsabhängigkeiten sind exakt versioniert.
- Build-Artefakterzeugung ist von der lesenden Verifikation getrennt.
- Tests laufen mit temporären XDG-, Coverage- und Diagnosepfaden.
- Release-ZIPs werden aus dem Manifest mit festen Zeitstempeln und normalisierten Dateimodi erzeugt.
- Zwei unabhängige Paketierungsläufe müssen byteidentische ZIPs liefern.
- Updatekandidaten werden vor und nach dem Selbsttest bytegenau verglichen.

## Stable-Blocker

Vor einer Stable-Freigabe müssen Ruff, MyPy, Bandit und pip-audit im strengen Modus tatsächlich ausgeführt und ihre Berichte archiviert werden. Zusätzlich bleibt die reale Kubuntu-/KDE-/XFCE-Sichtprüfung für diesen Build offen.
