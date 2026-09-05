# VideoBatch Fast 2.8.3-rc24 – hier beginnen

## Ziel

Diese Anleitung führt ohne Vorwissen vom entpackten Projektpaket bis zum ersten geprüften Testvideo.

## Pflichtgrad

- **Pflicht:** Projekt entpacken, Starter ausführen, Quellen und Ausgabeordner prüfen.
- **Empfohlen:** Erstes Video mit Kopien der Medien erstellen.
- **Optional:** Vorschau-Cache und erweiterte Einstellungen verwenden.

## Voraussetzungen

- Kubuntu oder Ubuntu 22.04 beziehungsweise 24.04
- ein normaler Benutzerzugang ohne Rootbetrieb
- ein vollständig entpacktes VideoBatch-Projektpaket
- mindestens eine Audio- und eine Bild- oder Videodatei
- ein beschreibbarer Ausgabeordner

## Sicherung und Rückweg

Für den ersten Test Kopien der Medien verwenden. VideoBatch verändert Originalquellen nicht, aber eine zusätzliche Kopie schützt vor Bedienfehlern außerhalb der Anwendung.

## 30-Sekunden-Check vor dem Programmstart

Spätestens direkt vor Schritt 4 müssen diese vier Punkte stimmen:

- [ ] Projekt vollständig entpackt – nicht direkt aus dem ZIP gestartet.
- [ ] Terminal befindet sich im entpackten Projektordner.
- [ ] Mindestens eine Audio- und eine Bild- oder Videodatei liegt bereit.
- [ ] Ein eigener beschreibbarer Ausgabeordner ist vorbereitet; ausgewählt wird er später in Schritt 7.

**Sicherheitsregel beim Start:** Erscheint eine rote Meldung, nicht blind erneut starten, sondern zuerst die Ursache lesen.

**So verwenden:** Jetzt mit Schritt 1 beginnen. Direkt vor Schritt 4 die vier Punkte kurz abgleichen; fehlt dann ein Punkt, zuerst genau diesen korrigieren.

## Schritt-für-Schritt-Anleitung

### Schritt 1: Projektpaket entpacken

**Aktion:** Das ZIP in einen neuen Ordner entpacken. Nicht direkt aus dem ZIP starten.

**Warum notwendig?** VideoBatch muss Einstellungen, Protokolle und temporäre Zustände schreiben können.

**Kann entfallen?** Nein. Ein Start direkt aus dem Archiv ist nicht zuverlässig.

**Erwartetes Ergebnis:** Im Ordner sind `videobatch.sh`, `README.md`, `src`, `scripts` und diese Anleitung sichtbar.

### Schritt 2: Terminal im Projektordner öffnen

**Aktion:** Den entpackten Ordner im Dateimanager öffnen und dort ein Terminal starten.

**Erwartetes Ergebnis:** Das Terminal befindet sich im VideoBatch-Projektordner.

### Schritt 3: Optional – Starter direkt ausführbar machen

```bash
chmod +x videobatch.sh
```

**Warum notwendig?** Linux benötigt die Ausführungsberechtigung für einen direkten Skriptstart mit `./videobatch.sh`.

**Kann entfallen?** Ja. Wenn die Dateiberechtigung nicht geändert werden soll, in Schritt 4 die dort gezeigte Bash-Alternative verwenden.

### Schritt 4: VideoBatch starten

Direkter Start bei ausführbarer Datei:

```bash
./videobatch.sh
```

Alternativ ohne Änderung der Dateiberechtigung:

```bash
bash ./videobatch.sh
```

Beide Varianten verwenden denselben zentralen Starter und umgehen keine Vorprüfung.

**Warum notwendig?** Der Starter prüft Laufzeit, FFmpeg, Projektzustand und benötigte Benutzerordner, bevor die Oberfläche geöffnet wird.

**Kann entfallen?** Nein. Den Starter nicht durch einen direkten Modulaufruf umgehen.

**Erwartetes Ergebnis:** Die VideoBatch-Oberfläche öffnet sich ohne rote Startmeldung.

