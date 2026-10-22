<!-- release-status:start -->
# provoware - videoautomation - 2026 · 2.8.3-rc24

**Kanal:** rc
**Kanonische Quelle:** `diagnostics/release_readiness/RELEASE_EVIDENCE.json`
**Freigegebener Qualitätsbericht:** `VideoBatch_Fast_2.8.3-rc24_BUILD_REPORT_save_.json`

- 325/325 automatisierte Tests bestanden
- 82.43 % Zeilenabdeckung
- 67.21 % Zweigabdeckung
- 18/18 visuelle Szenarien bestanden
- Release-Manifest: 496 Dateien
- Kubuntu-CI-Matrix: 1/1 Kombinationen bestanden

### Offene Stable-Gates

- Physische Kubuntu-26.04-Plasma-Wayland-Abnahme: Der reale 125-%-Screenshot vom 06.10.2026 zeigte abgeschnittene und überladene Arbeitsbereiche. Der daraus abgeleitete seitengetrennte Qt-Stand muss vor Stable erneut real auf Kubuntu 26.04 / KDE Plasma / Wayland bei 100 %, 125 %, 150 % und 200 % geprüft werden.
<!-- release-status:end -->

> **Nachweisgrenze:** Die vorstehenden RC24-Zahlen (325 Tests, 496 Release-Dateien) stammen aus dem unveränderten historischen Nachweis. Sie sind **keine** Prüfung des Integrationskandidaten PR #240 (Dateiumfang laut aktuellem `RELEASE_MANIFEST.json`). Dessen separate, commitgebundene Ergebnisse stehen unter `diagnostics/release_readiness/CANDIDATE_PR240_CI_EVIDENCE.json` und `CANDIDATE_PR240_QUALITY_STATUS.json`. Es gibt keine neue Stable-Freigabe; eine reale Kubuntu-/Wayland-Sichtabnahme bei 100/125/150/200 % fehlt.


<!-- release-files:start -->
## Release-Dateistatus

Only standalone user and release deliverables receive _save_. Source modules, CI workflows, canonical manifests, entrypoints and README retain stable technical names.

| Releasefertig (`_save_`) | Noch nicht releasefertig |
|---|---|
| `docs/start/START_HIER_save_.md`<br>Schnellstart: Geprüfter Nutzerstart und sichere erste Schritte | `TODO.md`<br>Offene Arbeitsliste: Automatisierte Gates werden für den seitengetrennten Qt-Stand neu geprüft; danach ist die reale 100/125/150/200-%-Sichtabnahme und anschließend die Stable-Promotion offen. |
| `docs/start/AUTOINSTALLATION_save_.md`<br>Installationsanleitung: Benutzerpfade, A/B-Slots und Berechtigungsschutz dokumentiert | `docs/LONG_RENDER_2.8.3-rc24.md`<br>Langzeitrender: Prüfvertrag bleibt als Referenz erhalten; Langzeitrender wurde am 29.09.2026 manuell als in Ordnung bestätigt |
| `docs/start/PROJEKTORDNERSTRUKTUR_save_.md`<br>Projektübersicht: Ordner, Start, Sicherheit und Funktionen beschrieben | `docs/STABLE_ACCEPTANCE_EVIDENCE.md`<br>Stable-Abnahmenachweis: Basisfreigaben bleiben dokumentiert; der reale 125-%-Befund vom 06.10.2026 verlangt eine neue 100/125/150/200-%-Sichtabnahme des korrigierten Qt-Stands. |
| `docs/archive/rc24/RELEASE_NOTES_save_.md`<br>Releasehinweise: Aktueller RC24-Funktionsstand dokumentiert | `QUALITY_ENVIRONMENT_STATUS.json`<br>Qualitätsumgebung: Maschinenlesbarer Qualitätsstatus; nach der Layoutkorrektur müssen die automatisierten Gates erneut grün sein und die physische 100/125/150/200-%-UI-Abnahme bleibt offen. |
| `docs/archive/rc24/TEST_REPORT_save_.md`<br>Testbericht: Automatisierte und offene Prüfungen getrennt ausgewiesen | `VISUAL_INSPECTION_MANIFEST.json`<br>Visuelles Prüfmanifest: Automatisierte visuelle Verträge bleiben Referenz; die reale 100/125/150/200-%-Sichtabnahme des seitengetrennten Qt-Stands steht noch aus. |
| `docs/archive/rc24/FRESH_PACKAGE_REPORT_save_.md`<br>Paketbericht: Saubere Paketprüfung für RC24 dokumentiert | — |
| `docs/archive/rc24/CODE_QUALITY_REPORT_2.8.3-rc24_save_.md`<br>Codequalitätsbericht: Interne Qualitätsprüfung ohne Befund | — |
| `docs/archive/rc24/IMPLEMENTATION_REPORT_2.8.3-rc24_save_.md`<br>Implementierungsbericht: Umgesetzte Funktions- und Sicherheitsverträge dokumentiert | — |
| `docs/archive/rc24/FINAL_AUDIT_2.8.3-rc24_save_.md`<br>RC-Abschlussaudit: RC-Gates und offene Stable-Gates ehrlich getrennt | — |
| `VideoBatch_Fast_2.8.3-rc24_BUILD_REPORT_save_.json`<br>Maschinenlesbarer Buildbericht: Aus der kanonischen RELEASE_EVIDENCE.json erzeugt | — |
<!-- release-files:end -->


## Entwicklungsprüfung (separat vom historischen RC24-Nachweis)

- **Historischer Integrationsstand:** PR #246 (Ordnerstruktur) und PR #251 (Qt-Layout) wurden integriert. PR #252 (Raster) bleibt ein Entwicklungsentwurf. Neuer QA-Bericht: `docs/design/VIDEOBATCH_QA_AUDIT_2026-10-20.md`.
- **Letzter vollständig geprüfter Commit vor diesem Dokumentationsupdate:** `2ae2ae51fb1147b46150fe107b97a53e4a65495f` – alle acht GitHub-Prüfläufe erfolgreich.
- **Entpacktes Benutzerpaket:** ZIP erstellt, Integrität geprüft, **7 Hauptordnerdateien**, interner Kommando-Einstieg über Bash erfolgreich getestet; [Paketprüflauf](https://github.com/provoware/PROVOWARE_VIDEO_AUTOMATION_2026/actions/runs/39339430217).
- **Offen:** vollständige Offline-Erstinstallation und Qt-GUI-Start *aus dem entpackten Paket*, anschließende reale Kubuntu-Endabnahme; keinerlei neue Stable-Freigabe.
- **Pfadstandard:** `STARTEN.sh` im Hauptordner, interne Startskripte unter `scripts/cli/`, Installationsskripte unter `scripts/install/`, Verträge unter `config/contracts/`, Sperrdateien unter `config/requirements/`.

Diese Entwicklungsnotiz ist bewusst **nicht** Teil des automatisch aus historischen RC24-Belegen erzeugten Statusblocks.
