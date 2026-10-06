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

## Überblick

VideoBatch Fast ist die lokale Video-Automation für **Kubuntu 26.04 LTS · KDE Plasma · natives Wayland · PySide6/Qt 6**. Der aktuelle Stand ist **2.8.3-rc24**. Der aktuelle Releasekandidat enthält jetzt einen seitengetrennten Qt-Arbeitsbereich als Reaktion auf den realen 125-%-Sichtbefund vom 06.10.2026. Dateien, Ausgabe und Produktion besitzen eigene Arbeitsseiten; Projekt, Hilfe und Diagnose verdrängen den Hauptablauf nicht mehr. Vor Stable ist eine erneute reale Sichtprüfung bei 100 %, 125 %, 150 % und 200 % erforderlich.

## Schnellstart

1. Projekt-ZIP vollständig entpacken.
2. Terminal im Projektordner öffnen.
3. Falls nötig den Starter ausführbar machen:

```bash
chmod +x videobatch.sh
```

4. VideoBatch starten:

```bash
./videobatch.sh
```

5. Für den ersten Lauf einen **kurzen Testauftrag** verwenden und das Ergebnis am Anfang, in der Mitte und am Ende abspielen.

**Sicherheitsregel:** Bei einem Fehler nicht mit `sudo`, `chmod -R 777` oder rekursiven Besitzänderungen reagieren. Stattdessen `ERROR_HANDLING.md` verwenden.

## Repository auf einen Blick

| Bereich | Zweck |
|---|---|
| `videobatch.sh`, `start.sh`, `STARTEN.sh` | Start- und Launcherpfade |
| `START_HIER_save_.md`, `AUTOINSTALLATION_save_.md` | Einstieg und Installation |
| `src/` | Anwendungscode |
| `scripts/` | Prüf-, Build-, Release- und Wartungsskripte |
| `tests/` | automatisierte Funktions- und Vertragsprüfungen |
| `.github/workflows/` | CI- und Merge-Gates |
| `docs/` | aktuelle Fach- und Projektdokumentation |
| `docs/reference/` | technische Referenzdokumente, bewusst aus dem Hauptverzeichnis ausgelagert |
| `docs/archive/` | historische interne Nachweise und alte Prüfstände |
| `diagnostics/release_readiness/` | kanonische Release-Evidence |
| `RELEASE_MANIFEST.json` | kompakter reproduzierbarer Release-Vertrag |

**Ordnungskonzept:** Im Hauptverzeichnis bleiben vor allem Startdateien, aktive Release-Unterlagen und maschinenlesbare Verträge. Technische Hintergrunddokumente gehören nach `docs/reference/`; historische interne Nachweise nach `docs/archive/`.

## Dokumentation

| Aufgabe | Datei |
|---|---|
| erster Start und erstes Testvideo | `START_HIER_save_.md` |
| vollständige Bedienung | `docs/BENUTZERHANDBUCH.md` |
| automatische Installation | `AUTOINSTALLATION_save_.md` |
| Fehler sicher beheben | `ERROR_HANDLING.md` |
| Update und Rückfall | `UPDATE_SYSTEM.md` |
| Projektstruktur verstehen | `PROJEKTORDNERSTRUKTUR_save_.md` |
| Dokumente einordnen | `docs/DOKUMENTATIONSINDEX.md` |
| Entwickler-Einstieg | `DEVELOPER_GUIDE.md` |
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
| `START_HIER_save_.md`<br>Schnellstart: Geprüfter Nutzerstart und sichere erste Schritte | `TODO.md`<br>Offene Arbeitsliste: Automatisierte Gates werden für den seitengetrennten Qt-Stand neu geprüft; danach ist die reale 100/125/150/200-%-Sichtabnahme und anschließend die Stable-Promotion offen. |
| `AUTOINSTALLATION_save_.md`<br>Installationsanleitung: Benutzerpfade, A/B-Slots und Berechtigungsschutz dokumentiert | `docs/LONG_RENDER_2.8.3-rc24.md`<br>Langzeitrender: Prüfvertrag bleibt als Referenz erhalten; Langzeitrender wurde am 29.09.2026 manuell als in Ordnung bestätigt |
| `PROJEKTORDNERSTRUKTUR_save_.md`<br>Projektübersicht: Ordner, Start, Sicherheit und Funktionen beschrieben | `docs/STABLE_ACCEPTANCE_EVIDENCE.md`<br>Stable-Abnahmenachweis: Basisfreigaben bleiben dokumentiert; der reale 125-%-Befund vom 06.10.2026 verlangt eine neue 100/125/150/200-%-Sichtabnahme des korrigierten Qt-Stands. |
| `RELEASE_NOTES_save_.md`<br>Releasehinweise: Aktueller RC24-Funktionsstand dokumentiert | `QUALITY_ENVIRONMENT_STATUS.json`<br>Qualitätsumgebung: Maschinenlesbarer Qualitätsstatus; nach der Layoutkorrektur müssen die automatisierten Gates erneut grün sein und die physische 100/125/150/200-%-UI-Abnahme bleibt offen. |
| `TEST_REPORT_save_.md`<br>Testbericht: Automatisierte und offene Prüfungen getrennt ausgewiesen | `VISUAL_INSPECTION_MANIFEST.json`<br>Visuelles Prüfmanifest: Automatisierte visuelle Verträge bleiben Referenz; die reale 100/125/150/200-%-Sichtabnahme des seitengetrennten Qt-Stands steht noch aus. |
| `FRESH_PACKAGE_REPORT_save_.md`<br>Paketbericht: Saubere Paketprüfung für RC24 dokumentiert | — |
| `CODE_QUALITY_REPORT_2.8.3-rc24_save_.md`<br>Codequalitätsbericht: Interne Qualitätsprüfung ohne Befund | — |
| `IMPLEMENTATION_REPORT_2.8.3-rc24_save_.md`<br>Implementierungsbericht: Umgesetzte Funktions- und Sicherheitsverträge dokumentiert | — |
| `FINAL_AUDIT_2.8.3-rc24_save_.md`<br>RC-Abschlussaudit: RC-Gates und offene Stable-Gates ehrlich getrennt | — |
| `VideoBatch_Fast_2.8.3-rc24_BUILD_REPORT_save_.json`<br>Maschinenlesbarer Buildbericht: Aus der kanonischen RELEASE_EVIDENCE.json erzeugt | — |
<!-- release-files:end -->

**Vor Stable gilt:** Auslieferung als vollständiges Projekt-ZIP. Teil- und Onlineupdates bleiben bis nach der Stable-Freigabe deaktiviert.

## Abschlussprüfung

Ein erster Lauf gilt als erfolgreich, wenn die Oberfläche ohne Fehlermeldung startet, ein kurzer Testauftrag abgeschlossen wird und das erzeugte Ergebnis plausibel abgespielt wurde. **Stable ist noch nicht freigegeben.** Zuerst muss der seitengetrennte UI-Stand auf Kubuntu 26.04 / KDE / Wayland real bei 100 %, 125 %, 150 % und 200 % geprüft werden; erst danach folgt die getrennte reproduzierbare Stable-Promotion mit finaler Paket-, Branch-, Tag- und Release-Prüfung.

## Nächster Schritt

- **Einsteiger:** `START_HIER_save_.md`
- **Nutzer:** `docs/BENUTZERHANDBUCH.md`
- **Entwickler:** `DEVELOPER_GUIDE.md`
- **Aktueller Arbeitsplan:** `TODO.md`
