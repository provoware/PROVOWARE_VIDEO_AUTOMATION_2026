# VideoBatch-Update-System

## Ziel

Diese Anleitung erklärt den sicheren Updateablauf mit signiertem Channel-Verzeichnis, A/B-Slots, atomarem Wechsel und automatischem Rückfall.

## Pflichtgrad

- **Pflicht:** Signatur- und Hashprüfung, Aufbau im inaktiven Slot, Selbsttest, erster Start und Abschlussprüfung.
- **Empfohlen:** Projekte und individuelle Konfigurationen vor einem größeren Update zusätzlich sichern.
- **Optional:** Offline-Update über eine ausdrücklich gewählte lokale Quelle.

## Vor dem Update

### Schritt 1: Laufende Arbeiten abschließen

**Aktion:** Laufende Renderaufträge beenden oder kontrolliert stoppen und das Projekt speichern.

**Warum notwendig?** Ein Update während einer laufenden Produktion kann offene Zustände schwer nachvollziehbar machen.

**Kann entfallen?** Nein.

### Schritt 2: Updatekanal prüfen

**Aktion:** Kontrollieren, ob `stable` oder `rc` ausgewählt ist.

**Warum notwendig?** Der RC-Kanal kann neue Funktionen enthalten, ist aber nicht als Stable freigegeben.

**Kann entfallen?** Nein. Ein unbeabsichtigter Kanalwechsel kann eine andere Version installieren als erwartet.

### Schritt 3: Sicherung prüfen

**Aktion:** Bei wichtigen Projekten Projektdatei, Medienliste und individuelle Einstellungen sichern.

**Warum notwendig?** Das A/B-System schützt die Anwendung, ersetzt aber keine Projektsicherung.

**Kann entfallen?** Ja, wenn keine wichtigen lokalen Zustände vorhanden sind. Empfohlen bleibt die Sicherung trotzdem.

## Signiertes Channel-Verzeichnis

`channel-index.json` wird mit Ed25519 signiert. Für `stable` und `rc` enthält es unter anderem:

- Version und monotone Releasefolge
- Mindest-Installer-Schema
- Mindest-Ausgangsversion
- Manifest-URL, Größe und SHA-256
- Update-Reihenfolge
- Komponenten-Hashes und Downloadgrößen

Remotequellen werden ausschließlich über HTTPS akzeptiert. Lokale `file://`-Quellen sind nur für bewusst gewählte Offline- und CI-Prüfungen zulässig.

## Schritt-für-Schritt-Update

### Schritt 1: Channel-Index laden und prüfen

**Automatisch erledigt.**

Signatur, Struktur, Kanal und Mindestversion werden geprüft.

**Warum notwendig?** Ein manipuliertes oder für die Installation ungeeignetes Update muss vor jedem Download blockiert werden.

**Kann entfallen?** Nein.

### Schritt 2: Signiertes Release-Manifest prüfen

**Automatisch erledigt.**

Manifestgröße, SHA-256 und Signatur werden gegen den Channel-Index geprüft.

**Kann entfallen?** Nein.

### Schritt 3: Komponenten vergleichen

**Automatisch erledigt.**

VideoBatch vergleicht installierte Komponenten-Hashes mit dem neuen Manifest.

**Warum notwendig?** Dadurch werden nur tatsächlich geänderte Komponenten geladen.

**Kann entfallen?** Ja, technisch wäre ein vollständiger Download möglich. Er wäre jedoch unnötig größer und langsamer.

### Schritt 4: Inaktiven Slot vorbereiten

**Automatisch erledigt.**

Der bestätigte aktive Slot bleibt unverändert. Der inaktive Slot wird aus dem bestätigten Stand geklont und erhält ausschließlich vollständig ersetzte geänderte Komponenten.

**Warum notwendig?** Mischzustände innerhalb einer Komponente und Schäden am aktiven Stand werden verhindert.

**Kann entfallen?** Nein, wenn ein sicherer Rückfall erhalten bleiben soll.

### Schritt 5: Kandidaten vollständig prüfen

Geprüft werden:

1. jede Datei gegen das signierte Release-Manifest;
2. jeder vollständige Komponentenbaum;
3. das Portable-Vollmanifest;
4. Runtime und FFmpeg;
5. grundlegende Medienverarbeitung;
6. Startfähigkeit der Benutzeroberfläche.

