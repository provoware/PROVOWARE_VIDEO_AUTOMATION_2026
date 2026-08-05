# Rein lesendes Release-Bereitschafts-Dashboard

Dieses Diagnosemodul führt widersprüchliche Freigabeangaben aus mehreren Quellen in einen einzigen fail-closed Status zusammen. Es verändert keine Eingabequelle und benötigt keine Zusatzbibliotheken.

## Eingelesene Quellen

- `RELEASE_MANIFEST.json`
- `DEVELOPMENT_STATUS.json`
- `QUALITY_ENVIRONMENT_STATUS.json`
- `RELEASE_FILE_STATUS.json`
- der in `DEVELOPMENT_STATUS.json` benannte freigegebene Buildbericht
- optional ein normalisierter CI-Snapshot oder der Live-Status eines GitHub-Commits

## Ausgaben

Ausschließlich im gewählten Ausgabeordner:

- `RELEASE_READINESS_STATUS.json`
- `RELEASE_READINESS_DASHBOARD.md`
- `RELEASE_READINESS_DASHBOARD.html`

Standardziel: `build/release-readiness/`. Dieser Ordner ist vom Release-Manifest ausgeschlossen.

## Ampellogik

- **GRÜN:** alle Pflicht-Gates PASS, keine Widersprüche, Eingaben unverändert
- **GELB:** keine Fehler, aber offene, laufende oder unbekannte Pflicht-Gates
- **ROT:** widersprüchliche Quellen, fehlgeschlagene CI, ungültiges Manifest, fehlende Release-Dateien oder unterschrittene Abdeckung

Exitcodes: `0 = GRÜN`, `1 = GELB`, `2 = ROT/Eingabefehler`.

## Lokaler Lauf

```bash
python3 diagnostics/release_readiness/release_readiness_dashboard.py \
  --root . \
  --ci-file diagnostics/release_readiness/ci_status.example.json
```

Nur prüfen, ohne Ausgabedateien:

```bash
python3 diagnostics/release_readiness/release_readiness_dashboard.py --root . --no-write
```

## Live-CI von GitHub einlesen

```bash
GITHUB_TOKEN="...read-only token..." \
python3 diagnostics/release_readiness/release_readiness_dashboard.py \
  --root . \
  --github-repository provoware/PROVOWARE_VIDEO_AUTOMATION_2026 \
  --github-sha "$GITHUB_SHA"
```

Benötigte GitHub-Berechtigungen: `contents: read`, `actions: read`, `checks: read`. Das Modul führt ausschließlich GET-Abfragen aus.

## GitHub-Actions-Schritt

```yaml
permissions:
  contents: read
  actions: read
  checks: read

- name: Release-Bereitschaft erzeugen
  env:
    GITHUB_TOKEN: ${{ github.token }}
  run: |
    python3 diagnostics/release_readiness/release_readiness_dashboard.py \
      --root . \
      --github-repository "${GITHUB_REPOSITORY}" \
      --github-sha "${GITHUB_SHA}"
```

Der Schritt ist absichtlich fail-closed: Gelb liefert Exitcode 1, Rot Exitcode 2. Für einen reinen Bericht kann der Aufruf in der Workflow-Shell kontrolliert abgefangen und das Ausgabeverzeichnis anschließend als Artefakt hochgeladen werden.

## Selbsttest

```bash
python3 diagnostics/release_readiness/selftest.py
```

Geprüft werden Rot-, Gelb- und Grünfall, unveränderte Eingabehashes sowie die atomare Erzeugung aller drei Ausgabeformate.

## Sicherheitsgrenzen

- keine Änderungen an Manifest, Statusdateien, Testberichten oder Quellcode
- keine Löschoperationen
- keine Shellausführung aus eingelesenen Daten
- sichere relative Pfade ohne `..`
- atomare Ausgabe über temporäre Dateien und `os.replace`
- HTML vollständig lokal, ohne CDN, JavaScript oder Tracking
- GitHub-Abfrage nur über validierten Repositorynamen und Commit-SHA
