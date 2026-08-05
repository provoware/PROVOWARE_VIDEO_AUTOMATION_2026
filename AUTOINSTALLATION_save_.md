# Automatische Installation · VideoBatch Fast 2.8.3-rc24

## Sicherheitsgrundsatz

VideoBatch installiert in benutzereigene XDG-Pfade und benötigt keine pauschalen Rootrechte. Unbekannte Ordner erhalten niemals rekursiv `chmod 777` oder einen erzwungenen Besitzerwechsel.

## Ablauf

1. Betriebssystem, Architektur und vorhandene Werkzeuge prüfen.
2. Installationsziel durch eine echte Schreibprobe validieren.
3. Unbrauchbare Altpfade sicher quarantänisieren oder einen XDG-Ausweichpfad wählen.
4. Signaturen, SHA-256, Paketgrößen und Entpackgrenzen prüfen.
5. Den inaktiven A/B-Slot vollständig aufbauen.
6. Runtime-, Medien- und UI-Selbsttest ausführen.
7. Den `current`-Link atomar umschalten.
8. Oberfläche starten und erfolgreichen Boot bestätigen.
9. Aktiven Slot abschließend unabhängig prüfen.

Kann ein Ziel nicht sicher verwendet werden, bleibt es unverändert. Der Installer nennt Ursache, Schutzmaßnahme und einen kontrollierten Benutzerpfad als Alternative.
