# Automatische Installation – RC18

## Grundsatz

VideoBatch benötigt keine Rootrechte. Das Programm wird in benutzereigenen XDG-Pfaden installiert. Eine pauschale Berechtigungsfrage am Anfang wäre unsicher und unnötig.

## Ablauf

1. System, Architektur und verfügbare Werkzeuge prüfen.
2. Installationsziel mit einer echten Schreibprobe prüfen.
3. Unbrauchbare Altpfade sicher quarantänisieren oder einen XDG-Ausweichpfad wählen.
4. Signaturen, Hashes, Paketgrößen und Entpackgrenzen prüfen.
5. Den inaktiven A/B-Slot vollständig aufbauen.
6. Runtime-, Medien- und UI-Selbsttest ausführen.
7. Den `current`-Link atomar umschalten.
8. Oberfläche starten und Boot bestätigen.
9. Aktiven Slot abschließend unabhängig prüfen.

## Berechtigungsfehler

Der Installer führt niemals rekursive `chmod 777`- oder Besitzänderungen an unbekannten Ordnern aus. Kann ein Pfad nicht sicher verwendet werden, bleibt er unverändert und VideoBatch wechselt in einen kontrollierten Benutzerpfad.
