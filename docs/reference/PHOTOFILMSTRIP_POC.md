# PhotoFilmStrip Motion-Adapter – isolierter Proof of Concept

## Ziel

Dieser Slice prüft ausschließlich, ob VideoBatch einen rendererunabhängigen Bewegungsplan in ein gültiges
PhotoFilmStrip-Projekt (Schema-Revision 4) übersetzen kann.

Der produktive Runner, die GUI, Projektpersistenz und vorhandene FFmpeg-Pfade bleiben unverändert.

## Neue Module

- `motion_planner.py`
  - rendererunabhängige `MotionRecipe`
  - normierte Fokuspunkte
  - Zoom-in, Zoom-out und horizontale Pan-Presets
  - sichere Crop-Rechtecke innerhalb der Bildgrenzen
  - Abbildung der Bewegungskurve auf PhotoFilmStrip `movement`

- `photofilmstrip_adapter.py`
  - erzeugt atomar eine `.pfs`-SQLite-Datei gemäß PhotoFilmStrip Schema-Revision 4
  - speichert Start-/Zielrechteck, Dauer und Bewegungsart
  - kann optional eine Audiodatei referenzieren
  - baut den dokumentierten `photofilmstrip-cli`-Aufruf
  - erkennt die CLI über `VIDEOBATCH_PHOTOFILMSTRIP_CLI` oder `PATH`

## Sicherheitsgrenze

Dieser Proof of Concept startet PhotoFilmStrip bewusst noch nicht aus dem produktiven `BatchRunner`.
Eine spätere Integration muss den bestehenden Prozessvertrag einhalten:

`BatchRunner -> ProcessExecution -> externer Prozess -> verification.py`

Es wird kein zweiter produktiver Prozesswächter eingeführt.

## Lokale Abnahme

Die Unit-Tests prüfen:

1. Zoom-in verkleinert das Zielrechteck.
2. Zoom-out kehrt die Größenrichtung um.
3. Seitenverhältnis bleibt erhalten.
4. Fokuspunkte werden sicher in die Bildgrenzen geklemmt.
5. Die erzeugte `.pfs` enthält die erwarteten Tabellen, Properties und Bewegungswerte.
6. Der CLI-Aufruf ist deterministisch.

Isolierter PoC-Teststand vor Übernahme: **5/5 Tests bestanden**.

## Noch offenes reales Gate

Auf der aktuellen Prüfumgebung ist `photofilmstrip-cli` nicht installiert. Der reale Render-Gate muss daher auf
einem System mit PhotoFilmStrip erfolgen:

1. Testbild und optional Audio wählen.
2. Mit `write_pfs_project(...)` ein Projekt erzeugen.
3. Den mit `build_render_command(...)` erzeugten Befehl über den bestehenden Prozesswächter ausführen.
4. Die tatsächlich erzeugte Videodatei mit dem vorhandenen `verify_output(...)`/FFprobe-Vertrag prüfen.
5. Erst danach eine produktive Backend-Auswahl oder GUI-Option ergänzen.

## Nächster Integrations-Slice

Wenn der reale Render-Gate grün ist:

- kleine Backend-Schnittstelle für `ffmpeg` und `photofilmstrip`
- PhotoFilmStrip-Ausführung ausschließlich über `ProcessExecution`
- gemeinsames `MotionRecipe` als Quelle für beide Renderer
- erst danach optionale UI-Auswahl
