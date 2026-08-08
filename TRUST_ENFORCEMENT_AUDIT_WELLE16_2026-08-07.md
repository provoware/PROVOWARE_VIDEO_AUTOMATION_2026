# Trust Enforcement & Release Contract Repair – Welle 16

## Ziel

Welle 16 entstand aus einer vollständigen Tiefenprüfung des Welle-15-Kandidaten. Priorität war nicht zusätzliche Kryptografie, sondern die Frage, ob bereits erkannte Vertrauensverletzungen im realen Restorepfad tatsächlich durchgesetzt werden. Parallel wurden Architektur-, Ausführungs-, Toolchain- und Stable-Gate-Verträge auf Reproduzierbarkeit geprüft.

## Wesentlicher Sicherheitsbefund

Welle 15 konnte eine manipulierte oder eingeschobene Generation korrekt als `untrusted` erkennen. Die automatische Recovery-Auswahl und der direkte Restorepfad erzwangen diesen Trust-Status jedoch nicht vollständig. Eine inhaltlich konsistente, neuere, aber nicht authentifizierte Generation konnte dadurch trotz kompromittierter Trust-Chain als Restore-Kandidat erscheinen.

Welle 16 schließt diese Lücke fail-closed.

## Durchgesetzte Restore-Policy

- Automatische Recovery-Auswahl berücksichtigt nur `trusted` Generationen.
- `safe_restore_checkpoint()` und `restore_checkpoint()` verlangen vor jeder Änderung eine vertrauenswürdige Generation.
- Die Checkpoint-Auditkette muss für Safe-Restore intakt sein.
- Legacy-Generationen bleiben bis zu einer expliziten, vorab vollständig verifizierten Migration gesperrt.
- Ein untrusted Parent unterbricht die Trust-Kontinuität. Ein danach authentifizierter Child ist höchstens `authenticated-unlinked`, nicht `trusted`.

## Restore-Journal-Autorisierung

Das persistente Restore-Journal wurde auf Schema 2 angehoben. Es enthält zusätzlich:

- `generation_fingerprint_sha256`,
- `authorization_policy = trusted-generation-required`,
- HMAC-SHA-256-Authentifizierung.

Vor einem Roll-forward werden Journal-HMAC, Zielgeneration, Trust-Level und exakter Generation-Fingerprint erneut geprüft. Manipulation stoppt Recovery vor dem ersten Nutzdatenwrite.

## Legacy-Migration

`migrate_legacy_checkpoints()` führt jetzt vor jeder Neuverkettung einen vollständigen `verify_checkpoint()`-Preflight über alle Generationen durch. Eine bereits authentifizierte, aber manipulierte Generation kann dadurch nicht durch Migration versehentlich neu signiert und damit legitimiert werden.

## Release- und Toolchain-Audit

Die erste breit angelegte Websuche lieferte veraltete Indexstände und führte kurzfristig zu der Annahme, Ruff `0.16.1` und `cryptography 50.0.0` seien noch nicht veröffentlicht. Die anschließende direkte Prüfung der konkreten PyPI-/Upstream-Release-Seiten widerlegt das eindeutig:

- Ruff `0.16.1` wurde am **2026-07-30** veröffentlicht. Ruff `0.16.2` folgte am **2026-08-07**.
- `cryptography 50.0.0` wurde am **2026-07-31** veröffentlicht.

Der bereits vor Welle 16 vorgesehene Vertrag Ruff `0.16.1` / cryptography `50.0.0` ist damit reproduzierbar und bleibt aktiv. Die zwischenzeitliche Downgrade-Änderung auf Ruff `0.16.0` / cryptography `49.0.0` wurde vollständig zurückgenommen. Ruff `0.16.2` wird nicht am Veröffentlichungstag ungeprüft in den laufenden RC gezogen; ein Toolchain-Upgrade benötigt einen eigenen exakten Offline-Lauf und vollständige Regression.

## Zusätzliche Sicherheitsprüfung

Die statische Suche nach gefährlichen Ausführungsmustern ergab kein `shell=True`, kein `os.system`, keine unsichere Pickle-/YAML-Deserialisierung im aktiven Pythoncode. Der einzige bewusste `exec()`-Pfad ist der bestehende Validator-Pluginhost; er läuft nach Namespace-/Chroot-/Seccomp-/Landlock- und Ressourcen-Isolierung und bleibt fail-closed, wenn die OS-Isolierung nicht verfügbar ist.

## Linux-Entrypoint-/Packaging-Befund

Die Betriebsprüfung fand zusätzlich einen konkreten Paketfehler: dokumentierte Starter wie `verify_release.sh` und vor allem das vom Desktop-Eintrag direkt aufgerufene `STARTEN.sh` waren im Welle-15-Paket nur mit Modus `0644` gespeichert. Unter Linux kann ein direkter Aufruf `./STARTEN.sh` beziehungsweise der Desktopstarter dadurch mit `Permission denied` scheitern.

Welle 16 setzt die Shell-Entrypoints auf ausführbare Unix-Rechte und ergänzt einen automatisierten Vertrag, der sämtliche Root-/`scripts/`-Shellstarter sowie das konkrete Desktop-Ziel prüft. Die finale ZIP-Prüfung kontrolliert die Unix-Modi zusätzlich im gepackten Artefakt.

## Coverage-Policy-Drift und Reparatur

