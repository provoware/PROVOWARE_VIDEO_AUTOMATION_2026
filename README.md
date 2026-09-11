<!-- release-status:start -->
# provoware - videoautomation - 2026 · 2.8.3-rc24

**Kanal:** rc
**Kanonische Quelle:** `diagnostics/release_readiness/RELEASE_EVIDENCE.json`
**Freigegebener Qualitätsbericht:** `VideoBatch_Fast_2.8.3-rc24_BUILD_REPORT_save_.json`

- 325/325 automatisierte Tests bestanden
- 82.43 % Zeilenabdeckung
- 67.21 % Zweigabdeckung
- 18/18 visuelle Szenarien bestanden
- Release-Manifest: 468 Dateien
- Kubuntu-CI-Matrix: 1/1 Kombinationen bestanden

### Offene Stable-Gates

- Physische Kubuntu-26.04-Plasma-Wayland-Abnahme: Reale Zielsystem-Abnahme auf Kubuntu 26.04 LTS mit KDE Plasma und nativem Wayland fehlt; die CI-Prüfung ist headless und ersetzt die Sichtabnahme nicht.
- Langzeitrender mit großer Medienauswahl: Realer Lauf auf langsamem externem Ziel fehlt
<!-- release-status:end -->

## Dokumentation

| Aufgabe | Datei | Pflichtgrad |
|---|---|---|
| erster Start und erstes Testvideo | `START_HIER_save_.md` | Pflicht |
| vollständige Bedienung | `docs/BENUTZERHANDBUCH.md` | Empfohlen |
| automatische Installation | `AUTOINSTALLATION_save_.md` | Pflicht bei Installation |
| Fehler beheben | `ERROR_HANDLING.md` | Pflicht bei Fehlern |
| Update und Rückfall | `UPDATE_SYSTEM.md` | Pflicht bei Updates |
| Projektordner verstehen | `PROJEKTORDNERSTRUKTUR_save_.md` | Empfohlen |
| alle Dokumente einordnen | `docs/DOKUMENTATIONSINDEX.md` | Empfohlen |
| Dokumentationen schreiben | `docs/DOKUMENTATIONSSTANDARD.md` | Pflicht für Beiträge |

## Schnellstart

### Schritt 1: ZIP vollständig entpacken

VideoBatch nicht direkt aus dem ZIP starten.

**Warum notwendig?** Einstellungen, Protokolle und Projektzustände müssen geschrieben werden können.

**Kann entfallen?** Nein.

### Schritt 2: Terminal im Projektordner öffnen

### Schritt 3: Starter ausführbar machen

```bash
chmod +x videobatch.sh
```

**Kann entfallen?** Ja, wenn die Datei bereits ausführbar ist.

### Schritt 4: VideoBatch starten

```bash
./videobatch.sh
```

**Erwartetes Ergebnis:** Die Oberfläche öffnet sich nach der Laufzeit-, FFmpeg-, Ordner- und Projektprüfung.

**Bei einem Fehler:** Nicht mit `sudo`, `chmod -R 777` oder rekursiven Besitzänderungen reagieren. `ERROR_HANDLING.md` verwenden.

## Erster Bedienablauf

1. Audiodateien hinzufügen.
2. Bilder oder Videos hinzufügen.
3. Quellenzahlen und Vorschau kontrollieren.
4. Beim ersten Test die Automatik verwenden.
5. Beschreibbaren Ausgabeordner bestätigen.
6. Produktion starten.
7. Queue und Abschlussmeldung abwarten.
8. Anfang, Mitte und Ende des Ergebnisses abspielen.

**Warum ist die Ergebnisprüfung notwendig?** Ein technisch abgeschlossener Render beweist noch nicht, dass Inhalt, Ton und Wirkung korrekt sind.

**Kann sie entfallen?** Vor Veröffentlichung oder Archivierung: nein.

## Was VideoBatch schützt

- Originalmedien werden nicht überschrieben.
- Projektzustände werden bei Fehlern nicht stillschweigend verworfen.
- Schreibziele werden mit einer echten Schreibprobe geprüft.
- pauschale Rootrechte und `chmod 777` sind nicht vorgesehen.
- Wiederanlaufquellen werden geladen, aber nicht automatisch gestartet.
- ungültige Effekte können auf eine sichere Automatik zurückgesetzt werden.
- der Vorschau-Cache entfernt nur eigene, eindeutig erkannte Vorschaudateien.

## Kernfunktionen

- Audio-, Bild- und Videoimport
- automatische Moduswahl und Schnellmodi
- Render-Queue mit Fehler- und Wiederanlaufzuständen
- Vorschau und Thumbnail-Datenträgercache
- direkte sichere Fehlerlösungen
- persistente Projekteinstellungen
- A/B-Update- und Rückfallkonzept
- kanonische Themes, Schriftprofile und KPI-Dashboard
- Design-, Manifest- und Linux-Matrix-Gates

## Vorschau-Cache

Vorschaubilder werden im XDG-Benutzercache gespeichert. Standardgrenzen:

- maximal 1 GiB
- maximal 2.000 VideoBatch-PNG-Dateien

Bei Überschreitung werden zuerst lange nicht verwendete eigene Cacheeinträge entfernt. Originalmedien, Projektdateien und fremde Dateien bleiben unberührt.

### Cache prüfen

1. Bilder- oder Videoauswahl öffnen.
2. `Vorschau-Cache` wählen.
3. Anzahl, Größe, Auslastung, Pfad und letzte Bereinigung kontrollieren.

### Cache leeren

1. `Vorschau-Cache leeren` wählen.
2. Sicherheitsabfrage lesen.
3. Nur bei Platzmangel, Diagnose oder beschädigten Vorschauen bestätigen.

