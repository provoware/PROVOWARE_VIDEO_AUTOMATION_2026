# Fest integrierte Qualitätswerkzeuge – 2.8.3-rc3

## Verbindlicher Vertrag

Diese Ausgabe bindet folgende Versionen unveränderlich an den Releaseprozess:

- Ruff 0.16.1
- MyPy 2.3.0
- Bandit 1.9.4
- pip-audit 2.10.1

Die zentrale Wahrheit ist `QUALITY_TOOLCHAIN_CONTRACT.json`. Abweichende, fehlende oder doppelte Lockfile-Einträge blockieren die Prüfung.

## Einmalige Vorbereitung

```bash
./quality-toolchain.sh prepare
```

Ist noch kein Offline-Wheelhouse vorhanden, fragt das Skript interaktiv, ob die exakt gesperrten Binärpakete von PyPI geladen werden dürfen. Ohne ausdrückliche Zustimmung findet kein Netzwerkzugriff statt.

Nichtinteraktive, bewusste Freigabe:

```bash
./quality-toolchain.sh prepare --allow-online
```

Danach werden alle Pakete ausschließlich aus `quality_wheelhouse/` in `.quality-venv/` installiert. Das Wheelhouse wird über Dateigröße, SHA-256 und Paketidentität geprüft.

## Release-Gates

```bash
./quality.sh
./test.sh
```

Beide Pfade verlangen ein gültiges Wheelhouse, die exakten installierten Versionen und grüne Ergebnisse aller vier Werkzeuge. Fehlende Werkzeuge werden nicht übersprungen.

`stable_release.sh` erzeugt nur dann ein Stable-ZIP, wenn zusätzlich `VERSION.json` ausdrücklich den Kanal `stable` trägt und die vollständige Releaseprüfung grün ist.

## Fehlercodes

- 20: Qualitätsvertrag oder Lockfile ungültig
- 21: Wheelhouse fehlt oder ist ungültig
- 22: Offlineinstallation fehlgeschlagen
- 24: externes Qualitätsgate blockiert
