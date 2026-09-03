# Exakter Offline-Qualitätsbericht 2.8.3-rc24

## Ergebnis

Die exakt gepinnte Qualitätswerkzeugkette wurde am 3. September 2026 auf dem aktuellen A32.2-Kandidaten vollständig ausgeführt. Alle vier Pflichtwerkzeuge bestanden ohne Quell- oder Sicherheitsbefund.

| Werkzeug | Exakte Version | Ergebnis | Rückgabecode |
|---|---:|---|---:|
| Ruff | 0.16.1 | bestanden | 0 |
| MyPy | 2.3.0 | bestanden | 0 |
| Bandit | 1.9.4 | bestanden | 0 |
| pip-audit | 2.10.1 | bestanden | 0 |

## Geprüfter Kandidat

- Produkt-Commit: `048aa5733d9d0ce5fef872d25e0437fae08eab94`
- Workflow-Lauf: `33801346178`
- isolierter Probe-PR: `#89` (nicht gemergt)
- Evidence-Artefakt: `a32-quality-evidence-048aa573`
- Artefakt-ID: `9911189721`
- Artefakt-SHA-256: `63c172740436777e0bcdfa7593839da0ef8b1c180d9eae7c3070e3fa8cd99fec`
- Runner: Ubuntu 24.04.4 / Python 3.12
- Offline-Netzwerkguard während der vier Qualitätswerkzeuge: aktiv

Der Workflow-Trigger selbst lief auf einem isolierten Probe-Branch. Vor der Qualitätsprüfung wurde hart der oben genannte Produkt-Commit detached ausgecheckt und mit `git rev-parse HEAD` gegen den erwarteten SHA geprüft. Der Probe-Commit ist deshalb nicht der geprüfte Produktstand.

## Reproduzierbarer Ablauf

1. Repository auf exakt `048aa5733d9d0ce5fef872d25e0437fae08eab94` ausgecheckt und Commit-Identität geprüft.
2. Einheits-Wheelhouse aus der gesperrten Werkzeugkette aufgebaut.
3. 47 Wheel-Dateien identifiziert und vollständig verifiziert.
4. Quality-Umgebung aus dem geprüften Wheelhouse offline neu installiert.
5. Installierte Werkzeugversionen exakt gegen den Vertrag geprüft.
6. Ruff, MyPy, Bandit und pip-audit mit aktivem Offline-Netzwerkguard ausgeführt.
7. Version, Status und Rückgabecode aller vier Werkzeuge maschinenlesbar protokolliert.

## Einzelbefunde

### Ruff 0.16.1
Rückgabecode 0. Umfang: `src`, `scripts`, `tests` gemäß `pyproject.toml`.

### MyPy 2.3.0
Rückgabecode 0. Umfang: zehn sicherheits- und laufzeitkritische Module des verbindlichen externen Qualitätsrunners.

### Bandit 1.9.4
Rückgabecode 0; keine Sicherheitsbefunde.

### pip-audit 2.10.1
Rückgabecode 0; keine bekannte Schwachstelle in der exakt gepinnten Laufzeit-Lockdatei. Der Lauf nutzte den vorbereiteten Advisory-Cache unter aktivem Offline-Netzwerkguard.

## Einordnung

Dieser Nachweis ersetzt den veralteten Offline-Quality-Nachweis vom 5. August 2026 für Commit `2e33a2c00a0b2e7aa44f3db38a0a60a2d6998710`. Die Qualitätsampeln werden nicht bloß umgeschrieben, sondern durch einen neuen Lauf auf dem aktuellen A32.2-Kandidaten belegt.

## Verbleibende Stable-Gates

Die externen Python-Qualitätswerkzeuge blockieren Stable nicht. Weiterhin offen bleiben:

1. physische KDE-Abnahme unter echten Zielbedingungen,
2. dokumentierter Langzeitrender mit großer Medienauswahl und langsamem externem Ziel.

Der Kandidat bleibt bis zu diesen Nachweisen `2.8.3-rc24` und wird nicht als Stable bezeichnet.
