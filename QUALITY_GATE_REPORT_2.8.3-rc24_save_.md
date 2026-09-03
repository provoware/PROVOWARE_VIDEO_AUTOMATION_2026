# Exakter Offline-Qualitätsbericht 2.8.3-rc24

## Ergebnis

Die exakt gepinnte Qualitätswerkzeugkette wurde am 3. September 2026 erneut vollständig auf dem aktuellen A32.2-Head `934688e8a2f9e1344a91a959396aaef361ee9b67` ausgeführt. Alle vier Pflichtwerkzeuge bestanden mit Rückgabecode 0; der finale Werkzeuglauf lief mit aktivierter Offline-Netzwerksperre.

| Werkzeug | Exakte Version | Ergebnis | Rückgabecode |
|---|---:|---|---:|
| Ruff | 0.16.1 | bestanden | 0 |
| MyPy | 2.3.0 | bestanden | 0 |
| Bandit | 1.9.4 | bestanden | 0 |
| pip-audit | 2.10.1 | bestanden | 0 |

## Geprüfter Kandidat

- Produkt-Commit: `934688e8a2f9e1344a91a959396aaef361ee9b67`
- Workflow-Lauf: `33804721216`
- Trigger-Branch: `ci/a32-2-quality-evidence-934688e8`
- Evidence-Artefakt: `a32-pinned-offline-quality-evidence-934688e8`
- Artefakt-ID: `9912461944`
- Artefakt-SHA-256: `7574b309911b3c067583510b7e418af1ceec999e59008ea1c07c1d12525a4c7c`
- Offline-Netzwerkguard während der vier Qualitätswerkzeuge: aktiv

Der Workflow-Trigger lief absichtlich auf einem isolierten Helper-Branch. Vor der Qualitätsprüfung wurde hart der oben genannte Produkt-Commit ausgecheckt und gegen den erwarteten SHA geprüft. Der Helper-Commit ist deshalb nicht der geprüfte Produktstand; der nachträgliche Evidence-Commit zertifiziert nicht sich selbst.

## Einzelbefunde

### Ruff 0.16.1
Rückgabecode 0; Umfang `src`, `scripts`, `tests` gemäß `pyproject.toml`.

### MyPy 2.3.0
Rückgabecode 0; zehn sicherheits- und laufzeitkritische Module des verbindlichen externen Qualitätsrunners ohne Befund.

### Bandit 1.9.4
Rückgabecode 0; keine Sicherheitsbefunde.

### pip-audit 2.10.1
Rückgabecode 0; keine bekannte Schwachstelle in der exakt gepinnten Laufzeit-Lockdatei. Der finale Audit lief unter aktivem Offline-Netzwerkguard.

## Verbleibende Stable-Gates

Die externen Python-Qualitätswerkzeuge blockieren Stable nicht. Weiterhin offen bleiben:

1. physische KDE-Abnahme unter echten Zielbedingungen,
2. dokumentierter Langzeitrender mit großer Medienauswahl und langsamem externem Ziel.

Der Kandidat bleibt bis zu diesen Nachweisen `2.8.3-rc24` und wird nicht als Stable bezeichnet.
