# FAIL_MEMORY_PASS

## Pflichtablauf jeder Folge-Iteration

1. Diese Datei vor Analyse, Planung oder Änderung vollständig lesen.
2. Genau einen klar abgegrenzten offenen Punkt auswählen.
3. Vorher Ziel, betroffene Dateien, Risiken und bewusste Nicht-Änderungen festhalten.
4. Den kleinsten vollständigen Patch umsetzen.
5. Syntax, Logik, Fehlerpfade, Dokumentation und betroffene Regressionen prüfen.
6. Ergebnisse, neue Erkenntnisse und Restpunkte hier aktualisieren.

## Kurzzeitgedächtnis - aktuelle Iteration

### Ziel
Dauerhaften Thumbnail-Datenträgercache vollständig begrenzen und absichern.

### Umsetzung
- bestehende persistente Vorschauablage unter dem XDG-Cache weiterverwendet
- Cachegrenzen: 256 MiB und 2.000 PNG-Dateien
- LRU-Bereinigung anhand letzter Nutzung
- Quellpfad, Änderungszeit, Dateigröße und Zielbreite bleiben Bestandteil des Cache-Schlüssels
- Cachetreffer aktualisieren die Nutzung, ohne Quelldateien zu verändern
- neue Vorschauen werden zuerst in eine Teil-Datei geschrieben und anschließend atomar übernommen
- unvollständige, zu kleine oder fehlgeschlagene Erzeugnisse werden verworfen
- das aktuell erzeugte oder gelesene Vorschaubild wird während der Bereinigung geschützt

### Erfolgsbedingungen
- alte Einträge werden zuerst entfernt
- Datei- und Bytegrenze werden unabhängig eingehalten
- Nicht-PNG-Dateien bleiben unangetastet
- geänderte Quelldateien erzeugen einen neuen Cache-Schlüssel
- bestehender Vorschaupfad und Aufrufervertrag bleiben kompatibel

## Mittelfristige Erinnerung

- Cachebereinigung darf niemals Originalmedien, Projektdateien oder fremde Dateien anfassen.
- Generierte Dateien immer atomar bereitstellen; keine halbfertigen Ergebnisse unter endgültigem Namen veröffentlichen.
- GUI-Threads dürfen keine FFmpeg-, Bilddekodierungs- oder Verzeichnisbereinigungsarbeit ausführen.
- Cachegrenzen müssen feste sichere Standardwerte besitzen; spätere Nutzereinstellungen benötigen harte Min-/Max-Grenzen.
- Tests bevorzugen kleine isolierte temporäre Verzeichnisse und dürfen keine echte Benutzerablage verändern.

## Langfristige Erinnerung

- Stable-Freigabe niemals aus Teiltests ableiten.
- Physische KDE-X11-/Wayland-Abnahme und Langzeitrender bleiben eigenständige Freigabegates.
- Dokumentation, Statusdateien und Release-Manifeste dürfen keinen höheren Reifegrad behaupten als die Nachweise tragen.
- Nach jeder Iteration: neue Fehlerursache, Schutzregel, Testnachweis und nächster Engpass eintragen.

## Fehlerwissen

### Bereits vermieden
- unbegrenztes Wachstum eines dauerhaft gespeicherten Vorschaucaches
- Überschreiben einer gültigen Vorschau durch einen abgebrochenen FFmpeg-Lauf
- erneute Verwendung veralteter Vorschauen nach Änderung der Quelle
- versehentliches Löschen fremder Dateitypen im Cacheordner

### Noch zu beobachten
- parallele Prozesse können gleichzeitig unterschiedliche Vorschaubilder erzeugen; atomare Endübernahme schützt die Dateien, ein optionales pro-Schlüssel-Lock könnte später doppelte Arbeit reduzieren
- reale Langzeitmessung mit mehreren tausend Medien auf langsamem Datenträger steht noch aus

## Nächster bevorzugter Entwicklungspunkt

Cacheverwaltung in den Diagnose-Dialog aufnehmen: aktuelle Größe, Dateianzahl, Limit, manueller sicherer Leerungsknopf und verständliche Wirkungserklärung.

## Alternative mit hohem Nutzen und geringem Risiko

Pro-Schlüssel-Erzeugungssperre ergänzen, damit zwei Prozesse dieselbe Vorschau nicht gleichzeitig berechnen, ohne die bestehende atomare Sicherheit zu verändern.
