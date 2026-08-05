# Code- und Releasequalität – 2.8.3-rc5

## Verifizierter Stand

- 156/156 automatisierte Tests bestanden
- 80,43 Prozent Zeilenabdeckung bei verbindlichem 80-Prozent-Gate
- 12/12 Anwendungssimulationen bestanden
- 16/16 visuelle Referenzszenarien bestanden
- GUI-Rasterprofil-Roundtrip bestanden
- Architektur-, Registry- und interne Qualitätsbefunde: 0
- maximale Funktionskomplexität: 28 bei Grenze 30
- größte Quelldatei: 584 bei Grenze 700 Zeilen

## RC5-Schwerpunkt

RC5 schließt den Installations- und Bedienvertrag zwischen Programmstart und Releaseprüfung. Laufzeitabhängigkeiten und Qualitätswerkzeuge besitzen getrennte, buildgebundene Verträge, atomare Wheelhouses und offline hashgebundene Installation. `setup.sh` ist der gemeinsame Einstieg.

## Noch nicht grün belegbar

Der Buildhost besitzt keinen Zugriff auf die erforderlichen PyPI-Wheels. Deshalb sind Ruff 0.16.1, MyPy 2.3.0, Bandit 1.9.4 und pip-audit 2.10.1 fest integriert, aber auf diesem Host nicht als ausgeführt bestanden markiert.