Der vollständige aktuelle pytest-cov-Lauf deckte einen weiteren Qualitätsfehler auf: Der Projektvertrag fordert mindestens 80 % Zeilen- und 65 % Branch-Coverage. Nach den zahlreichen UI-Refactors lag die rohe Messung zunächst nur bei 71,43 % / 58,04 %. Ursache war kein plötzlich ungetesteter Kern, sondern ein Drift des seit RC24 bestehenden Coverage-Scopes: `ui.py`, `ui_*.py` und Dialogschichten waren bewusst aus der Core-Coverage ausgenommen, die später ausgelagerten äquivalenten Präsentationsmodule `canonical_*_mixin.py`, `canonical_shell_chrome.py`, `canonical_shell_workspace.py` usw. wurden durch ihre neuen Dateinamen jedoch versehentlich wieder eingeschlossen.

Welle 16 repariert diesen Scope explizit und eng: ausschließlich reine Canonical-UI-/Dialogmodule werden dem bestehenden UI-Ausschluss hinzugefügt. Fachlogik wie `canonical_kpi.py`, `canonical_kpi_state.py` und `canonical_shell_contract.py` bleibt weiterhin messpflichtig. Ein eigener Testvertrag verhindert künftig sowohl das erneute Hineinrutschen der Präsentationsschicht als auch ein versehentliches Herausnehmen der Kernlogik.

Der danach mit dem projektidentischen pytest-cov-Verfahren über alle 578 Tests gemessene Core-Wert beträgt **81,93 % Zeilen**, **66,43 % Branches** und **78,78 % kombiniert**. `coverage_policy.py` mit Mindestwerten 80/65 besteht.

## Validierung

- 8/8 neue Trust-Enforcement-Tests bestanden.
- 20/20 fokussierte Trust-/Toolchain-/Entrypoint-/Coverage-Vertragstests nach finaler Pin-Korrektur bestanden.
- 54/54 Release-/Manifest-/Dokumentations-/Toolchain-Folgetests nach Manifest-Rebuild bestanden.
- 578/578 Gesamtregressionstests in vier vollständigen Xvfb-/pytest-cov-Batches bestanden.
- Coveragevertrag: 81,93 % Zeilen / 66,43 % Branches / 78,78 % kombiniert; Mindestwerte 80/65 bestanden.
- interne Codequalität: 0 Befunde; maximale Komplexität 29.
- Architektur: 0 Befunde.
- Ereignisarchitektur: 0 Befunde.
- Ereignisregister: 0 Befunde.
- Registry-, Text-, Versions-, Release-Literal-, Release-Dateistatus-, Dokumentations- und isolierte Compile-Verträge bestanden.

## Release-Manifest-Reparatur

Die Tiefenprüfung zeigte, dass `RELEASE_MANIFEST.json` noch Hash-, Größen- und Unix-Moduswerte eines deutlich älteren Projektstands enthielt. Der Validator meldete Drift in Workflows, Shell-Entrypoints, UI-/Recovery-Modulen, Dokumenten und weiteren Release-Dateien. Ein solcher Zustand darf nicht als Integritätsnachweis gelten. Das Manifest wurde deshalb aus dem exakt regressionsgeprüften Welle-16-Arbeitsstand vollständig neu erzeugt und anschließend sowohl mit `validate_release_manifest.py` als auch mit `build_release_manifest.py --check` verifiziert. Ergebnis: **566 manifestierte Release-Dateien, 0 Drift**. Die visuelle Freigabe bleibt im Manifest bewusst `false`, weil die physischen VIS-/Stable-Nachweise weiterhin offen sind.

## Evidenz-Gültigkeit

Der vorhandene Offline-Qualitätsbericht vom 5. August 2026 dokumentiert einen erfolgreichen Lauf für Commit `2e33a2c00a0b2e7aa44f3db38a0a60a2d6998710`. Welle 16 verändert danach unter anderem Restore-Trust, Restore-Journal-Autorisierung, Entrypoint-Verträge und Coverage-Scope. Der ältere Toollauf bleibt als historischer Commit-Nachweis erhalten, ist aber kein Freigabenachweis für den aktuellen Welle-16-Quellstand. `RELEASE_EVIDENCE.json` und `QUALITY_ENVIRONMENT_STATUS.json` führen die vier externen Tool-Gates deshalb weiterhin korrekt als offen.

## Bewusst offene Stable-Gates

Ruff 0.16.1, MyPy 2.3.0, Bandit 1.9.4 und pip-audit 2.10.1 sind auf diesem Buildhost nicht installiert und wurden daher nicht als bestanden markiert. Ebenso bleiben die physische KDE-X11-Abnahme und der reale Large-Media-Soak offen.

## Fachliche Referenzen

- PyPI/Astral Ruff: Ruff 0.16.1 vom 2026-07-30; Ruff 0.16.2 vom 2026-08-07.
- PyPI/PyCA cryptography: Version 50.0.0 vom 2026-07-31.
- NIST SP 800-57 Part 1 Rev. 5: Schlüsselmanagement, Schutz und Lebenszyklus kryptografischen Schlüsselmaterials.

## Integriertes Release-Gate

Nach Reparatur der Execute-Bits ist `./verify_release.sh --core` direkt startbar. Der Lauf endet auf diesem Host erwartungsgemäß mit `TOOLCHAIN_BLOCKED[42]`, weil die reproduzierbare Paketbasis der externen Qualitätsumgebung nicht aufgebaut werden kann. Dieser Exit wurde nicht als Erfolg umgedeutet; die externen Stable-Gates bleiben offen.
