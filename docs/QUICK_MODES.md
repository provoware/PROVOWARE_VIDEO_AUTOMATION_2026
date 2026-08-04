# Automatische Schnellmodi

VideoBatch Fast 2.2.0-rc1 bietet 13 automatische Modi. Ein Modus ist keine lose Effektauswahl, sondern ein geprüftes Paket aus:

- visuellem Look,
- kurzer Ein- oder Ausblendung,
- schnellem Encoderprofil,
- Codec,
- Auflösung,
- Ergebnisprüfung,
- sicherem Fallback.

## Sicherheitsregeln

1. Pro Versuch wird nur ein FFmpeg-Durchgang verwendet.
2. Originaldateien werden nie verändert.
3. Kompatible Videos dürfen im Modus **Automatisch schnell** und **Maximale Geschwindigkeit** direkt kopiert werden.
4. Ein fehlgeschlagener Effektmodus erhält höchstens einen automatischen Fallback.
5. Der Fallback ist **Maximale Geschwindigkeit**.
6. Jede Ausgabe wird vor der Erfolgsmeldung mit FFprobe geprüft.
7. Starkes Vollbildstroboskop ist nicht enthalten. Der Modus **Strobe Safe** arbeitet nur mit sehr milder Helligkeitsänderung.
8. Keine Zwischenvideos und keine mehrstufigen Effektketten.

## Modi

1. **Automatisch schnell** – entscheidet pro Datei zwischen Direktkopie und schnellem Bild-Look.
2. **Maximale Geschwindigkeit** – keine Filter, Direktkopie wenn technisch möglich.
3. **Techno Clean** – klarer Kontrast und kurze weiche Blende.
4. **HardTechno Impact** – härterer Kontrast und kurzer White Flash.
5. **Industrial Dark** – dunkler, entsättigter Warehouse-Look.
6. **Acid Neon** – kräftige Neonfarbverschiebung.
7. **Bass Pulse** – sanft pulsierender Kontrast ohne Beat-Analyse.
8. **Strobe Safe** – milde, begrenzte Helligkeitsimpulse.
9. **Glitch Light** – leichter digitaler Farb- und Schärfeeindruck.
10. **Monochrome Rave** – kontrastreiches Schwarzweiß.
11. **Cold Warehouse** – kühler Blau-Stahl-Look.
12. **Red Alert** – warmer Rotakzent und kurzer White Flash.
13. **Sharp Stage** – dezente Schärfung für Cover und Typografie.

Der Expertenmodus **Eigene Feineinstellung** ist getrennt und nicht Teil der automatischen Sicherheitsgarantie.
