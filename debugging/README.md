# VideoBatch Debugging

Dieser Ordner ist der lokale Zielort für verständliche Debug- und Absturzberichte.

Der Debugmodus ist bei einer neuen Konfiguration standardmäßig aktiv und bleibt aktiv, bis er im Tool unter **Dashboard → Darstellung → Debugmodus** ausgeschaltet wird.

Bei einem Fehler enthält der TXT-Bericht mindestens:

- **WAS?** – was aus Sicht des Benutzers passiert ist,
- **WIE?** – wie VideoBatch den Fehler erkannt hat,
- **WO?** – betroffene Datei, Funktion oder Startphase,
- **LÖSUNG?** – sichere nächste Schritte,
- vollständigen Python-Traceback, soweit vorhanden,
- System-, Fenster-, Projekt- und Laufzeitkontext,
- letzte Debugschritte,
- verfügbare Bootstrap- und Startup-Auszüge.

Generierte `*.txt`, `*.log` und `*.json`-Dateien werden absichtlich nicht versioniert. Sie bleiben lokal im Projektordner. Wenn der Projektordner nicht beschreibbar ist, verwendet VideoBatch als sichere Notlösung den Benutzer-State-Ordner `~/.local/state/VideoBatchFast/debugging`.

Berichte werden nicht automatisch hochgeladen oder versendet.
