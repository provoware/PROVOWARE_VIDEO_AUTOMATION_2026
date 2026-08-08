# Stable-Gate Evidence Audit – Fortsetzungswelle 17

## Ziel

Welle 17 schließt keine physische oder externe Prüfung künstlich. Sie macht die verbleibenden Stable-Gates reproduzierbar, kandidatengebunden und gegen veraltete oder manipulierte Evidence fail-closed.

## Umgesetzte Härtungen

1. Separate Candidate-Identität aus `candidate_id`, SHA-256 des Release-Manifests und einem kanonischen Source-Fingerprint über ausführungsrelevante Release-Dateien.
2. Externe Qualitätsberichte verwenden Evidence-Schema 4 und müssen exakt an diese Candidate-Identität gebunden sein.
3. Evidence-Index prüft Dateiliste, Größe und SHA-256 jeder Nachweisdatei; hinzugefügte, entfernte oder veränderte Dateien blockieren die Freigabe.
4. Reproduzierbares Quality-Evidence-ZIP mit stabiler Reihenfolge, Zeitstempel und Dateimodus.
5. Toolchain-Wheelhouse-Manifest Schema 2 bindet Toolchain-Lock, Toolchain-Contract und die kanonische komplette Wheelliste.
6. Offline-Installation erzwingt `--no-index`, `--only-binary=:all:` und `--require-hashes`.
7. Stable-Acceptance-Evidence Schema 2 bindet physische Nachweise zusätzlich an `source_sha256`.
8. Physischer KDE-Harness trennt reale Abnahme explizit von CI/Xvfb und prüft neun Größen-/Skalierungsprofile.
9. Large-Media-Harness exportiert Stable-Evidence nur nach realem, nicht als Rehearsal markiertem 96-Job-Lauf auf validiertem langsamem externem Ziel.
10. Importreihenfolge-Abhängigkeit der Evidence-Validatoren beseitigt; Direkt- und Paketaufrufe sind isoliert lauffähig.

## Fachliche Gegenprüfung

- pip dokumentiert für sichere/reproduzierbare Installationen Hash-Checking mit `--require-hashes`; alle direkten und transitiven Anforderungen müssen gepinnt und gehasht sein. Zusätzlich verhindert `--only-binary :all:` Source-Distribution-Fallbacks: https://pip.pypa.io/en/stable/topics/secure-installs/
- `pip hash` ist ausdrücklich zur Erzeugung lokaler Hashes für wiederholbare Installationen vorgesehen: https://pip.pypa.io/en/stable/cli/pip_hash/
- SLSA 1.2 definiert Provenance als verifizierbare Information darüber, woher ein Artefakt stammt und wie es erzeugt wurde. Die Bindung der Evidence an Source- und Manifest-Digests folgt genau diesem Provenance-Prinzip: https://slsa.dev/spec/v1.2/provenance

## Aktuelle Messungen

- Gesamtregression auf dem importstabilisierten Welle-17-Quellstand: **588/588**.
- Frische Coverage-Messung über vollständige deterministische Batches: **81,93 % Lines / 66,43 % Branches / 78,78 % kombiniert**, Policy 80/65 bestanden.
- Interne Qualitätsprüfung: **0 Befunde**, maximale Komplexität **29**.
- Architektur- und Ereignisgates: **0 Befunde**.

## Bewusst offen

Der Host kann PyPI/Files-PyPI aktuell nicht per DNS erreichen. Deshalb wurde der exakte Ruff-0.16.1-/MyPy-2.3.0-/Bandit-1.9.4-/pip-audit-2.10.1-Wheelhouse-Lauf **nicht** als bestanden ausgegeben. Ebenfalls offen bleiben die realen KDE-X11-Abnahme und der reale Large-Media-/Slow-Target-Lauf.

Die Welle-17-Infrastruktur ist damit bereit, diese Nachweise auf geeigneter Hardware/Netzwerkumgebung eindeutig und reproduzierbar zu schließen, ohne alte Evidence wiederverwenden zu können.
