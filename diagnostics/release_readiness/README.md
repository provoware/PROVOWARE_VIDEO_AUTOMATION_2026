# Kanonisches Release-Evidence- und Bereitschaftssystem

Dieses Modul trennt **eine Primärquelle** von allen abgeleiteten Ansichten.

## Primärquelle

`RELEASE_EVIDENCE.json` ist die einzige manuell gepflegte Quelle für:

- Produktversion und Releasekanal
- bestätigte Test- und Abdeckungszahlen
- aktuelle Release-Manifestzahl
- Kubuntu-CI-Matrix und ihre Provenienz
- interne Qualitätskennzahlen
- releasefertige und unfertige Dateien
- Stable-Gates und ihre Begründungen
- Stable-Bereitschaft und Fortschritt

README, Buildbericht, Entwicklungsstatus, Qualitätsstatus und Release-Dateistatus werden daraus erzeugt. Das Dashboard verwendet dieselbe Quelle und behandelt alle abgeleiteten Dateien nur noch als **Driftprüfungen**.

## Abgeleitete Dateien erzeugen

```bash
python3 diagnostics/release_readiness/generate_from_evidence.py --write
python3 scripts/build_release_manifest.py
```

Danach den Vertrag prüfen:

```bash
python3 diagnostics/release_readiness/generate_from_evidence.py --check
python3 scripts/validate_release_manifest.py
```

`--check` verändert nichts. Bereits eine manuell geänderte Testzahl, Manifestzahl, Blockerliste oder README-Statuszeile führt zu `RELEASE-EVIDENCE-DRIFT`.

## Release-Bereitschaft erzeugen

Mit abgeschlossenem CI-Snapshot:

```bash
python3 diagnostics/release_readiness/release_readiness_dashboard.py \
  --root . \
  --ci-file diagnostics/release_readiness/ci_status.completed.json
```

Live-CI über ausschließlich lesende GitHub-Rechte:

```bash
GITHUB_TOKEN="...read-only token..." \
python3 diagnostics/release_readiness/release_readiness_dashboard.py \
  --root . \
  --github-repository provoware/PROVOWARE_VIDEO_AUTOMATION_2026 \
  --github-sha "$GITHUB_SHA"
```

Benötigte Berechtigungen:

```yaml
permissions:
  contents: read
  actions: read
  checks: read
```

## Ausgaben

Nur unter `build/release-readiness/`:

- `RELEASE_READINESS_STATUS.json`
- `RELEASE_READINESS_DASHBOARD.md`
- `RELEASE_READINESS_DASHBOARD.html`

Der Ausgabeordner ist vom Release-Manifest ausgeschlossen.

## Ampellogik

- **GRÜN:** alle Pflicht-Gates bestanden, CI abgeschlossen, keine Drift
- **GELB:** Quellen widerspruchsfrei, aber mindestens ein Stable-Gate offen oder CI noch nicht final
- **ROT:** Manifestfehler, fehlgeschlagene CI, ungültige Eingaben oder Drift zwischen Primärquelle und Ableitungen

Exitcodes:

- `0` = GRÜN
- `1` = GELB
- `2` = ROT oder Eingabefehler

## Selbsttests

```bash
python3 diagnostics/release_readiness/selftest.py
python3 diagnostics/release_readiness/running_status_selftest.py
```

Geprüft werden:

- GELB bei offenen Stable-Gates
- GELB und präzise **LÄUFT** bei aktiver CI
- GRÜN bei vollständig abgeschlossenen Gates
- ROT bei einer manipulierten abgeleiteten Testzahl
- unveränderte Eingabehashes
- atomare Dashboardausgabe

## Sicherheitsgrenzen

- Dashboard und `--check` sind vollständig rein lesend
- der Generator schreibt nur die fest definierten abgeleiteten Dateien
- keine Shellausführung aus eingelesenen Daten
- keine absoluten oder rückwärts gerichteten Pfade
- atomare Ausgabe über temporäre Dateien und `os.replace`
- HTML ohne CDN, JavaScript oder Tracking
- physische KDE-Abnahme bleibt von der headless CI-Matrix getrennt
