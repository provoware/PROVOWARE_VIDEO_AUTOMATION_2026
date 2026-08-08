# Exakter Offline-Qualitätsbericht 2.8.3-rc24

> **Geltungsbereich:** Dieser Nachweis gilt ausschließlich für den unten genannten Commit `2e33a2c00a0b2e7aa44f3db38a0a60a2d6998710` vom 5. August 2026. Welle 16 verändert danach sicherheitsrelevanten Quellcode und Toolchain-/Coverage-Verträge. Der Bericht darf deshalb **nicht** als Freigabenachweis für den aktuellen Welle-16-Stand verwendet werden. Für Welle 16 bleiben Ruff 0.16.1, MyPy 2.3.0, Bandit 1.9.4 und pip-audit 2.10.1 bis zu einem erneuten exakten Lauf offen.

## Ergebnis

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

## Verbleibende Stable-Gates

Die externen Python-Qualitätswerkzeuge blockieren Stable nicht mehr. Weiterhin offen bleiben:

1. physische KDE-Abnahme unter echter X11-Sitzung,
2. dokumentierter Langzeitrender mit großer Medienauswahl und langsamem externem Ziel.

Der Kandidat bleibt bis zu diesen beiden Nachweisen `2.8.3-rc24` und wird nicht als Stable bezeichnet.