**Bei einem Fehler:** Nicht mit `sudo`, `chmod -R 777` oder rekursiven Besitzänderungen reagieren. Die vollständige Meldung lesen und direkt [`ERROR_HANDLING.md` – Protokolle für eine Fehlermeldung sammeln](ERROR_HANDLING.md#protokolle-für-eine-fehlermeldung-sammeln) verwenden.

### Schritt 5: Audiodatei hinzufügen

1. `Audiodateien hinzufügen` wählen.
2. Eine Datei markieren.
3. Auswahl bestätigen.

**Erwartetes Ergebnis:** Die Audioanzahl im Header oder in der Medien-KPI steigt.

### Schritt 6: Bild oder Video hinzufügen

1. `Bilder hinzufügen` oder `Videos hinzufügen` wählen.
2. Eine Datei markieren.
3. Auswahl bestätigen.

**Erwartetes Ergebnis:** Die Medienanzahl steigt und die Vorschau zeigt die zuletzt aktiv gewählte Quelle.

### Schritt 7: Automatik und Ausgabeordner prüfen

1. Beim ersten Test den automatischen Modus verwenden.
2. Einen eigenen beschreibbaren Ausgabeordner auswählen.
3. Die angezeigten Quellenzahlen kontrollieren.

**Warum notwendig?** Ein falscher oder nicht beschreibbarer Zielordner verhindert eine sichere Ausgabe.

**Kann entfallen?** Der manuelle Modus kann entfallen; die Zielordnerprüfung nicht.

**Erwartetes Ergebnis:** Automatikmodus ist aktiv, der gewählte Ausgabeordner ist beschreibbar und die angezeigten Quellenzahlen entsprechen der Auswahl.

### Schritt 8: Testproduktion starten

1. `Automatisch prüfen und Videos erstellen` wählen.
2. Vorprüfung abwarten.
3. Queue-Status beobachten.
4. Abschlussmeldung abwarten.

**Erwartetes Ergebnis:** Der Auftrag endet ohne roten Fehler und die Ausgabedatei ist im gewählten Zielordner vorhanden.

### Schritt 9: Ergebnis prüfen

1. Video öffnen.
2. Anfang, Mitte und Ende abspielen.
3. Bild, Ton und Dateiname kontrollieren.

**Warum notwendig?** Ein technisch abgeschlossener Render garantiert noch nicht die gewünschte inhaltliche Wirkung.

**Kann entfallen?** Vor Veröffentlichung oder Archivierung: nein.

## Gelbe oder rote Meldungen

### Gelb

- Hinweis vollständig lesen.
- Genannten Wert prüfen.
- Empfohlene Aktion ausführen.
- Vorprüfung erneut starten.

Gelb bedeutet: Der Vorgang benötigt Aufmerksamkeit, ist aber nicht zwingend endgültig blockiert.

### Rot

- Nicht wiederholt blind auf Start klicken.
- Ursache und betroffenen Schritt lesen.
- Nur die angebotene sichere Lösung verwenden.
- Quellen, Ziel und Queue danach erneut prüfen.

Rot bedeutet: Der betroffene Vorgang wurde zum Schutz gestoppt. Originalmedien und gespeicherte Projekte bleiben unverändert.

Wenn die Ursache nicht direkt lösbar ist, führt [`ERROR_HANDLING.md` – Protokolle für eine Fehlermeldung sammeln](ERROR_HANDLING.md#protokolle-für-eine-fehlermeldung-sammeln) direkt zu den Angaben, die für eine sichere Diagnose benötigt werden.

## Mehrere Auswahlrunden

1. Im Medienbrowser Dateien markieren.
2. `Auswahl übernehmen + im Ordner bleiben` wählen.
3. Weitere Dateien oder Ordner ergänzen.
4. Erst mit `Fertig` die Sammlung in das Projekt übernehmen.

**Kann entfallen?** Ja. Bei Quellen aus einem einzigen Ordner genügt eine Auswahlrunde.

## Vorschau-Cache

Der Dialog `Vorschau-Cache` zeigt Anzahl, Größe, Auslastung, Pfad und letzte Bereinigung.

`Vorschau-Cache leeren` entfernt ausschließlich eindeutig erkannte VideoBatch-Vorschaudateien und veraltete eigene Teildateien. Originalmedien, Projekte und fremde Dateien bleiben unberührt.

**Kann die Leerung entfallen?** Ja. Sie ist nur bei Platzmangel, Diagnose oder beschädigten Vorschauen nötig.

## Heruntergeladenes Projekt-ZIP prüfen

### Schritt 1: Gesamtes ZIP prüfen

Im Ordner mit ZIP und `.sha256`-Datei:

```bash
sha256sum --check *.zip.sha256
```

**Erwartetes Ergebnis:** `OK`.

**Bei einem Fehler:** Archiv nicht starten. Erneut aus dem zugehörigen grünen GitHub-Actions-Lauf herunterladen.

### Schritt 2: Jeden ZIP-Eintrag prüfen

```bash
python3 scripts/build_artifact_contents.py \
  PROVOWARE_VIDEO_AUTOMATION_2026_*_verified.zip \
  --check ARTIFACT_CONTENTS.json
```

**Erwartetes Ergebnis:**

```text
ARTIFACT-CONTENTS BESTANDEN · <Dateizahl> Dateien · <Bytes> Bytes
```

Exitcodes:

- `0`: ZIP und Inhaltsliste stimmen überein.
- `1`: Datei fehlt, ist zusätzlich vorhanden oder weicht bei Größe, SHA-256 oder Metadaten ab.
- `2`: ZIP oder Inhaltsliste ist beschädigt beziehungsweise strukturell ungültig.

Die Prüfung extrahiert und startet keine Datei.

## Abschlussprüfung

- Oberfläche startet
- Audio und Medien werden gezählt
- Ausgabeordner ist beschreibbar
- Queue endet erfolgreich
- Ausgabedatei ist vorhanden
- Anfang, Mitte und Ende wurden geprüft
- Originalquellen sind unverändert

## Nächster Schritt

Für die vollständige Bedienung [`docs/BENUTZERHANDBUCH.md`](docs/BENUTZERHANDBUCH.md) öffnen. Für Installation [`AUTOINSTALLATION_save_.md`](AUTOINSTALLATION_save_.md), für Fehler [`ERROR_HANDLING.md`](ERROR_HANDLING.md) und für die Dokumentationsübersicht [`docs/DOKUMENTATIONSINDEX.md`](docs/DOKUMENTATIONSINDEX.md) verwenden.
