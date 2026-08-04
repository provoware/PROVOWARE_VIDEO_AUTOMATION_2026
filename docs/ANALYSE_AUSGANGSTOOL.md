# Analyse des Ausgangstools

## Geschwindigkeitsvorteile

Das Ausgangstool kopiert bei Videos ohne Skalierung den Videostream mit `-c:v copy`. Dadurch wird das Bild nicht neu berechnet. Bei Bildern ist eine Videocodierung technisch unvermeidbar, allerdings ohne Übergänge, Effekte oder komplexe Filter.

## Erkannte Schwachstellen

- Fortschritt nur nach vollständig abgeschlossenem Auftrag
- kein aktueller Jobfortschritt und keine Restzeit
- `subprocess.run` liefert während des Laufs keine Rückmeldung
- Fehlerstatus wird von `_run` nicht an die Stapellogik zurückgegeben
- nach FFmpeg-Fehler kann trotzdem die Prüfung und ein Retry folgen
- Retry erfolgt nur wegen einer einfachen Audio-Dauerprüfung
- Konfiguration wird nicht atomisch und nicht über XDG gespeichert
- Fehler beim Speichern werden still ignoriert
- keine Schreibrechts- oder Speicherplatzprüfung
- keine Abbruchfunktion
- keine Kollisionsstrategie außer Zeitstempel
- starres Tkinter-Layout ohne flexible Größenaufteilung
- keine klaren Jobzustände oder Fast-Path-Erklärung

## Neue Leitlinie

Die neue Edition erhält den schnellen direkten Prozess, ersetzt aber die unklare Ausführung durch kontrollierte Vorprüfung, maschinenlesbaren FFmpeg-Fortschritt, genau einen sicheren Fallback und eine moderne flexible Oberfläche.
