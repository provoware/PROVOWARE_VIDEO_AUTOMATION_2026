# Offline-Qualitätsumgebung

## Ziel

Ruff, MyPy, Bandit, pip-audit, pytest-cov und alle transitiven Abhängigkeiten werden einmalig als vollständiges Wheelhouse erzeugt, hashgebunden und danach ohne Netzwerk installiert.

## Vertrauenskette

1. Exakte Versionen stehen in `requirements-quality.lock`.
2. Der Builder akzeptiert ausschließlich Wheels.
3. Download erfolgt zuerst in ein neues Staging-Verzeichnis.
4. Jedes Wheel wird über seine interne METADATA identifiziert.
5. Dateiname, Distribution, Version, Größe und SHA-256 werden manifestiert.
6. Erst ein vollständiges geprüftes Staging ersetzt atomar den bisherigen Bestand.
7. Ein Downloadfehler lässt ein vorhandenes geprüftes Wheelhouse unverändert.
8. Der Installer prüft das Manifest vor dem Erzeugen der virtuellen Umgebung.
9. Installation erfolgt mit `--no-index --find-links`.
10. `pip check` und die exakte Werkzeugversionsprüfung müssen bestehen.

## Aufbau auf einem vernetzten Buildsystem

```bash
./quality-toolchain.sh prepare
./quality.sh
```

Das Buildsystem muss zu Zielplattform, Maschinenarchitektur und Python-Hauptversion passen. Der Builder schreibt diese Identität in `QUALITY_WHEELHOUSE_MANIFEST.json`.

## Offline-Übertragung

Der komplette Ordner `quality_wheelhouse/` wird gemeinsam mit seinem Manifest auf ein Offline-Medium kopiert. Vor jeder Installation muss erneut geprüft werden:

```bash
./quality-toolchain.sh verify
```

## Fail-closed

Fehlende Wheels, zusätzliche Wheels, geänderte Hashwerte, doppelte Distributionen, falsche Versionen, ein fehlendes Manifest oder ein Installationskonflikt blockieren die Umgebung.

## Aktueller RC-Status

In der vorliegenden Buildumgebung bot das konfigurierte Paketgateway die gesperrten Qualitätsdistributionen nicht an. Die Umgebung wurde daher nicht künstlich oder unvollständig erzeugt. Der strenge Lauf bleibt offen.
