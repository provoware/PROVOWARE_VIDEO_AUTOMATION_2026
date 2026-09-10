# Exakter Offline-Qualitätsbericht 2.8.3-rc24

## Ergebnis

> **Provenienz-Hinweis zum aktuellen RC24-Kandidaten:** Dieser Bericht dokumentiert einen realen, erfolgreichen historischen Lauf vom 5. August 2026 auf Commit `2e33a2c00a0b2e7aa44f3db38a0a60a2d6998710`. Er darf nicht automatisch als Freigabe der vier Werkzeuge für spätere Kandidatenstände gelesen werden. Die kanonische Quelle `diagnostics/release_readiness/RELEASE_EVIDENCE.json` entscheidet über den aktuellen Stable-Status. Für Ruff 0.16.1 liegt inzwischen ein neuer aktueller Offline-Nachweis aus Run `34418854572` vor; MyPy, Bandit und pip-audit bleiben bis zu einer erneuten Provenienzprüfung offen.

Die exakt gepinnte Qualitätswerkzeugkette wurde am 5. August 2026 vollständig und reproduzierbar ausgeführt. Alle vier Pflichtwerkzeuge bestanden ohne Quell- oder Sicherheitsbefund.

| Werkzeug | Exakte Version | Ergebnis | Rückgabecode |
|---|---:|---|---:|
| Ruff | 0.16.1 | bestanden | 0 |
| MyPy | 2.3.0 | bestanden | 0 |
| Bandit | 1.9.4 | bestanden | 0 |
| pip-audit | 2.10.1 | bestanden | 0 |

## Reproduzierbarer Ablauf

1. Die Paketbasis wurde einmalig mit ausdrücklich freigegebenem Zugriff auf den im Vertrag festgelegten öffentlichen Paketindex aufgebaut.
2. 47 Wheel-Dateien wurden identifiziert, gehasht und in einem atomar veröffentlichten Wheelhouse gebunden.
3. Wheelhouse, Manifest und aufgelöste Hash-Lockdatei wurden erfolgreich verifiziert.
4. Die Qualitätsumgebung wurde ausschließlich mit `--no-index`, `--find-links` und `--require-hashes` installiert.
5. Die installierten Versionen wurden über `importlib.metadata` gegen die Pflichtversionen geprüft.
6. Alle vier Werkzeuge liefen getrennt. Rückgabecodes und vollständige Rohprotokolle wurden unabhängig vom Ergebnis als GitHub-Actions-Artefakt gespeichert.

## Einzelbefunde

### Ruff 0.16.1

`All checks passed!`

Geprüfter Umfang: `src`, `scripts`, `tests` gemäß `pyproject.toml`.

### MyPy 2.3.0

`Success: no issues found in 10 source files`

Geprüfter Umfang: die zehn im verbindlichen externen Qualitätsrunner festgelegten sicherheits- und laufzeitkritischen Module.

### Bandit 1.9.4

Rückgabecode 0; keine Sicherheitsbefunde. Bandit gab ausschließlich harmlose Parserhinweise zu natürlichen Wörtern in Kommentaren aus. Diese Hinweise sind keine Test-IDs, keine Schwachstellen und rechtfertigen keine Quelländerung.

### pip-audit 2.10.1

`No known vulnerabilities found`

Geprüft wurde die exakt gepinnte Laufzeit-Lockdatei mit deaktivierter impliziter Pip-Auflösung.

## Nachweis

- Workflow-Lauf: `30972392104`
- geprüfter Commit: `2e33a2c00a0b2e7aa44f3db38a0a60a2d6998710`
- Artefakt: `pinned-offline-quality-evidence`
- Artefakt-ID: `8917005198`
- Artefakt-SHA-256: `4bc19bb1f3d935f8fab4b197ba9b6a1e5dc3e962b7bc11e28a41a3c5c95b58fd`
- Aufbewahrung: 30 Tage

## Patchentscheidung

Es wurden keine Anwendungsdateien geändert, weil kein konkreter reproduzierbarer Quell- oder Sicherheitsbefund vorlag. Der einzige erste Laufabbruch war eine fehlende Runner-Systemvoraussetzung (`python3-tk`) vor der Werkzeugausführung. Nach Ergänzung dieser bereits vom Toolchain-Laufzeitvertrag verlangten Systemkomponente bestand die unveränderte Werkzeugkette vollständig.

## Einordnung der damaligen Schlussfolgerung

Für den am 5. August 2026 geprüften Commit waren nach diesem Lauf die vier Python-Qualitätswerkzeuge grün. Für den **aktuellen** RC24-Kandidaten gilt jedoch ausschließlich die kanonische Release-Evidence. Dort ist Ruff 0.16.1 durch den neuen Run `34418854572` aktuell bestätigt; MyPy 2.3.0, Bandit 1.9.4 und pip-audit 2.10.1 bleiben bis zu einer erneuten Provenienzprüfung offen.

Unabhängig davon bleiben die physische KDE-Abnahme unter echten X11- und Wayland-Sitzungen sowie der dokumentierte Langzeitrender mit großer Medienauswahl und langsamem externem Ziel erforderlich. Der Kandidat wird nicht als Stable bezeichnet.
