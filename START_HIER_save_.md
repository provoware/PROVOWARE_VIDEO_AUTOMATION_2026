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
