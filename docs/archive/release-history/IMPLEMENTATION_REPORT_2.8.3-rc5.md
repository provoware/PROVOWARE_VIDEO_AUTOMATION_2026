# Implementierungsbericht 2.8.3-rc5

## Anlass

Die reale Kubuntu-Prüfung von RC4 zeigte zwei Bedienblocker: `test.sh` und
`verify_release.sh` blockierten ohne vorbereitete Qualitätsumgebung, während
`start.sh` bei fehlendem `cryptography` lediglich auf einen separaten
Reparaturbefehl verwies. Das Stable-Gate blockierte korrekt, erklärte den
Releasekandidaten-Status jedoch nicht ausreichend.

## Umsetzung

- zentraler Runtime-Vertrag für `cryptography 46.0.4`, `Pillow 12.2.0`,
  `cffi 2.0.0` und `pycparser 3.0`
- atomar aufgebautes Runtime-Wheelhouse mit SHA-256-Manifest
- vollständig hashgebundene Offlineinstallation in `.venv`
- einheitlicher Einstieg über `setup.sh`
- automatische, ausdrücklich bestätigte Selbstreparatur beim Programmstart
- verständliche Vorbereitungshinweise in `test.sh` und `quality.sh`
- klar gekennzeichnete Kernprüfung über `./test.sh --core`
- Release- und Stable-Gates bleiben fail-closed
- Runtime- und Qualitätsverträge sind an dieselbe Buildidentität gebunden

## Sicherheitswirkung

Onlinezugriff erfolgt nur nach ausdrücklicher Zustimmung. Nach dem Download
werden Laufzeit- und Qualitätsabhängigkeiten ausschließlich aus lokal geprüften
Wheelhouses installiert. Vorhandene gültige Umgebungen werden atomar ersetzt;
bei Fehlern bleibt der vorige Bestand erhalten.
