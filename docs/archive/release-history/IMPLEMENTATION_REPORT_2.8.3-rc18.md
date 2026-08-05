# VideoBatch Fast 2.8.3-rc18 – Implementierungsbericht

## Ziel

Die bisher zu dicht verschachtelte Oberfläche wurde in klar erreichbare, vollflächige Arbeitsbereiche zerlegt. Gleichzeitig wurde der Installations- und Ordnerzugriff so gehärtet, dass normale Nutzerpfade ohne Rootrechte verwendet und unbrauchbare Altpfade automatisch umgangen werden.

## Umgesetzt

### Berechtigungen

- Installation ausschließlich in benutzereigene XDG-Pfade
- kein pauschales `sudo` und keine globalen Schreibrechte
- Schreibprobe vor Installation und vor Ausgabeverwendung
- sichere Quarantäne ungeeigneter Altordner
- kontrollierter Ausweichpfad, falls der Standardpfad nicht nutzbar ist
- verständliche Statusanzeige statt Python- oder Shell-Traceback
- symbolische Altpfade werden per `lstat` erkannt, ohne unzugänglichen Zielen zu folgen

### Oberfläche

- sechs Haupt-Tabs: Start, Medien, Vorschau, Modus & Ausgabe, Produktion, Hilfe & Protokoll
- obere Menüleiste mit Datei-, Medien-, Ansicht-, Produktions-, Werkzeug- und Hilfefunktionen
- stabile Tabnavigation statt ineinander verschachtelter Splitter
- getrennte Zoomstufe für jeden Hauptbereich
- globale Schriftvergrößerung bleibt zusätzlich verfügbar
- aktive Registerkarte und Zoomwerte werden persistent gespeichert
- alte splitterbasierte Layoutdaten werden nicht mehr angewendet

### Medienauswahl

- großer Medienbrowser mit Mehrfachauswahl
- Start im Downloads-Ordner
- Navigation zu Home, Downloads und übergeordnetem Ordner
- Bild- und Videovorschau
- Audioinformationen
- sortierbare Spalten nach Typ, Name, Größe und Änderungszeit
- Ordnerimport
- größere Tabellenzeilen und sichtbare Scrollleisten
- Doppelklick führt direkt zur Vorschau

## Sicherheit und Rückfall

Die Änderungen beeinflussen A/B-Slots, Update-Signaturen, Recovery-Journal, atomare Dateischreibvorgänge und Renderpipeline nicht. Bei einem unbrauchbaren Ausgabeordner wird ein sicherer Nutzerpfad gewählt; bestehende Daten werden nicht still gelöscht oder mit Rootrechten verändert.
