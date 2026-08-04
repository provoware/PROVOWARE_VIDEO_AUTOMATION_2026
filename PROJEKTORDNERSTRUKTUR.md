# PROJEKTORDNERSTRUKTUR

Diese Übersicht beschreibt das Basisprojekt für Laien, Tester und Entwickler. Sie nennt nur die wichtigen Ordner und Dateien. Ziel ist: schnell verstehen, sicher starten, sicher prüfen und nichts versehentlich beschädigen.

## 1. Grundregeln des Projekts

- **Originaldateien bleiben geschützt.** VideoBatch löscht fehlende oder offline liegende Medien nicht automatisch.
- **Ausgabeordner werden vor dem Start geprüft.** Ein Ziel wird reserviert, bevor FFmpeg mit der Arbeit beginnt.
- **Ablagen erfolgen sicher.** Dateien werden erst nach Journal, Hashprüfung und Abschlussprüfung als fertig betrachtet.
- **Jeder Hintergrundvorgang endet eindeutig.** Es gibt genau ein klares Abschlussereignis: erfolgreich, gestoppt oder fehlgeschlagen.
- **Fehler werden einfach erklärt.** Jede Meldung soll Ursache, Auswirkung, Schutzmaßnahme, Lösung und Alternative nennen.
- **Stable-Gates bleiben ehrlich.** Nicht ausgeführte physische Tests oder Langzeitrender werden nicht als bestanden beschrieben.

## 2. Ordnerstruktur

```text
.
├── src/videobatch_fast/          # Programmlogik und Oberfläche
├── resources/texts/              # Deutsche UI-Texte und Hilfetexte
├── resources/themes/             # Farbschemata und Erscheinungsbild
├── resources/reference/          # Referenzbilder und Analysewerte für visuelle Prüfung
├── resources/signing/            # Öffentliche Signatur-Informationen, keine privaten Schlüssel
├── registries/                   # Prüfregister für UI, Qualität, Plugins, Updates und Szenarien
├── scripts/                      # Build-, Prüf- und Dokumentationshilfen
├── tests/                        # Automatisierte Tests
├── docs/                         # Vertiefende technische Dokumentation
├── toolchain_wheelhouse/         # Hinweise zur gesperrten Qualitäts-Werkzeugkette
├── visual_inspection/            # Dateien für visuelle Abnahmen
├── VERSION.json                  # einzige Quelle für Name, Version, Build und Kanal
├── DEVELOPMENT_STATUS.json       # freigegebener Status, Testzahlen und offene Stable-Gates
├── README.md                     # kurze Start- und Statusübersicht
├── STATUS.md                     # abgeleitete Statusdatei
├── TODO.md                       # nächste Aufgaben und offene Prüfungen
├── CHANGELOG.md                  # nachvollziehbare Änderungshistorie
├── UPDATE_SYSTEM.md              # Updateprinzipien und Nachrelease-System
├── requirements.txt              # Einstieg in exakt gesperrte Laufzeitabhängigkeiten
├── requirements.lock             # feste Laufzeitpakete
├── requirements-quality.lock     # feste Qualitätswerkzeuge
├── build_artifacts.sh            # schreibender Build-Schritt
├── test.sh                       # paketbezogene, schreibgeschützte Teststrecke
├── quality.sh                    # Qualitätsstrecke mit Ruff, MyPy, Bandit und pip-audit
├── STARTEN.sh                    # einfacher Start für Nutzer
└── start.sh / videobatch.sh      # technische Starthelfer
```

## 3. Wichtige Dateien in einfacher Sprache

