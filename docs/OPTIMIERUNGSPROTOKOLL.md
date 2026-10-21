# PROVOWARE – Optimierungsprotokoll

## 2026-10-21 – VideoBatch: Benutzerordner niemals automatisch umbenennen

- **Projekt:** `provoware/PROVOWARE_VIDEO_AUTOMATION_2026`
- **Befund:** `PATH-DATA-001`
- **Ausgangs-HEAD:** `e49abcea684ce7967e87f8bc062a78c2af2e7f1d`
- **Entwicklungszweig:** `auto/20261021-userdir-no-rename`
- **Status:** Korrektur und sechs Tests eingecheckt; Vollprojektprüfung bei PR-Erstellung noch offen.

### Ausgangsproblem

`src/videobatch_fast/paths.py` führte nach fehlgeschlagener Schreibprobe eine Umbenennung des betroffenen Benutzerordners mit `os.replace()` aus und legte anschließend einen neuen Ordner an. Ein bloßer Berechtigungsfehler konnte damit vorhandene Benutzerdateien unerwartet an einen versteckten anderen Ort verschieben.

### Umsetzung

`_prepare_directory()` führt nur noch die vorhandene Schreibprobe aus. Im Fehlerfall meldet sie verständlich, welcher Ordner betroffen ist, und fordert zur Kontrolle der Zugriffsrechte beziehungsweise Wahl eines anderen Speicherorts auf. Automatisches Verschieben oder Wiederholen ist entfernt; die weiterhin erforderliche Anlage neuer Ordner erfolgt nur durch die normale Schreibprobe.

### Nutzermehrwert

Persönliche Daten bleiben am vertrauten Ort. Fehlende Zugriffsrechte werden nicht mehr durch eine stillschweigende Verzeichnisumbenennung kaschiert. Keine neue Laufzeitabhängigkeit und keine Änderung am Benutzerdatenformat.

### Rückfalltests

`tests/test_paths_permission_safety.py` enthält sechs Prüfungen: Schreibfehler bei bestehendem Ordner mit Originaldatei; bestehende Datei statt Verzeichnis; neuer normaler Ordner; kaputte symbolische Verknüpfung; kein zweiter Schreibversuch; Erhalt des Inhalts eines beschreibbaren Ordners.

**Prüfgrenze:** Die Tests waren vor der GitHub-Integration als isolierte Prüfung mit Python 3.13.5 erfolgreich (6/6). Das vollständige Projekt und die aktuelle GitHub-Prüfung müssen den unveränderten PR-Commit getrennt bewerten. Reale Zielsystem-Abnahme auf Kubuntu 26.04 bleibt ausdrücklich zurückgestellt.

### GitHub

- [Entwicklungszweig](https://github.com/provoware/PROVOWARE_VIDEO_AUTOMATION_2026/tree/auto/20261021-userdir-no-rename)
- [Pull Requests](https://github.com/provoware/PROVOWARE_VIDEO_AUTOMATION_2026/pulls)

### Nächste Empfehlung

Den unveränderten Pull-Request-HEAD mit bestehenden Pfad-/Start-/Sicherheitsprüfungen kontrollieren, gegebenenfalls Release-Index und Manifest gemäß `AGENTS.md` erst für den finalisierten Dateibaum regenerieren; keine historische Releasefreigabe behaupten.
