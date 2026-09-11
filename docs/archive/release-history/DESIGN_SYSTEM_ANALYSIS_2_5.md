# Design- und Layoutanalyse der Vorlage

## 1. Quelle und Messgrundlage

- Referenzdatei: `resources/reference/laienmodus_einfach_reference.png`
- Bildgröße: **810 × 701 Pixel**
- Auswertung: visuelle Strukturprüfung plus automatisierte Farbreduktion
- Maschinenlesbare Analyse: `resources/reference/laienmodus_einfach_analysis.json`

Die Vorlage ist kein klassisches dichtes Produktionsfenster, sondern eine **ruhige Startzentrale für Einsteiger**. Sie priorisiert verständliche Handlungen vor technischen Details.

## 2. Visuelle Hierarchie

Die Vorlage folgt fünf klaren Ebenen:

1. **Modus- und Seitentitel**
   - große weiße Überschrift
   - gelbe nummerierte Kennzeichnung
   - kurze graue Unterzeile

2. **Begrüßungs- und Hilfebereich**
   - direkte Frage an den Nutzer
   - Hilfe rechts als eigenständige Aktion

3. **Vier Hauptaktionen**
   - gleichwertige große Kacheln
   - eindeutige Farbcodierung
   - Symbol über Beschriftung
   - großzügige Klickfläche

4. **Assistent und Tipps**
   - zwei Karten mit klarer Zuständigkeit
   - linker Bereich größer als rechter Bereich
   - Assistent zeigt eine einfache Schrittfolge
   - Tipps zeigen kurze präventive Hinweise

5. **Schnellaktionen und Fußinformation**
   - vier flachere Schaltflächen
   - niedrigere visuelle Priorität
   - kleine Schrift-/Statusaktionen am unteren Rand

## 3. Größen- und Flächenverhältnisse

Aus der Vorlage abgeleitete Zielverhältnisse:

- äußerer Inhaltsrahmen: ungefähr **94 % der Bildbreite**
- Hauptaktionsreihe: ungefähr **20 % der Gesamthöhe**
- Assistent-/Tippsreihe: ungefähr **30 % der Gesamthöhe**
- Verhältnis Assistent zu Tipps: ungefähr **60 : 40**
- Kachelabstand: klein, aber klar sichtbar
- Innenabstand der Hauptkarten: ungefähr **16–24 Pixel** in der Referenzskala
- Rahmen: dünn, warm-golden, nicht leuchtend-neonartig

Die Umsetzung verwendet diese Verhältnisse als Orientierung, nicht als starre Pixelkopie. Dadurch bleibt die Oberfläche bei unterschiedlichen Schriftgrößen und Bildschirmauflösungen benutzbar.

## 4. Farbcharakter

Dominante automatisch erkannte Grundfarben:

- sehr dunkles Oliv-Schwarz: `#0d0f0a`
- dunkles Grün-Anthrazit: `#161c19`
- erhöhte dunkle Fläche: `#202115`
- warme Rahmenfarbe: ungefähr `#423820` bis `#655521`
- gedämpfter Sekundärtext: ungefähr `#808779`

Hauptkacheln:

- Gold/Gelb: warme Primäraktion
- Magenta: Projekt-/Kreativaktion
- Grün: Notiz, Status oder sichere Aktion
- Blau: Audio, Wiedergabe oder Medienaktion

Die Projektumsetzung nutzt folgende semantische Hauptwerte:

- Gold: `#d7b043`
- Magenta: `#7b2a62`
- Grün: `#335d2e`
- Blau: `#23567a`

Diese Werte werden durch visuelle Regressionstests auf sichtbare Präsenz geprüft.

## 5. Typografie

Die Vorlage verwendet:

- helle, kräftige Hauptüberschriften
- gut lesbare Standardtexte
- gedämpfte Sekundärtexte
- kurze Beschriftungen
- keine langen technischen Erklärungen in der Hauptansicht

Übertragene Regeln:

- keine abgeschnittenen Hauptbeschriftungen
- Textumbruch bei Untertiteln
- große Aktionsschriften
- technische Details nur im Arbeitsbereich
- Status nie ausschließlich über Farbe

## 6. Interaktionsmodell

Die Vorlage vermittelt ein Assistentenmodell:

- Nutzer wählt zuerst **eine verständliche Aufgabe**
- Hilfe bleibt jederzeit erreichbar
- technische Funktionen werden nachgelagert
- primäre und sekundäre Aktionen sind klar getrennt

Übertragung in VideoBatch Fast:

- Startseite und Produktionsarbeitsbereich sind getrennte Registerseiten
- Startseite entspricht der Vorlage
- bestehende Produktionsfunktionen bleiben im Arbeitsbereich erhalten
- Hauptkacheln führen in vorbereitete Workflows
- freie Erweiterungsflächen bleiben sichtbar und registriert

## 7. Header-Erweiterung

Zusätzlich zur Vorlage wurden die ausdrücklich gewünschten Funktionen integriert:

- Projektname
- kleiner Schnellspeicher für Entwicklerinformationen
- atomisches Speichern in einer festen Projektdatei
- Datum und Uhrzeit
- vollständige Monatsansicht
- jeder Tag einzeln anklickbar
- sechs Markierungszustände:
  - neutral
  - Erfolg
  - Warnung
  - Fehler
  - Information
  - aktiv

Der Kalender verwendet eine kompakte Canvas-Darstellung. Dadurch bleibt die Monatsansicht auch bei 1280 × 720 vollständig sichtbar.

## 8. Responsive Strategie

Getestete Referenzszenarien:

- 1280 × 720 bei 100 %
- 1366 × 768 bei 100 %
- 1920 × 1080 bei 100 %
- 1920 × 1080 bei 140 %

Strategie:

- Startdashboard und Produktionsbereich sind getrennt
- das Dashboard bleibt auf kleinen Anzeigen vollständig sichtbar
- der Kalender besitzt eine feste kompakte Höhe
- Hauptkacheln verwenden gleichgewichtete Spalten
- Assistent und Tipps skalieren proportional
- technische Produktionslisten belasten die Startseite nicht

## 9. Erweiterungs- und Pluginfähigkeit

Alle neuen Bereiche sind über Registries beschrieben:

- `registries/UI_BLUEPRINT.json`
- `registries/UI_COMPONENT_REGISTRY.json`
- `registries/VISUAL_REGRESSION_REGISTRY.json`
- `registries/PLUGIN_TRUST_REGISTRY.json`

Freie Erweiterungsflächen sind für folgende Bausteine vorbereitet:

- Assistenten-Widgets
- Plugin-Karten
- Recovery-Hinweise
- Statusbausteine
- Tutorialkarten
- zusätzliche Prüfungen

## 10. Freigaberegel

Eine sichtbare Änderung ist nur freigegeben, wenn:

1. Pflichttexte vorhanden sind,
2. keine sichtbaren Widgets das Fenster verlassen,
3. alle vier semantischen Kachelfarben vorhanden sind,
4. die Bildabweichung innerhalb der registrierten Grenzen bleibt,
5. eine beabsichtigte neue Referenz ausdrücklich bestätigt wurde.

Referenzbilder werden niemals automatisch ersetzt.