**Kann entfallen?** Ja. Die normale Nutzung erfordert keine regelmäßige manuelle Leerung.

## Mehrere Auswahlrunden

1. Dateien markieren.
2. `Auswahl übernehmen + im Ordner bleiben` wählen.
3. Weitere Quellen ergänzen.
4. Erst mit `Fertig` die Gesamtauswahl in das Projekt übernehmen.

**Kann entfallen?** Ja. Bei einem einzelnen Ordner genügt eine Auswahlrunde.

## Fehlerampel

- **Hinweis:** lesen und Zustand kontrollieren.
- **Warnung:** Ursache prüfen; nur ausdrücklich angebotene sichere Fortsetzung verwenden.
- **Vorgang gestoppt:** Ursache beheben und Vorprüfung erneut ausführen.

Originalmedien und gespeicherte Projekte bleiben bei blockierenden Fehlern unverändert.

## Release- und Dateistatus

<!-- release-files:start -->
## Release-Dateistatus

Only standalone user and release deliverables receive _save_. Source modules, CI workflows, canonical manifests, entrypoints and README retain stable technical names.

| Releasefertig (`_save_`) | Noch nicht releasefertig |
|---|---|
| `START_HIER_save_.md`<br>Schnellstart: Geprüfter Nutzerstart und sichere erste Schritte | `TODO.md`<br>Offene Arbeitsliste: Enthält bewusst die verbleibenden Stable-Gates |
| `AUTOINSTALLATION_save_.md`<br>Installationsanleitung: Benutzerpfade, A/B-Slots und Berechtigungsschutz dokumentiert | `QUALITY_GATE_ATTEMPT_2.8.3-rc24.md`<br>Externe Qualitätswerkzeuge: Technische Provenienzdatei der inzwischen bestandenen Python-Qualitätsgates; bleibt bewusst ohne _save_-Suffix und ist kein Stable-Blocker mehr |
| `PROJEKTORDNERSTRUKTUR_save_.md`<br>Projektübersicht: Ordner, Start, Sicherheit und Funktionen beschrieben | `STABLE_GATE_ITERATION_2.8.3-rc24_2026-09-11.md`<br>Stable-Freigabeiteration: Aktueller Stable-Arbeitsstand; reale Zielsystemabnahme und Langzeitrender sind noch offen |
| `RELEASE_NOTES_save_.md`<br>Releasehinweise: Aktueller RC24-Funktionsstand dokumentiert | `docs/LONG_RENDER_2.8.3-rc24.md`<br>Langzeitrender: Realer Langzeitrender mit großer Auswahl und langsamem Ziel fehlt |
| `TEST_REPORT_save_.md`<br>Testbericht: Automatisierte und offene Prüfungen getrennt ausgewiesen | `docs/STABLE_ACCEPTANCE_EVIDENCE.md`<br>Stable-Abnahmenachweis: Physische Desktop- und Langzeitnachweise fehlen |
| `FRESH_PACKAGE_REPORT_save_.md`<br>Paketbericht: Saubere Paketprüfung für RC24 dokumentiert | `VISUAL_DESKTOP_APPROVAL.md`<br>Desktop-Sichtprüfung: Physische Kubuntu-26.04-Plasma-Wayland-Abnahme bleibt offen |
| `CODE_QUALITY_REPORT_2.8.3-rc24_save_.md`<br>Codequalitätsbericht: Interne Qualitätsprüfung ohne Befund | `QUALITY_ENVIRONMENT_STATUS.json`<br>Qualitätsumgebung: Maschinenlesbarer Status; automatisierte Qualitätsgates sind bestanden, Stable bleibt wegen physischer Kubuntu-26.04-Wayland-Abnahme und Langzeitrender offen |
| `IMPLEMENTATION_REPORT_2.8.3-rc24_save_.md`<br>Implementierungsbericht: Umgesetzte Funktions- und Sicherheitsverträge dokumentiert | `VISUAL_INSPECTION_MANIFEST.json`<br>Visuelles Prüfmanifest: Aktueller physischer Lauf ist nicht vollständig bestätigt |
| `FINAL_AUDIT_2.8.3-rc24_save_.md`<br>RC-Abschlussaudit: RC-Gates und offene Stable-Gates ehrlich getrennt | — |
| `VideoBatch_Fast_2.8.3-rc24_BUILD_REPORT_save_.json`<br>Maschinenlesbarer Buildbericht: Aus der kanonischen RELEASE_EVIDENCE.json erzeugt | — |
<!-- release-files:end -->

**Vor Stable gilt:** Auslieferung als vollständiges Projekt-ZIP. Teil- und Onlineupdates bleiben bis nach der Stable-Freigabe deaktiviert.

## Dokumentationsregel

Aktive Anleitungen müssen Ziel, Pflichtgrad, Voraussetzungen, Sicherung, nummerierte Schritte, Begründung, Weglassbarkeit, erwartetes Ergebnis, Fehlerfall, Abschlussprüfung und nächsten Schritt enthalten. Historische Berichte bleiben unverändert und werden im `docs/DOKUMENTATIONSINDEX.md` als Archiv beziehungsweise Nachweis eingeordnet.

## Abschlussprüfung

Der erste Lauf ist abgeschlossen, wenn die Oberfläche ohne Fehlermeldung startet, ein kurzer Testauftrag beendet wird und das Ergebnis vollständig abgespielt wurde. Stable bleibt bis zu den oben genannten realen Prüfungen gesperrt.

## Nächster Schritt

Einsteiger öffnen `START_HIER_save_.md`. Fortgeschrittene Nutzer verwenden `docs/BENUTZERHANDBUCH.md`. Entwickler beginnen mit `DEVELOPER_GUIDE.md` und `docs/DOKUMENTATIONSSTANDARD.md`.