| Datei oder Ordner | Wofür ist das? | Darf man es normalerweise ändern? |
| --- | --- | --- |
| `VERSION.json` | Enthält Produktname, Version, Build und Kanal. | Nur bei echter Release-Änderung. |
| `DEVELOPMENT_STATUS.json` | Enthält freigegebene Testzahlen und offene Stable-Gates. | Nur nach belegtem Statuswechsel. |
| `src/videobatch_fast/` | Enthält Python-Code für Start, UI, FFmpeg, Sicherheit und Plugins. | Ja, aber klein und gezielt. |
| `resources/texts/` | Enthält sichtbare Texte der Anwendung. | Ja, wenn Texte verständlicher werden. |
| `resources/themes/` | Enthält Farben und Erscheinungsbild. | Ja, wenn Kontrast und Lesbarkeit besser werden. |
| `registries/` | Enthält maschinenlesbare Prüfverträge. | Nur mit passender Prüfung. |
| `scripts/` | Enthält Helfer für Build, Prüfung und Dokumentation. | Ja, aber Build und Prüfung getrennt halten. |
| `tests/` | Enthält automatische Tests. | Ja, passend zur Codeänderung. |
| `docs/` | Enthält technische Nachweise und Detailkonzepte. | Ja, wenn Verhalten oder Ablauf erklärt werden muss. |

## 4. Was kann im Basisprojekt bereits mitgeliefert werden?

### Sinnvoll mitlieferbar

- **Python-Pakete aus dem Lockfile:** `Pillow` für Bildprüfung und `cryptography` für Signaturen sind bereits feste Laufzeitabhängigkeiten.
- **Qualitätswerkzeuge als Wheelhouse:** Ruff, MyPy, Bandit und pip-audit können offline vorbereitet werden, müssen aber exakt zum Lockfile passen.
- **Öffentliche Signaturschlüssel:** öffentliche Schlüssel dürfen mitgeliefert werden, private Schlüssel nicht.
- **Deutsche Textkataloge:** Hilfen, Statusmeldungen und Dialogtexte können direkt im Projekt liegen.
- **Themes und visuelle Referenzen:** Farbschemata und Referenzbilder helfen bei wiederholbarer Prüfung.
- **Desktop-Starter und Startskripte:** einfache Startdateien senken Einstiegshürden für Laien.

### Nicht direkt mitliefern oder nur bewusst gebündelt

- **Private Schlüssel:** niemals im Release.
- **System-FFmpeg ohne Lizenz- und Plattformprüfung:** FFmpeg ist systemabhängig. Ein gebündeltes FFmpeg ist nur sinnvoll, wenn Lizenz, Herkunft, Hash und Rauchtest dokumentiert sind.
- **Grafiksystem-Pakete wie Tk, X11, Wayland oder KDE:** diese gehören meist zur Linux-Distribution.
- **Ungeprüfte Plugins:** Plugins dürfen nur signiert, freigegeben und isoliert laufen.
- **Online-Installer als Pflichtweg:** vor Stable bleibt das vollständige Projekt-ZIP der sichere Hauptweg.

## 5. Laienanleitung: Start in kleinen Schritten

### Schritt 1: Projektordner öffnen

```bash
cd /pfad/zum/PROVOWARE_VIDEO_AUTOMATION_2026
```

Wenn der Ordner anders heißt, ersetze den Pfad durch deinen echten Ordner.

### Schritt 2: Anwendung starten

```bash
./STARTEN.sh
```

Falls Linux fragt, ob die Datei ausführbar sein darf:

```bash
chmod +x STARTEN.sh start.sh videobatch.sh
./STARTEN.sh
```

### Schritt 3: Dateien hinzufügen

1. Klicke auf **Audiodateien hinzufügen**.
2. Wähle eine oder mehrere Audiodateien.
3. Klicke auf **Bilder oder Videos hinzufügen**.
4. Wähle Bilder oder Videos.
5. Prüfe im Kopfbereich, ob die gezählten Dateien stimmen.

### Schritt 4: Vorschau prüfen

1. Klicke eine Datei an.
2. Prüfe, ob Bild, Video oder Audio erwartbar angezeigt wird.
3. Wenn etwas fehlt: Datenträger verbinden oder Datei bewusst neu auswählen.
4. Fehlende Dateien nicht im Dateimanager löschen, solange ein Projekt sie noch verwendet.

### Schritt 5: Schnellmodus wählen

1. Nutze zuerst den einfachen Schnellmodus.
2. Ändere nur Einstellungen, die du verstehst.
3. Wenn VideoBatch eine gelbe Meldung zeigt, lies den Hinweis vollständig.
4. Wenn VideoBatch eine rote Meldung zeigt, starte nicht blind neu, sondern nutze die vorgeschlagene Lösung.

