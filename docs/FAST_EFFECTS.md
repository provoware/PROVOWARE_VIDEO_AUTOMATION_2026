# Fast-Effect-Engine 2.2

## Ziel

Visuelle Effekte sollen die direkte, robuste FFmpeg-Pipeline nicht in eine komplexe Mehrstufenproduktion verwandeln. Jeder Automatikmodus ist deshalb als fester, geprüfter Einpass-Vertrag definiert.

## Verarbeitungswege

1. **Direktkopie**: kein Effekt, keine Skalierung, kompatibles Video. Der Videostream wird ohne Qualitätsverlust kopiert.
2. **Schneller Einpass-Render**: Effekt, Übergang und optionale Skalierung werden in genau einer `-vf`-Filterkette berechnet.
3. **Sicherer Fallback**: Schlägt ein Automatik-Look fehl, wird genau einmal der Modus **Maximale Geschwindigkeit** versucht.
4. **Ergebnisprüfung**: FFprobe bestätigt Video, Audio und plausible Dauer vor der Erfolgsmeldung.

## Unterstützte schnelle Bildoperationen

- `eq` für Kontrast, Helligkeit und Sättigung
- `hue` für Schwarzweiß und statische Farbverschiebung
- `unsharp` für begrenzte Schärfung
- `vignette` für leichte Randabdunklung
- `colorbalance` für kalte oder rote Farbakzente
- `fade` für kurze schwarze oder weiße Impulse

Alle Filter stammen aus der regulären FFmpeg-Filterkette. Es werden keine Zwischenvideos erzeugt.

## Geschwindigkeitsregeln

- genau ein FFmpeg-Durchgang pro Versuch
- kein Zwei-Pass-Encoding
- keine temporären Effektvideos
- keine optische Flussberechnung
- keine aufwendige Beat-Analyse
- keine temporalen Mehrbildfilter
- keine automatische Qualitätsreduzierung
- alle Filter in einer gemeinsamen Filterkette
- maximal ein automatischer Fallback

## Sicherheitsgrenze für Lichtimpulse

Der Modus **Strobe Safe** verwendet nur eine sehr geringe Helligkeitsänderung. Starkes Vollbildblitzen und harte schnelle Weißwechsel sind bewusst nicht Bestandteil des Standardmodus. Nutzer mit Lichtempfindlichkeit sollten dennoch einen Modus ohne Puls wählen.

## Wichtige technische Grenze

Jeder Pixel-Effekt verhindert die verlustfreie Videodirektkopie. Der größte Zeitunterschied entsteht daher nicht durch den einzelnen leichten Filter, sondern durch die notwendige Neucodierung. Der Modus **Automatisch schnell** erhält bei kompatiblen Videos die Direktkopie und wendet den schnellen Look nur dort an, wo ohnehin codiert werden muss.
