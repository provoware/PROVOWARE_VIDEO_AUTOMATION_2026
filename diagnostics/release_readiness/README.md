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

## Verifiziertes Gesamtprojekt-Artefakt

Nach vollständig grünem Preflight, grüner Vierfachmatrix und grünem Abschlussbericht erzeugt der PR-Workflow ein nicht veröffentlichtes Gesamtprojekt-Artefakt. Der Archivjob prüft unmittelbar vor dem Packen erneut:

1. `scripts/build_release_manifest.py --check --json`
2. `diagnostics/release_readiness/generate_from_evidence.py --check`
3. `python3 -m compileall -q -f src scripts diagnostics tests`
4. einen unveränderten Git-Arbeitsbaum
5. die ZIP-Integrität

Das Artefakt enthält:

- das vollständige, mit `git archive` erzeugte Projekt-ZIP
- die SHA-256-Datei des ZIPs
- `VERIFIED_SOURCE_ARTIFACT.json`
- `release-manifest-check.json`
- `ARTIFACT_CONTENTS.json`

`ARTIFACT_CONTENTS.json` dokumentiert für jeden Datei-Eintrag im ZIP den Pfad, die unkomprimierte Größe und den SHA-256-Wert. Verzeichniseinträge werden nicht als Dateien gezählt. Doppelte ZIP-Pfade, beschädigte Einträge und unsortierte oder widersprüchliche Inhaltslisten werden fail-closed abgelehnt.

### Inhaltsliste erzeugen

```bash
python3 scripts/build_artifact_contents.py \
  PROJEKT_verified.zip \
  --commit "$GIT_COMMIT" \
  --output ARTIFACT_CONTENTS.json
```

### Heruntergeladenes ZIP vollständig prüfen

```bash
python3 scripts/build_artifact_contents.py \
  PROJEKT_verified.zip \
  --check ARTIFACT_CONTENTS.json
```

Maschinenlesbarer Driftbericht:

```bash
python3 scripts/build_artifact_contents.py \
  PROJEKT_verified.zip \
  --check ARTIFACT_CONTENTS.json \
  --json
```

Optional kann der erwartete Commit explizit festgelegt werden:

```bash
python3 scripts/build_artifact_contents.py \
  PROJEKT_verified.zip \
  --check ARTIFACT_CONTENTS.json \
  --commit "$EXPECTED_COMMIT"
```

Der Prüfmodus erkennt getrennt:

- `missing`: erwartete Datei fehlt im ZIP
- `unexpected`: zusätzliche Datei ist im ZIP enthalten
- `size_changed`: Dateigröße weicht ab
- `sha256_changed`: Dateiinhalt weicht ab
- `metadata_changed`: Archivname, Commit, Dateizahl oder Gesamtgröße weichen ab

Exitcodes:

- `0`: ZIP und Inhaltsliste stimmen vollständig überein
- `1`: reproduzierbare Inhalts- oder Metadatendrift
- `2`: ZIP, JSON oder Vertragsstruktur ist ungültig

## Selbsttests

```bash
python3 diagnostics/release_readiness/selftest.py
python3 diagnostics/release_readiness/running_status_selftest.py
```

Geprüft werden Rot-, Gelb- und Grünfall, unveränderte Eingabehashes, die atomare Erzeugung aller drei Ausgabeformate sowie die präzise Einstufung eines laufenden GitHub-Status als **LÄUFT** statt **UNBEKANNT**.

## Sicherheitsgrenzen

- keine Änderungen an Manifest, Statusdateien, Testberichten oder Quellcode
- keine Löschoperationen
- keine Shellausführung aus eingelesenen Daten
- sichere relative Pfade ohne `..`
- atomare Ausgabe über temporäre Dateien und `os.replace`
- HTML vollständig lokal, ohne CDN, JavaScript oder Tracking
- GitHub-Abfrage nur über validierten Repositorynamen und Commit-SHA
- Artefaktprüfung ohne Extraktion und ohne Ausführung enthaltener Dateien
- SHA-256-Berechnung streamend in 1-MiB-Blöcken
- doppelte ZIP-Pfade und beschädigte ZIP-Einträge werden abgelehnt
