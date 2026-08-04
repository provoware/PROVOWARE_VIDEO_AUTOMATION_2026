# Einheitliche Vorbereitung

## Alles vorbereiten

```bash
./setup.sh
```

Der Ablauf prüft Python, `venv`, Tk, FFmpeg und FFprobe. Danach werden die exakt
gesperrten Laufzeit- und Qualitätsabhängigkeiten vorbereitet. Jeder notwendige
Onlinezugriff wird separat bestätigt.

## Nur Programmstart reparieren

```bash
./setup.sh --runtime
```

## Nur Releasewerkzeuge vorbereiten

```bash
./setup.sh --quality
```

## Status ohne Änderung prüfen

```bash
./setup.sh --check
```

## Prüfarten

- `./test.sh --core`: Funktions- und Regressionstests, nicht releasefreigebend
- `./verify_release.sh`: vollständige Releaseprüfung mit allen vier Werkzeugen
- `./stable_release.sh`: nur nach expliziter Stable-Promotion zulässig
