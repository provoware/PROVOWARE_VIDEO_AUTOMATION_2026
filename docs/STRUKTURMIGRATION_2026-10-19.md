# Strukturmigration – Plan und Bestandsaufnahme (2026-10-19)

Basis-Commit: `5a30e72bc25887f4e233a61f6c490eb1343fcab1`.

**Noch nicht verschoben:** Diese Tabelle ist der verbindliche Migrationsentwurf, nicht der Nachweis einer abgeschlossenen Verschiebung.

Ziel: maximal acht Dateien direkt im Repository-Hauptordner **und** im entpackten Nutzerpaket. Geplant: sechs Dateien (inklusive `.gitignore` und `.gitattributes`). Die endgültige Paketstruktur ist separat zu verifizieren. Keine Live-Release-Freigabe.

| Bisherige Datei | Verbindlicher Zielpfad |
|---|---|
| `.gitattributes` | `.gitattributes` |
| `.gitignore` | `.gitignore` |
| `AGENTS.md` | `AGENTS.md` |
| `ARCHITECTURE_V1.json` | `config/ARCHITECTURE_V1.json` |
| `CHANGELOG.md` | `docs/CHANGELOG.md` |
| `DEVELOPMENT_STATUS.json` | `config/DEVELOPMENT_STATUS.json` |
| `FAULT_LAB_CONTRACT.json` | `config/FAULT_LAB_CONTRACT.json` |
| `FEHLERLABOR.sh` | `scripts/entrypoints/FEHLERLABOR.sh` |
| `FINALISIEREN.sh` | `scripts/entrypoints/FINALISIEREN.sh` |
| `INSTALLER_SYSTEM_CONTRACT.json` | `config/INSTALLER_SYSTEM_CONTRACT.json` |
| `KUBUNTU_26_04_QT_ABNAHME.sh` | `scripts/entrypoints/KUBUNTU_26_04_QT_ABNAHME.sh` |
| `PLATFORM_SUPPORT.json` | `config/PLATFORM_SUPPORT.json` |
| `PORTABLE_BAUEN.sh` | `scripts/entrypoints/PORTABLE_BAUEN.sh` |
| `PORTABLE_RUNTIME_CONTRACT.json` | `config/PORTABLE_RUNTIME_CONTRACT.json` |
| `QUALITY_ENVIRONMENT_STATUS.json` | `config/QUALITY_ENVIRONMENT_STATUS.json` |
| `QUICK_MODES_MANIFEST.json` | `config/QUICK_MODES_MANIFEST.json` |
| `README.md` | `README.md` |
| `RELEASE_FILE_STATUS.json` | `config/RELEASE_FILE_STATUS.json` |
| `RELEASE_MANIFEST.json` | `config/RELEASE_MANIFEST.json` |
| `STARTEN.sh` | `STARTEN.sh` |
| `STARTUP_CONTRACT.json` | `config/STARTUP_CONTRACT.json` |
| `STATUS.md` | `docs/STATUS.md` |
| `TODO.md` | `docs/TODO.md` |
| `TOOLCHAIN_CONTRACT.json` | `config/TOOLCHAIN_CONTRACT.json` |
| `VERSION.json` | `config/VERSION.json` |
| `VISUAL_INSPECTION_MANIFEST.json` | `config/VISUAL_INSPECTION_MANIFEST.json` |
| `VideoBatch-Fast.desktop` | `resources/desktop/VideoBatch-Fast.desktop` |
| `VideoBatch_Fast_2.8.3-rc24_BUILD_REPORT_save_.json` | `docs/archive/rc24/VideoBatch_Fast_2.8.3-rc24_BUILD_REPORT_save_.json` |
| `autoinstall.sh` | `scripts/entrypoints/autoinstall.sh` |
| `build_artifacts.sh` | `scripts/entrypoints/build_artifacts.sh` |
| `manifest.json` | `config/manifest.json` |
| `pyproject.toml` | `pyproject.toml` |
| `quality-toolchain.sh` | `scripts/entrypoints/quality-toolchain.sh` |
| `quality.sh` | `scripts/entrypoints/quality.sh` |
| `requirements-qt.txt` | `config/requirements-qt.txt` |
| `requirements-quality.lock` | `config/requirements-quality.lock` |
| `requirements-toolchain.lock` | `config/requirements-toolchain.lock` |
| `requirements.lock` | `config/requirements.lock` |
| `requirements.txt` | `config/requirements.txt` |
| `runtime-toolchain.sh` | `scripts/entrypoints/runtime-toolchain.sh` |
| `setup.sh` | `scripts/entrypoints/setup.sh` |
| `stable_release.sh` | `scripts/entrypoints/stable_release.sh` |
| `start.sh` | `scripts/entrypoints/start.sh` |
| `test.sh` | `scripts/entrypoints/test.sh` |
| `verify_release.sh` | `scripts/entrypoints/verify_release.sh` |
| `videobatch.sh` | `scripts/entrypoints/videobatch.sh` |

## Vor jedem tatsächlichen Umzug

1. Startskripte: `STARTEN.sh` → `scripts/debug_launcher.py`; `start.sh`, `videobatch.sh`, Bootstrap und `01_START_HIER` konsolidieren. Python-/Shell-Pfade sowie Arbeitsverzeichnis zentral ableiten.
2. Releasevertragsdateien (`VERSION.json`, `RELEASE_MANIFEST.json`, `TOOLCHAIN_CONTRACT.json`) über einen gemeinsamen Pfadresolver aktualisieren; alte Releasebelege bleiben unverändert im Archiv.
3. `scripts/package_release.py`, `scripts/build_portable_bundle.py`, `scripts/build_release_manifest.py`, `src/videobatch_fast/versioning.py`, `registry.py`, Installer/A-B-Updater und sämtliche CI-Workflows auf neue Pfade umstellen. Insbesondere Release-Manifeste, Dateiregister und Prüfsummen neu, aber ausschließlich für den neuen Entwicklungskandidaten, ableiten.
4. Unterordner `01_START_HIER` erst nach funktionierender Hauptstarter-Parität und Anpassung aller Verweise entfernen. Tk-Legacy nur nach tatsächlicher Aufrufer- und Funktionsparitätsprüfung löschen, niemals ausschließlich wegen Namen.
5. In getrenntem Integrationszweig: Start, Offline-Bootstrap, Paketerzeugung, Signaturen, Updates, alle Pflichtprüfungen sowie entpacktes Testpaket prüfen. Keine persönliche Kubuntu-Gesamtabnahme vor finalem Release.

Aktuell gibt es sechs offene Issues (#80, #137, #233, #234, #235, #238), deren Überschneidungen und Zwischenstände vor Abschluss einzeln abgeglichen werden müssen.
