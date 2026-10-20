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

> **Nachweisgrenze:** Die vorstehenden RC24-Zahlen (325 Tests, 496 Release-Dateien) stammen aus dem unveränderten historischen Nachweis. Sie sind **keine** Prüfung des aktuellen Strukturmigrationszweigs PR #246. Historische Entwicklungsbelege für PR #240 sind separat archiviert; neue CI-Ergebnisse werden ausschließlich über den geprüften Commit nachgewiesen. Es gibt keine neue Stable-Freigabe; eine reale Kubuntu-/Wayland-Sichtabnahme bei 100/125/150/200 % fehlt.


## Überblick

VideoBatch Fast ist die lokale Video-Automation für **Kubuntu 26.04 LTS · KDE Plasma · natives Wayland · PySide6/Qt 6**. Der aktuelle Stand ist **2.8.3-rc24**. Der aktuelle Releasekandidat enthält jetzt einen seitengetrennten Qt-Arbeitsbereich als Reaktion auf den realen 125-%-Sichtbefund vom 06.10.2026. Dateien, Ausgabe und Produktion besitzen eigene Arbeitsseiten; Projekt, Hilfe und Diagnose verdrängen den Hauptablauf nicht mehr. Vor Stable ist eine erneute reale Sichtprüfung bei 100 %, 125 %, 150 % und 200 % erforderlich.

## Aktueller Entwicklungsstand – PR #246 (nicht Stable)