### Schritt 6: Ausgabeordner wählen

1. Wähle einen Ordner in deinem Benutzerbereich, zum Beispiel `Videos`.
2. Vermeide Systemordner wie `/usr`, `/bin` oder fremde Benutzerordner.
3. Bei externen Laufwerken: erst anschließen, dann Schreibrechte prüfen lassen.

### Schritt 7: Produktion starten

```text
Schaltfläche: Automatisch prüfen und Videos erstellen
```

VideoBatch prüft Eingaben, Rechte, freien Speicher und FFmpeg. Erst danach startet die Erstellung.

### Schritt 8: Ergebnis prüfen

1. Warte auf die Abschlussmeldung.
2. Öffne den Ausgabeordner.
3. Spiele das Ergebnis kurz an.
4. Verschiebe Originaldateien erst, wenn du das Ergebnis geprüft hast.

## 6. Funktionsübersicht

- **Medienauswahl:** Audios, Bilder und Videos sammeln.
- **Vorschau:** zuletzt aktiv angeklickte Datei anzeigen oder vorhören.
- **Schnellmodus:** einfache Voreinstellungen für typische Videos.
- **Diashow:** Bilder automatisch passend zur Audiolänge verteilen.
- **Sortierung:** Reihenfolge sichtbar prüfen und bewusst übernehmen.
- **Ausgabeprüfung:** Schreibziel vor dem Start testen und reservieren.
- **Recovery:** unterbrochene Aufträge nachvollziehbar wieder anbieten.
- **Hilfezentrum:** Status, Protokolle, Schnellstart und Problemlösung an einer Stelle.
- **Plugin-Prüfung:** Erweiterungen nur mit Signatur, Freigabe und Isolation.
- **Update-System:** vorbereitetes A/B-Prinzip, aber vor Stable kein Pflicht-Onlineupdate.

## 7. Standards und Best Practices

### Bedienbarkeit für Laien

- Schaltflächen sagen, was passiert.
- Warnungen erklären Schutz und nächsten Schritt.
- Fachbegriffe werden vermieden oder kurz erklärt.
- Ein sicherer Standardpfad ist besser als eine freie, riskante Eingabe.

### Barrierefreiheit

- Texte müssen kontrastreich und groß genug lesbar sein.
- Status darf nicht nur über Farbe erklärt werden; Text wie „Bereit“, „Hinweis“ oder „Blockiert“ ist Pflicht.
- Lange Texte müssen scrollbar sein.
- Tastaturbedienung und klare Fokusreihenfolge bleiben wichtig.

### Codequalität

- Kleine Funktionen und kleine Dateien bevorzugen.
- Logik, Oberfläche, Konfiguration, Tests und Dokumentation trennen.
- Keine stillen Fehler: lieber sicher stoppen und klar erklären.
- Keine gefährlichen Shell-Aufrufe wie `shell=True`, `os.system` oder `tempfile.mktemp`.
- Schreibende Build-Schritte und lesende Prüfungen getrennt halten.

### Datenintegrität

- Nie automatisch löschen, nur weil ein Pfad fehlt.
- Vor dem Rendern Ausgabe reservieren.
- Nach dem Rendern Ergebnis prüfen.
- Erst nach erfolgreicher Prüfung archivieren oder aufräumen.

## 8. Zusammenfassung der Prinzipien

Dieses Projekt folgt einem vorsichtigen Grundsatz: **Sicherheit vor Tempo**. Eine laienfreundliche Anwendung darf nicht raten, wenn Dateien, Rechte oder Abhängigkeiten unklar sind. Sie soll erklären, schützen und sichere Alternativen anbieten. Abhängigkeiten können im Basisprojekt mit festen Hashes, öffentlichen Schlüsseln, Texten, Themes und Prüfwerkzeugen vorbereitet werden. Systemnahe Bestandteile wie FFmpeg, Display-Server und Desktop-Pakete brauchen dagegen eine klare Plattformprüfung. So bleibt VideoBatch nachvollziehbar, reparierbar, barrierearm und stabil.