**Kann entfallen?** Nein.

### Schritt 6: Transaktion dauerhaft vormerken

Vor dem Wechsel wird `pending_transaction.json` dauerhaft geschrieben.

**Warum notwendig?** Nach Stromausfall oder Absturz ist eindeutig erkennbar, ob ein Wechsel vorbereitet oder bereits durchgeführt wurde.

**Kann entfallen?** Nein.

### Schritt 7: `current` atomar umschalten

**Automatisch erledigt.**

Der relative `current`-Link wird in einem atomaren Schritt auf den geprüften Slot gesetzt.

**Warum notwendig?** Es darf keinen Zwischenzustand geben, in dem Teile beider Versionen aktiv sind.

**Kann entfallen?** Nein.

### Schritt 8: Ersten echten Start überwachen

VideoBatch wird bis zur bestätigten UI-Bereitschaft gestartet.

**Erwartetes Ergebnis:** Oberfläche öffnet sich und der neue Slot wird bestätigt.

**Bei einem Fehler:** Automatischer Rückfall auf den zuvor bestätigten Slot.

### Schritt 9: Aktiven Slot abschließend prüfen

Nach erfolgreichem Start wird der tatsächlich aktive Slot unabhängig geprüft.

**Warum notwendig?** Der vorbereitete Kandidat und der aktiv verwendete Zustand müssen identisch sein.

**Kann entfallen?** Nein.

## Verhalten nach Stromausfall

### Alter Slot ist weiterhin aktiv

Der vorbereitete Wechsel wird verworfen. Der alte bestätigte Stand bleibt aktiv.

### Neuer Slot ist bereits aktiv

Der erste Start wird überwacht. Scheitert er, wird `current` atomar auf den bestätigten alten Slot zurückgesetzt.

## Downloadökonomie

Zuerst werden nur Channel-Index und Manifest geladen. Danach lädt VideoBatch ausschließlich geänderte vollständige Komponenten.

**Warum vollständige Komponenten statt einzelner Dateien?** Dadurch entstehen innerhalb einer Komponente keine ungetesteten Mischstände.

**Kann der vollständige Projekt-ZIP-Weg weggelassen werden?** Vor Stable nein. Bis zur Stable-Freigabe bleibt das vollständige Projekt-ZIP der sichere Hauptweg; Teil- und Onlineupdates sind ein kontrollierter Nachrelease-Mechanismus.

## Manuelles Offline-Update

1. Updatepaket und Prüfsummen aus einer verifizierten Quelle beziehen.
2. Paket nicht direkt ausführen.
3. Signatur und SHA-256 prüfen.
4. Lokale Quelle ausdrücklich auswählen.
5. Normalen A/B-Prüfablauf durchführen lassen.
6. Ersten Start und Rückfallfähigkeit bestätigen.

## Was nicht getan werden darf

- Dateien direkt im aktiven Slot ersetzen
- `current` manuell während eines Updates umbiegen
- Signatur- oder Hashfehler ignorieren
- Update mit Rootrechten erzwingen
- unvollständige Komponenten mischen
- alten Slot vor erfolgreicher Abschlussprüfung löschen

## Technische Folgeentwicklungen

Die typisierte Ereignisarchitektur, Auswahlvorschau und das Ereignisregister ändern den signierten Channel-, A/B- und Rollbackvertrag nicht. Sie verbessern interne Zustandsübertragung und Vollständigkeitsprüfung, ersetzen aber keinen der oben beschriebenen Update-Sicherheitschecks.

## Abschlussprüfung

- richtiger Kanal ausgewählt
- Signaturen und SHA-256 bestanden
- inaktiver Slot vollständig aufgebaut
- Kandidatenprüfung bestanden
- `pending_transaction.json` korrekt verarbeitet
- atomarer Wechsel erfolgt
- Oberfläche gestartet
- aktiver Slot nachgeprüft
- alter Slot als Rückfall verfügbar
- Projekte und Originalmedien unverändert

## Nächster Schritt

Nach einem erfolgreichen Update `RELEASE_NOTES_save_.md` lesen und anschließend einen kleinen Testauftrag nach `START_HIER_save_.md` ausführen.
