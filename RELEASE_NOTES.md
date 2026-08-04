# Release Notes 2.8.3-rc24

## Kritische Stabilitätskorrektur

Der verbleibende Absturz beim Anklicken eines Bildes in der bereits ausgewählten Medienliste wurde behoben.
Der frühere Pfad startete pro Auswahlereignis einen eigenen Hintergrundthread und einen eigenen
FFmpeg-Vorschauprozess. Schnelle Klickfolgen konnten dadurch parallele native Prozesse, veraltete
Ergebnisse und unsichere Bildübergaben an Tk erzeugen.

RC24 verwendet stattdessen genau einen seriellen Vorschauarbeiter. Neue Klicks ersetzen wartende
Anfragen; alte Ergebnisse werden anhand eines Generationstokens verworfen.

## Sichere Vorschau

- 180-ms-Debounce für schnelle Auswahlwechsel
- genau ein laufender Vorschauauftrag
- Fokuszeile statt erster Mehrfachauswahleintrag
- sichere Größen- und Pixelgrenzen
- Pillow-Validierung vor ImageTk
- kontrollierte Behandlung gelöschter oder beschädigter Dateien
- kein Tk-Zugriff aus Hintergrundthreads
- sauberes Beenden beim Programmschluss

## Interaktive Fehlerlösung

Bei einem Vorschaufehler stehen jetzt funktionsfähige Aktionen bereit:

- Datei technisch erneut prüfen
- Datei extern öffnen
- Protokoll öffnen

## Ausgabeform

RC24 wird als vollständiges Projekt-ZIP bereitgestellt. Teil- und Onlineupdates bleiben bis nach
der Stable-Veröffentlichung ein Nachrelease-System.
