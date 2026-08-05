# VideoBatch Fast 2.8.3-rc24 starten

Dieses Paket enthält das vollständige Projekt. Teil- und Onlineupdates bleiben bis zur Stable-Freigabe deaktiviert.

## Sicherer Standardstart

```bash
chmod +x videobatch.sh
./videobatch.sh
```

Der Starter prüft Laufzeit, FFmpeg, Projektzustand und benötigte Benutzerverzeichnisse. Qualitätswerkzeuge gehören zur Releaseprüfung und blockieren den normalen Programmstart nicht.

## Erster Ablauf

1. **Audiodateien hinzufügen** wählen.
2. **Bilder oder Videos hinzufügen** wählen.
3. Die zuletzt angeklickte Vorschau kontrollieren.
4. Einen Schnellmodus auswählen.
5. Einen beschreibbaren Ausgabeordner bestätigen.
6. **Automatisch prüfen und Videos erstellen** starten.
7. Die Abschlussmeldung abwarten und das Ergebnis kurz abspielen.

## Bei gelber oder roter Meldung

- Gelb: Hinweis lesen und den genannten Punkt kurz prüfen.
- Rot: Nur der betroffene Schritt ist blockiert. Nutze die angebotene sichere Lösung.
- Originalmedien und gespeicherte Projekte bleiben unverändert.
- Unter **Hilfe** können Systemstatus, Protokolle, Handbuch und Fehlerlabor geöffnet werden.

## Mehrere Auswahlrunden

Im großen Medienbrowser Dateien markieren und **Auswahl übernehmen + im Ordner bleiben** wählen. Weitere Ordner oder Dateien können danach ergänzt werden. Erst **Fertig** übernimmt die Sammlung in das Projekt.

## Vorschau-Cache

Der Dialog **Vorschau-Cache** zeigt Größe, Dateizahl, Auslastung und Pfad. Das sichere Leeren entfernt nur eindeutig erkannte VideoBatch-Vorschaubilder; Originalmedien und fremde Dateien bleiben unberührt.

## Heruntergeladenes Projekt-ZIP prüfen

Ein vollständig verifiziertes GitHub-Actions-Artefakt enthält neben dem Projekt-ZIP:

- eine `.sha256`-Datei für das gesamte ZIP
- `ARTIFACT_CONTENTS.json` mit Pfad, Größe und SHA-256 jeder enthaltenen Datei
- `VERIFIED_SOURCE_ARTIFACT.json` mit Commit und erfüllten Prüfverträgen
- `release-manifest-check.json` mit dem Manifestprüfergebnis

### 1. Gesamtes ZIP prüfen

Im Ordner mit ZIP und `.sha256`-Datei:

```bash
sha256sum --check *.zip.sha256
```

Erwartetes Ergebnis: `OK`.

### 2. Jede enthaltene Datei prüfen

```bash
python3 scripts/build_artifact_contents.py \
  PROVOWARE_VIDEO_AUTOMATION_2026_*_verified.zip \
  --check ARTIFACT_CONTENTS.json
```

Erwartetes Ergebnis:

```text
ARTIFACT-CONTENTS BESTANDEN · <Dateizahl> Dateien · <Bytes> Bytes
```

Exitcodes:

- `0`: ZIP und Inhaltsliste stimmen vollständig überein
- `1`: Dateien fehlen, sind zusätzlich vorhanden oder unterscheiden sich bei Größe, SHA-256 oder Metadaten
- `2`: ZIP oder Inhaltsliste ist beschädigt beziehungsweise strukturell ungültig

Die Prüfung extrahiert und startet keine Datei. Bei Exitcode 1 oder 2 das Archiv nicht ausführen und erneut aus dem zugehörigen grünen GitHub-Actions-Lauf herunterladen.
