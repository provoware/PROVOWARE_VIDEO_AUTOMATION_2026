# Fest integrierte Qualitätswerkzeuge – 2.8.3-rc4

Die Werkzeugkette ist exakt auf Ruff 0.16.1, MyPy 2.3.0, Bandit 1.9.4 und pip-audit 2.10.1 festgelegt. `./quality-toolchain.sh prepare` erzeugt nach ausdrücklicher Zustimmung ein laufzeitpassendes Wheelhouse, schreibt SHA-256-Metadaten und installiert anschließend ausschließlich offline mit `--no-index --require-hashes`.

Der Wheelhouse-Vertrag ist an Build, Python-Haupt-/Nebenversion, Implementierung, Betriebssystem und Maschinenarchitektur gebunden. Abweichungen blockieren das Gate.
