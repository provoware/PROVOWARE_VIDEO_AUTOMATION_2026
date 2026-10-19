# VideoBatch – verifizierbare Umzugstabelle (Stand: 2026-10-19)

Basiscommit: `5a30e72bc25887f4e233a61f6c490eb1343fcab1`. Ausgangs-Hauptordner: 46 Dateien; Ziel: 8 Dateien.

**Status:** Entwicklungszweig, NICHT produktiv freigegeben. Jede verschobene Datei verlangt einen Verweis-/Starter-/CI-Nachweis, bevor integriert wird. Alte RC24-Nachweise bleiben unverändert.

## Im Hauptordner verbleiben (8)

- `.gitignore`
- `.gitattributes`
- `AGENTS.md`
- `README.md`
- `STARTEN.sh`
- `pyproject.toml`
- `VERSION.json`
- `RELEASE_MANIFEST.json`

## Umzüge (38)

| Bisher | Neu |
|---|---|
| `ARCHITECTURE_V1.json` | `config/contracts/ARCHITECTURE_V1.json` |
| `CHANGELOG.md` | `docs/CHANGELOG.md` |
| `DEVELOPMENT_STATUS.json` | `config/status/DEVELOPMENT_STATUS.json` |
| `FAULT_LAB_CONTRACT.json` | `config/contracts/FAULT_LAB_CONTRACT.json` |
| `FEHLERLABOR.sh` | `scripts/dev/FEHLERLABOR.sh` |
| `FINALISIEREN.sh` | `scripts/release/FINALISIEREN.sh` |
| `INSTALLER_SYSTEM_CONTRACT.json` | `config/contracts/INSTALLER_SYSTEM_CONTRACT.json` |
| `KUBUNTU_26_04_QT_ABNAHME.sh` | `scripts/acceptance/KUBUNTU_26_04_QT_ABNAHME.sh` |
| `PLATFORM_SUPPORT.json` | `config/contracts/PLATFORM_SUPPORT.json` |
| `PORTABLE_BAUEN.sh` | `scripts/release/PORTABLE_BAUEN.sh` |
| `PORTABLE_RUNTIME_CONTRACT.json` | `config/contracts/PORTABLE_RUNTIME_CONTRACT.json` |
| `QUALITY_ENVIRONMENT_STATUS.json` | `config/status/QUALITY_ENVIRONMENT_STATUS.json` |
| `QUICK_MODES_MANIFEST.json` | `config/contracts/QUICK_MODES_MANIFEST.json` |
| `RELEASE_FILE_STATUS.json` | `config/status/RELEASE_FILE_STATUS.json` |
| `STARTUP_CONTRACT.json` | `config/contracts/STARTUP_CONTRACT.json` |
| `STATUS.md` | `docs/STATUS.md` |
| `TODO.md` | `docs/TODO.md` |
| `TOOLCHAIN_CONTRACT.json` | `config/contracts/TOOLCHAIN_CONTRACT.json` |
| `VISUAL_INSPECTION_MANIFEST.json` | `registries/VISUAL_INSPECTION_MANIFEST.json` |
| `VideoBatch-Fast.desktop` | `resources/desktop/VideoBatch-Fast.desktop` |
| `VideoBatch_Fast_2.8.3-rc24_BUILD_REPORT_save_.json` | `docs/archive/rc24/VideoBatch_Fast_2.8.3-rc24_BUILD_REPORT_save_.json` |
| `autoinstall.sh` | `scripts/install/autoinstall.sh` |
| `build_artifacts.sh` | `scripts/dev/build_artifacts.sh` |
| `manifest.json` | `config/contracts/manifest.json` |
| `quality-toolchain.sh` | `scripts/dev/quality-toolchain.sh` |
| `quality.sh` | `scripts/dev/quality.sh` |
| `requirements-qt.txt` | `config/requirements/requirements-qt.txt` |
| `requirements-quality.lock` | `config/requirements/requirements-quality.lock` |
| `requirements-toolchain.lock` | `config/requirements/requirements-toolchain.lock` |
| `requirements.lock` | `config/requirements/requirements.lock` |
| `requirements.txt` | `config/requirements/requirements.txt` |
| `runtime-toolchain.sh` | `scripts/dev/runtime-toolchain.sh` |
| `setup.sh` | `scripts/install/setup.sh` |
| `stable_release.sh` | `scripts/release/stable_release.sh` |
| `start.sh` | `scripts/cli/start.sh` |
| `test.sh` | `scripts/dev/test.sh` |
| `verify_release.sh` | `scripts/dev/verify_release.sh` |
| `videobatch.sh` | `scripts/cli/videobatch.sh` |

## Offene Nachweise

1. Vollständige dynamische Pfadauflösung (Start, Installation, Qt, FFmpeg, Projekte, Konfiguration, Release, GitHub Actions).
2. Automatische Linux-Start- und Paketprüfungen, beide Root-Dateigrenzen ≤8.
3. Release-Manifest/Projekt-Dateiindex auf denselben unveränderten Commit synchronisieren.
4. Ältere UI-Module nur nach nachgewiesener Qt-Funktionsparität entfernen.
5. Persönliche Kubuntu-Abnahme erst am finalen Releasekandidaten.
