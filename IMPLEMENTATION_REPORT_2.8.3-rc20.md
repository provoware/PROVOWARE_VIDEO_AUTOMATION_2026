# VideoBatch Fast 2.8.3-rc20 – Storyboard und musikgesteuerte Diashow

## Bildreihenfolge

- große horizontale Thumbnail-Leiste
- freie Reihenfolge per Drag-and-drop
- alphabetische Sortierung
- Sortierung nach EXIF-Aufnahmedatum, ersatzweise Dateiänderungszeit
- reproduzierbare Zufallsreihenfolge mit gespeichertem Seed
- Reihenfolge umkehren
- bevorzugtes Start- und Abschlussbild
- vollständige Speicherung im Projektzustand

## Audiowellenform und Szenenmarken

- lokale Dekodierung über FFmpeg
- sichtbare Wellenform ohne Cloudzugriff
- automatische Vorschläge für Intro, Beat-Einsatz, ruhige Phase, Drop und Outro
- optional musikstrukturgesteuerte Bildwechsel
- variable Bildzeiten bei exakt erhaltener Audiodauer
- sicherer Rückfall auf gleichmäßige Zeiten bei Analysefehlern
- begrenzte PCM-Dekodierung und persistenter, streng validierter Cache

## Härtungen

- kurze Audios mit vielen Bildern bleiben mathematisch gültig
- Cachedateien werden größen-, Werte- und Marker-validiert
- beschädigte EXIF-Bilder lösen keinen UI-Abbruch aus
- sämtliche neuen UI-Texte sind ausgelagert
- Konfigurationsnormalisierung wurde in kleine, testbare Funktionen zerlegt
- Update- und Channelfunktionen bleiben bis zur Stable-Freigabe ein Nachrelease-System; RC20 wird als vollständiges Projekt-ZIP ausgeliefert
