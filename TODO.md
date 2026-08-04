# TODO 2.8.3-rc24

## Arbeitsprinzip für Folge-Iterationen

- [x] Vor jeder Änderung Ziel, Datei, Block, Patchgrund, Risiko und bewusste Nicht-Änderungen dokumentieren.
- [x] Danach nur den kleinsten sinnvollen Patch anwenden.
- [x] Am Ende nur betroffene Syntax-, Logik-, Ausgabe- und Testpfade validieren.
- [ ] Stable-Gates erst nach unverändertem Kandidaten in der dokumentierten Reihenfolge ausführen.

## Aktuelle Folge-Iteration · Cache-Diagnose und Schlüssel-Sperre

- [x] `FAIL_MEMORY_PASS.md` und `preview_service.py` zuerst eingelesen.
- [x] Cachegrenze von 256 MiB auf 1 GiB erhöht; Dateigrenze von 2.000 beibehalten.
- [x] Statusfunktion für Größe, Anzahl, Grenzwerte, Auslastung, Pfad und letzten Bereinigungslauf ergänzt.
- [x] kleine Bedienoberfläche direkt in die Bilder-/Videoauswahl integriert.
- [x] bestätigungspflichtige sichere Leerung nur eigener VideoBatch-Vorschaudateien ergänzt.
- [x] fremde PNGs und andere Dateien von Bereinigung und Leerung ausgeschlossen.
- [x] pro Cache-Schlüssel arbeitende Thread-/Kubuntu-Prozesssperre ergänzt.
- [x] atomare Teil-Datei- und `os.replace`-Speicherung unverändert beibehalten.
- [x] fokussierte Tests für Status, 1 GiB, Fremddateischutz, Leerung und Parallelität ergänzt.
- [ ] PR-#46-Kompatibilitätsmatrix vollständig grün abschließen.

## Frühere Folge-Iteration · Dokumentations- und Bedienstandard abgeschlossen

- [x] `PROJEKTORDNERSTRUKTUR.md` mit Ordnerübersicht, Laienanleitung, Funktionsübersicht und Abhängigkeitsbewertung ergänzt.
- [x] Hilfezentrum-Texte zu Einsteigerverständlichkeit, Systemstatus und sicheren Alternativen vereinheitlicht.
- [x] Startfeedback mit klarerem Hinweis auf Hilfetexte und sichere Standardpfade verbessert.
- [x] README, UPDATE_SYSTEM und CHANGELOG für diese gezielte Dokumentationsiteration aktualisiert.

## Frühere Folge-Iteration · abgeschlossen

- [x] Hilfezentrum um einen klaren Sicherheits-Tipp für gelbe und rote Hinweise ergänzt.
- [x] Startdialog mit konkreterem Wartetext, Fehlerhinweis und größerem Fenster verbessert.
- [x] Systemstatus im Hilfezentrum optisch besser als eigener Hinweisblock lesbar gemacht.
- [x] Relevante Syntax- und Textkatalogprüfung abgeschlossen.

## Aktuelle RC24-Iteration · abgeschlossen

- [x] zentrale Fehlerauflösung gegen beschädigte Registerdaten absichern
- [x] Schweregrad im Lösungsdialog einheitlich und verständlich anzeigen
- [x] zweiten Absturzpfad in der bereits ausgewählten Bilderliste identifizieren
- [x] parallele Vorschauprozesse eliminieren
- [x] Auswahlereignisse entprellen
- [x] veraltete Ergebnisse sicher verwerfen
- [x] Bilddekodierung vor Tk validieren
- [x] interaktive technische Dateiprüfung anbinden
- [x] reale Klick-Stressprüfung durchführen
- [x] GUI-Layoutvertrag auf Tabs und Scrollraster migrieren
- [x] vollständige Regression, Coverage und Visualprüfung ausführen
- [x] vollständiges Projekt reproduzierbar paketieren und frisch prüfen

## Entwicklungsablauf · nächste kleine Verbesserungen

- [ ] Patchprotokoll-Vorlage in `scripts/` ergänzen, ohne bestehende Gates umzubauen.
- [ ] Vor-/Nachvalidierung für gezielte Dateien als trockenlaufbares Hilfsskript prüfen.
- [ ] Wiederkehrende Tool-Ausgaben weiter auf einfache deutsche Begriffe vereinheitlichen.

## Startroutine, Abhängigkeiten und Rechte · nächste kleine Verbesserungen

- [ ] Startbericht in der Oberfläche als eigener Diagnose-Dialog nutzbar machen.
- [ ] Fehlende optionale Werkzeuge mit Installationshinweis pro Distribution ergänzen.
- [ ] Berechtigungskonflikte für externe Ausgabelaufwerke mit Schreibtest und Nutzerwahl vertiefen.

## Visuelle Unterstützung und Flexibilität · nächste kleine Verbesserungen

- [ ] Aktive Arbeitsbereiche in allen Tabs mit einheitlichem Status-Badge markieren.
- [ ] Lange Operationen mit gleicher Fortschritts- und Abbruchsprache anzeigen.
- [ ] Optionale Komfortfunktionen weiterhin deaktivierbar halten und sicher zurückfallen lassen.

## Vor Stable offen

- [ ] Ruff, MyPy, Bandit und pip-audit real ausführen
- [ ] physische KDE-X11-/Wayland-Abnahme
- [ ] Langzeitrender mit großer Medienauswahl und langsamem externem Ziel
