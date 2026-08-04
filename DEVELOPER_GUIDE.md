# Developer Guide – 2.8.3-rc11

## Entwicklungsfolge

```text
Änderung
→ zielgerichtete Tests
→ interne Qualitätsprüfung
→ vollständige Coverage-Prüfung
→ visuelle Kandidatenprüfung in temporärer Kopie
→ Build-Artefakte ausdrücklich erzeugen
→ Release-Manifest erzeugen
→ schreibgeschützte Vollprüfung
→ Frischpaketprüfung
```

## Lokale Befehle

```bash
PYTHONPATH=src python -m pytest -q tests/test_hardening_2_8_2.py
./build_artifacts.sh
./test.sh
./quality.sh
```

`test.sh` nutzt für XDG-Zustand, Coverage, Diagnosen und visuelle Kandidaten temporäre Verzeichnisse. Änderungen an manifestierten Projektdateien sind ein Fehler.

## Neue Kernmodule

- `naming.py`: stapelweite Zielreservierung
- `archive_service.py`: Journal und Recovery
- `runner.py`: terminale Ereignisgarantie und Prozesseskalation
- `os_sandbox.py`: Seccomp, Landlock und Ressourcenlimits
- `plugin_runtime.py`: Namespace-/Chroot-Launcher
- `updates.py`: unveränderlicher Kandidatenvertrag
- `internal_quality_gate.py`: AST-, Sicherheits- und Komplexitätsgrenzen

## Abhängigkeiten

Laufzeit: `requirements.lock`  
Entwicklerwerkzeuge: `requirements-quality.lock`

Keine Versionsbereiche in Lockdateien. Änderungen an Abhängigkeiten benötigen neue Tests, Audit und Manifest.
