# Architektur

- `probe.py`: einmalige Medienanalyse und Cache
- `command_builder.py`: direkte FFmpeg-Befehle und Fast-Path-Entscheidung
- `jobs.py`: positionsweise Paarbildung
- `validation.py`: günstige Vorprüfung
- `runner.py`: Prozess, Echtzeitfortschritt, Abbruch und genau ein Fallback
- `verification.py`: schnelle Ergebnisprüfung
- `ui.py`: moderne Ttk-Oberfläche ohne Fachlogik
- `config.py`: atomische XDG-Konfiguration

Die UI startet keine zusammengesetzten Shellbefehle. Alle FFmpeg-Aufrufe werden als Argumentlisten ausgeführt.


## Fast-Effect-Engine

Die Effektengine ist deklarativ in `effects.py` definiert. Jeder Effekt besitzt Schlüssel, deutschen Namen, einfache Beschreibung und Geschwindigkeitsklasse. `command_builder.py` fügt Skalierung, Effekt und Ein-/Ausblendung in genau eine Filterkette ein. Effekte deaktivieren bewusst die Direktkopie, erzeugen aber keine Zwischenfiles und keinen zweiten Renderdurchlauf.
