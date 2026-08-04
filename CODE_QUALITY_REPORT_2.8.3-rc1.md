# Codequalitätsbericht – 2.8.3-rc1

## Ergebnis

| Gate | Grenze | Ergebnis |
|---|---:|---:|
| maximale Funktionskomplexität | 30 | **28** |
| Mindest-Coverage | 74 % | **74,43 %** |
| maximale Quelldatei | 700 Zeilen | **584** |
| interne AST-/Sicherheitsbefunde | 0 | **0** |
| Architekturbefunde | 0 | **0** |
| Python-Tests | – | **130 bestanden** |
| Anwendungssimulation | 12 | **12/12** |
| visuelle Regression | 16 | **16/16** |

## Refactoring

- Runner-Prozesssteuerung in `runner_process.py`
- Updatevalidierung in `update_validation.py`
- Seccomp-Aufbau in `sandbox_seccomp.py`
- UI-Ereignisrouting in `ui_event_handlers_mixin.py`
- Projektzustandsnormalisierung in kleinere Hilfsfunktionen zerlegt

## Fehlerpfadabdeckung

Neu oder erweitert geprüft werden unter anderem:

- Prozessstartfehler
- fehlerhafte FFmpeg-Fortschrittswerte
- Stall-Warnung
- Stream-Close-Fehler
- Seccomp-Kontext-, Regel- und Ladefehler
- nicht ladbare Seccomp-Bibliotheken
- Update-Pfadtraversal
- ungültige Manifestoperationen
- falsche Payload-Hashes
- nicht deklarierte ZIP-Dateien
- unzulässige Löschpayloads
- fehlende Stable-Freigabebindung
- atomarer Wheelhouse-Austausch
- Erhalt eines bestehenden Wheelhouse bei Downloadfehler

## Externe Werkzeuge

Exakt gesperrt sind:

- Ruff 0.16.1
- MyPy 2.3.0
- Bandit 1.9.4
- pip-audit 2.10.1
- pytest 9.0.2
- pytest-cov 7.0.0
- coverage 7.13.3

Die Buildumgebung konnte die fehlenden Wheels nicht aus ihrem Paketgateway beziehen. Deshalb lautet der externe Status **blockiert**, nicht bestanden. Ein Stable-Build darf diesen Status nicht übergehen.