**Einziger offener Entwicklungs-PR zum Prüfzeitpunkt:** [#246 – Benutzer-Hauptordner und sichere Strukturmigration](https://github.com/provoware/PROVOWARE_VIDEO_AUTOMATION_2026/pull/246). Die früheren parallelen PRs #247, #248 und #250 wurden geschlossen; **#250 wurde ohne Merge** abgelöst und seine benötigten Änderungen wurden geprüft in #246 übernommen.

**Nachweisstand vor dieser Dokumentationsaktualisierung:** Commit [`2ae2ae5`](https://github.com/provoware/PROVOWARE_VIDEO_AUTOMATION_2026/commit/2ae2ae51fb1147b46150fe107b97a53e4a65495f), **acht von acht GitHub-Prüfläufen erfolgreich**. Die Prüfungen enthalten Qt6 mit Wayland-Lebenszyklus, Offline-Runtime, Integrations- und Sicherheitswerkzeuge, FFmpeg, Langrender sowie Release-Verträge. Der reale ZIP-Bau und Entpacktest [GitHub-Lauf 39339430217](https://github.com/provoware/PROVOWARE_VIDEO_AUTOMATION_2026/actions/runs/39339430217) bestätigte **sieben Hauptordnerdateien** und den Aufruf des entpackten Kommando-Einstiegs. Dieser konkrete Nachweis ist auf `2ae2ae5` begrenzt; nach weiteren Änderungen gelten dessen Ergebnisse nicht automatisch für neue Commits.

**Noch nicht bewiesen:** Vollständige Offline-Erstinstallation und grafischer Qt-Start aus dem frisch entpackten Paket. Ebenso offen bleiben die persönliche Kubuntu-Sichtabnahme bei 100/125/150/200 % sowie die Stable-Freigabe. Die 325 historischen RC24-Tests sind kein Entwicklungs- oder Stable-Nachweis für #246.

## In Entwicklung: Platzsparende Qt-Oberfläche (20.10.2026)

Die nächste Oberflächenrunde prüft eine gleichmäßige Dateiauswahl auf breiten Bildschirmen. Auf schmalen Fenstern beziehungsweise bei großer Schrift werden die Bereiche automatisch untereinander angeordnet und können **vertikal** gescrollt werden. So bleiben Listen und Schaltflächen lesbar, ohne horizontalen Bildlauf zu erzwingen.

Die CPU-/RAM-/SWAP-Anzeigen und der Video-Fortschritt erhalten einen gemeinsamen, deutlich kompakteren Statusbereich. Die Schrift- und Ansichtsgröße kann von **80 % bis 200 %** eingestellt werden; der neue Ausgangswert ist **110 %**. Kompakte Abstände sollen Platz gewinnen, ohne die Bedienfunktionen zu entfernen.

**Freigabegrenze:** Dies ist eine laufende Entwicklungsänderung. Erst nach vollständigen Qt6-/Wayland- und Größenprüfungen einschließlich kleiner Fenster und 100/125/150/200-%-Sichtprüfung gilt die neue Aufteilung als freigegeben. Die persönliche physische Kubuntu-Endabnahme bleibt separat offen.

## Prüfablauf ohne wiederholte Endabnahmen

1. **Entwickeln:** Änderungen mit passenden automatisierten Tests und Sicherheitsprüfungen absichern. Keine persönliche Vollabnahme nach jeder Oberflächenänderung.
2. **Integrieren:** Mehrere erfolgreich geprüfte Entwicklungs-PRs ohne bekannte kritische Fehler in `main` zusammenführen. Die GitHub-Prüfung `Release contract sync` prüft dabei mit `--phase integration` ausschließlich aktuelle Dateiverträge und hält historische RC24-Belege getrennt.
3. **Endabnahme kurz vor Release:** Sobald Funktionen und Erscheinungsbild fertig sind, den Releasekandidaten einfrieren und dann *einmal gebündelt* auf Kubuntu 26.04/KDE/Wayland real starten, bei 100/125/150/200 % bedienen, echte Videos/FFmpeg und den Langzeitrender prüfen. Der separate `--phase release --acceptance-dir <Pfad>`-Vertrag bleibt ohne reale Nachweise strikt gesperrt.

Das historische RC24-Archiv wird nicht als neue Qualitätsmessung wiederverwendet. Die jeweils aktuellen GitHub-Prüfläufe sind anhand ihres Commits nachvollziehbar; es werden keine erfundenen PASS-Werte in den Quellbaum geschrieben.

## Schnellstart

1. Projekt-ZIP vollständig entpacken.
2. Terminal im Projektordner öffnen.
3. Falls nötig den Starter ausführbar machen:

```bash
chmod +x STARTEN.sh
```

4. VideoBatch starten:

```bash
./STARTEN.sh
```

5. Für den ersten Lauf einen **kurzen Testauftrag** verwenden und das Ergebnis am Anfang, in der Mitte und am Ende abspielen.

**Sicherheitsregel:** Bei einem Fehler nicht mit `sudo`, `chmod -R 777` oder rekursiven Besitzänderungen reagieren. Stattdessen `docs/manuals/ERROR_HANDLING.md` verwenden.

## Repository auf einen Blick

| Bereich | Zweck |
|---|---|
| `STARTEN.sh` | einziger kanonischer Hauptstarter; interne Kommandoaufrufe unter `scripts/cli/` |
| `docs/start/START_HIER_save_.md`, `docs/start/AUTOINSTALLATION_save_.md` | Einstieg und Installation |
| `src/` | Anwendungscode |
| `scripts/` | Prüf-, Build-, Release- und Wartungsskripte |
| `tests/` | automatisierte Funktions- und Vertragsprüfungen |
| `.github/workflows/` | CI- und Merge-Gates |
| `docs/` | aktuelle Fach- und Projektdokumentation |
| `docs/reference/` | technische Referenzdokumente, bewusst aus dem Hauptverzeichnis ausgelagert |
| `docs/archive/` | historische interne Nachweise und alte Prüfstände |
| `diagnostics/release_readiness/RELEASE_EVIDENCE.json` | historischer RC24-Release-Nachweis (496 Dateien) |
| `diagnostics/release_readiness/CANDIDATE_PR240_QUALITY_STATUS.json` | getrennte Entwicklungsnachweise (keine Freigabe) |
| `RELEASE_MANIFEST.json` | kompakter reproduzierbarer Release-Vertrag |

**Ordnungskonzept:** Im Hauptverzeichnis bleiben höchstens acht Dateien; der aktuelle Pakettest zählt sieben. Interne Start- und Installationsskripte liegen unter `scripts/`, Verträge unter `config/`. Technische Hintergrunddokumente gehören nach `docs/reference/`; historische interne Nachweise nach `docs/archive/`.

## Dokumentation

| Aufgabe | Datei |
|---|---|
| erster Start und erstes Testvideo | `docs/start/START_HIER_save_.md` |
| vollständige Bedienung | `docs/BENUTZERHANDBUCH.md` |
| automatische Installation | `docs/start/AUTOINSTALLATION_save_.md` |
| Fehler sicher beheben | `docs/manuals/ERROR_HANDLING.md` |
| Update und Rückfall | `docs/manuals/UPDATE_SYSTEM.md` |
| aktuelle Entwicklung und offene Nachweise | `docs/STATUS.md`, `docs/TODO.md` |
| chronologische Änderungen | `docs/CHANGELOG.md` |
| Projektstruktur verstehen | `docs/start/PROJEKTORDNERSTRUKTUR_save_.md` |
| Dokumente einordnen | `docs/DOKUMENTATIONSINDEX.md` |
| Entwickler-Einstieg | `docs/manuals/DEVELOPER_GUIDE.md` |
| technische Referenzen | `docs/reference/` |
| Dokumentationsstandard | `docs/DOKUMENTATIONSSTANDARD.md` |

## Sicherheitsprinzipien

- Originalmedien werden nicht überschrieben.
- Schreibziele werden vor produktiven Vorgängen geprüft.
- Wiederanlaufzustände werden kontrolliert geladen und nicht stillschweigend gestartet.
- Projekt- und Qualitätsprüfungen sollen lesend beziehungsweise reproduzierbar bleiben.
- Stable wird nicht aus CI-Ergebnissen allein abgeleitet. Der Langzeitrender vom 29.09.2026 bleibt gültig; nach dem realen 125-%-Layoutbefund muss der korrigierte Qt-Stand bei 100 %, 125 %, 150 % und 200 % erneut sichtbar geprüft werden.

## Erster Test

1. Wenige Audio-, Bild- oder Videoquellen hinzufügen.
2. Vorschau und erkannte Quellen kontrollieren.
3. Einen beschreibbaren Ausgabeordner auswählen.
4. Produktion starten und Queue bis zum Abschluss beobachten.
5. Ergebnis vollständig stichprobenartig prüfen.
6. Erst danach größere Aufträge verwenden.

Für Cache, Mehrfachauswahl, Schnellmodi und weitere Bedienfunktionen ist `docs/BENUTZERHANDBUCH.md` die maßgebliche Anleitung.

## Release- und Dateistatus

<!-- release-files:start -->
## Release-Dateistatus

Only standalone user and release deliverables receive _save_. Source modules, CI workflows, canonical manifests, entrypoints and README retain stable technical names.

| Releasefertig (`_save_`) | Noch nicht releasefertig |
|---|---|
| `docs/start/START_HIER_save_.md`<br>Schnellstart: Geprüfter Nutzerstart und sichere erste Schritte | `docs/TODO.md`<br>Offene Arbeitsliste: Automatisierte Gates werden für den seitengetrennten Qt-Stand neu geprüft; danach ist die reale 100/125/150/200-%-Sichtabnahme und anschließend die Stable-Promotion offen. |
| `docs/start/AUTOINSTALLATION_save_.md`<br>Installationsanleitung: Benutzerpfade, A/B-Slots und Berechtigungsschutz dokumentiert | `docs/LONG_RENDER_2.8.3-rc24.md`<br>Langzeitrender: Prüfvertrag bleibt als Referenz erhalten; Langzeitrender wurde am 29.09.2026 manuell als in Ordnung bestätigt |
| `docs/start/PROJEKTORDNERSTRUKTUR_save_.md`<br>Projektübersicht: Ordner, Start, Sicherheit und Funktionen beschrieben | `docs/STABLE_ACCEPTANCE_EVIDENCE.md`<br>Stable-Abnahmenachweis: Basisfreigaben bleiben dokumentiert; der reale 125-%-Befund vom 06.10.2026 verlangt eine neue 100/125/150/200-%-Sichtabnahme des korrigierten Qt-Stands. |
| `docs/archive/rc24/RELEASE_NOTES_save_.md`<br>Releasehinweise: Aktueller RC24-Funktionsstand dokumentiert | `config/status/QUALITY_ENVIRONMENT_STATUS.json`<br>Qualitätsumgebung: Maschinenlesbarer Qualitätsstatus; nach der Layoutkorrektur müssen die automatisierten Gates erneut grün sein und die physische 100/125/150/200-%-UI-Abnahme bleibt offen. |
| `docs/archive/rc24/TEST_REPORT_save_.md`<br>Testbericht: Automatisierte und offene Prüfungen getrennt ausgewiesen | `registries/VISUAL_INSPECTION_MANIFEST.json`<br>Visuelles Prüfmanifest: Automatisierte visuelle Verträge bleiben Referenz; die reale 100/125/150/200-%-Sichtabnahme des seitengetrennten Qt-Stands steht noch aus. |
| `docs/archive/rc24/FRESH_PACKAGE_REPORT_save_.md`<br>Paketbericht: Saubere Paketprüfung für RC24 dokumentiert | — |
| `docs/archive/rc24/CODE_QUALITY_REPORT_2.8.3-rc24_save_.md`<br>Codequalitätsbericht: Interne Qualitätsprüfung ohne Befund | — |
| `docs/archive/rc24/IMPLEMENTATION_REPORT_2.8.3-rc24_save_.md`<br>Implementierungsbericht: Umgesetzte Funktions- und Sicherheitsverträge dokumentiert | — |
| `docs/archive/rc24/FINAL_AUDIT_2.8.3-rc24_save_.md`<br>RC-Abschlussaudit: RC-Gates und offene Stable-Gates ehrlich getrennt | — |
| `docs/archive/rc24/VideoBatch_Fast_2.8.3-rc24_BUILD_REPORT_save_.json`<br>Maschinenlesbarer Buildbericht: Aus der kanonischen RELEASE_EVIDENCE.json erzeugt | — |
<!-- release-files:end -->

**Vor Stable gilt:** Auslieferung als vollständiges Projekt-ZIP. Teil- und Onlineupdates bleiben bis nach der Stable-Freigabe deaktiviert.

## Abschlussprüfung

Ein erster Lauf gilt als erfolgreich, wenn die Oberfläche ohne Fehlermeldung startet, ein kurzer Testauftrag abgeschlossen wird und das erzeugte Ergebnis plausibel abgespielt wurde. **Stable ist noch nicht freigegeben.** Zuerst muss der seitengetrennte UI-Stand auf Kubuntu 26.04 / KDE / Wayland real bei 100 %, 125 %, 150 % und 200 % geprüft werden; erst danach folgt die getrennte reproduzierbare Stable-Promotion mit finaler Paket-, Branch-, Tag- und Release-Prüfung.

## Nächster Schritt

- **Einsteiger:** `docs/start/START_HIER_save_.md`
- **Nutzer:** `docs/BENUTZERHANDBUCH.md`
- **Entwickler:** `docs/manuals/DEVELOPER_GUIDE.md`
- **Aktueller Arbeitsplan:** `docs/TODO.md`
