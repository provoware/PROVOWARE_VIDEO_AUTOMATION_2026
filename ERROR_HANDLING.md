# VideoBatch-Fehlerbehebung

## Ziel

Diese Anleitung erklärt, wie Meldungen sicher eingeordnet, behoben und abschließend geprüft werden. Sie richtet sich ausdrücklich auch an Nutzer ohne Linux- oder Entwicklerkenntnisse.

## Pflichtgrad

Bei blockierenden Fehlern ist diese Anleitung verpflichtend. Bei Warnungen ist sie empfohlen.

## Voraussetzungen

Die vollständige Meldung und der betroffene Projekt- oder Ausgabepfad müssen noch sichtbar oder im lokalen Diagnosebericht vorhanden sein.

## Grundregel

Jeder VideoBatch-Fehler soll fünf Fragen beantworten:

1. Was ist passiert?
2. Welche Auswirkung hat das?
3. Was hat VideoBatch automatisch zum Schutz getan?
4. Welche sichere Lösung wird empfohlen?
5. Welche Alternative bleibt, wenn die empfohlene Lösung nicht möglich ist?

## Meldungsarten

### Hinweis

Ein Hinweis informiert über einen Zustand, blockiert den Vorgang aber normalerweise nicht.

**Vorgehen:** Text lesen, genannten Wert kontrollieren und anschließend normal fortfahren.

**Kann ignoriert werden?** Nur wenn ausdrücklich angegeben wird, dass keine Handlung erforderlich ist.

### Warnung

Eine Warnung bedeutet, dass der Vorgang möglich sein kann, aber ein Risiko, eine unvollständige Angabe oder eine Abweichung vorliegt.

**Vorgehen:** Warnung nicht wegklicken, ohne den genannten Punkt zu prüfen.

**Kann ignoriert werden?** Manchmal, aber nur wenn VideoBatch eine sichere Fortsetzung ausdrücklich anbietet und die Folge verständlich erklärt.

### Vorgang gestoppt

Der betroffene Schritt wurde blockiert, damit keine unvollständige, unsichere oder nicht reproduzierbare Ausgabe entsteht.

**Vorgehen:** Nicht wiederholt blind starten. Erst Ursache beheben, danach Vorprüfung erneut ausführen.

**Kann ignoriert werden?** Nein.

## Schritt-für-Schritt-Anleitung

### Schritt 1: Meldung vollständig lesen

**Pflichtgrad:** Pflicht.

**Aktion:** Überschrift, Ursache, betroffenen Schritt und angebotene Aktion lesen.

**Warum notwendig?** Gleiche sichtbare Symptome können unterschiedliche Ursachen haben.

**Kann entfallen?** Nein.

### Schritt 2: Originalzustand schützen

**Aktion:** Keine Quelldatei löschen, verschieben oder überschreiben. Keine pauschalen Rechteänderungen ausführen.

**Warum notwendig?** Die Diagnose soll den Fehler beheben, ohne weitere Zustände zu verändern.

**Kann entfallen?** Nein.

### Schritt 3: Angebotene sichere Aktion verwenden

Beispiele:

- anderen Ausgabeordner wählen
- fehlende Referenzen entfernen
- Quelle erneut auswählen
- Wiederanlaufquellen laden
- sichere Automatik für Effekte wiederherstellen
- Protokolle öffnen

**Warum notwendig?** Diese Aktionen sind auf den konkreten Fehler begrenzt und verändern keine fremden Dateien.

**Kann entfallen?** Ja, wenn die Ursache stattdessen bewusst manuell behoben wird.

### Schritt 4: Betroffenen Bereich erneut prüfen

**Aktion:** Medien, Queue, Effekt oder Zielpfad erneut öffnen und den korrigierten Zustand kontrollieren.

**Warum notwendig?** Eine ausgeführte Aktion beweist noch nicht, dass alle Voraussetzungen wieder erfüllt sind.

**Kann entfallen?** Nein.

### Schritt 5: Vorprüfung wiederholen

**Aktion:** Auftrag erneut prüfen, aber noch nicht mehrfach hintereinander starten.

**Erwartetes Ergebnis:** Die ursprüngliche Warnung oder Blockierung tritt nicht erneut auf.

### Schritt 6: Kleinen Test ausführen

Bei Änderungen an Medien, Effekten, Pfaden oder Laufzeit zuerst einen kleinen Testauftrag verwenden.

**Warum notwendig?** Dadurch wird die Korrektur mit geringem Zeit- und Datenrisiko bestätigt.

**Kann entfallen?** Bei unkritischen Hinweisen ja. Nach einem blockierenden Fehler wird der Test empfohlen.

## Häufige Fehlerfälle

### Fehlende Quelldatei

1. Genannten Pfad prüfen.
2. Datei an den ursprünglichen Ort zurücklegen oder erneut auswählen.
3. Alternativ `Fehlende Verweise entfernen` verwenden.
4. Medienliste kontrollieren.
5. Auftrag neu vorbereiten.

**Warum notwendig?** Ein Auftrag mit nicht erreichbarer Quelle ist nicht reproduzierbar.

### Ausgabeordner nicht beschreibbar

1. Ausgabeordner im Dialog prüfen.
2. Einen eigenen Benutzerordner wählen.
3. Schreibprobe erneut ausführen lassen.
4. Auftrag erst nach grüner Pfadprüfung starten.

**Nicht verwenden:** `sudo`, `chmod -R 777` oder rekursive Besitzänderungen.

### Queueauftrag fehlgeschlagen

1. Ursprüngliche Fehlermeldung öffnen.
2. Queueeintrag nicht löschen, solange die Ursache noch benötigt wird.
3. `Wiederanlaufquellen laden` verwenden, falls angeboten.
4. Quellen und Einstellungen kontrollieren.
5. Auftrag bewusst neu starten.

**Wichtig:** Das Laden der Quellen startet keinen Render automatisch.

### Ungültiger Effekt oder Übergang

1. Effektbereich öffnen.
2. Ursache lesen.
3. Gültigen Effekt wählen oder `Sichere Automatik wiederherstellen` verwenden.
4. Vorschau beziehungsweise Testauftrag ausführen.

### Diagnosebericht konnte nicht geschrieben werden

1. Anwendung geöffnet lassen.
2. Alternativen Logpfad wählen.
3. Schreibbarkeit des Benutzerordners prüfen.
4. Protokoll erneut exportieren.

Die Anwendung bleibt in diesem Fehlerfall grundsätzlich nutzbar.

## Schutzfälle für Plugins und visuelle Freigaben

- `PLUGIN_APPROVAL_EXPIRED`: Pluginidentität oder Berechtigungen haben sich geändert. Die Freigabe wird deaktiviert und muss vollständig neu geprüft werden.
- `PLUGIN_APPROVAL_REVOKED`: Die Freigabe wurde widerrufen. Eine erneute Vollprüfung ist erforderlich.
- `VISUAL_APPROVAL_MISSING`: Der Release Candidate bleibt prüfbar, eine Stable-Freigabe wird blockiert.
- `VISUAL_APPROVAL_EXPIRED`: Manifest, Referenzbilder oder Prüfbericht wurden nach der Freigabe geändert.
- `VISUAL_APPROVAL_INVALID`: Signatur oder Schlüsselmaterial ist ungültig.
- `DIAGNOSTIC_REPORT_WRITE_FAILED`: Der Bericht konnte nicht gespeichert werden; ein alternativer Logpfad wird angeboten.

## Wenn das Fehlerregister selbst fehlt oder beschädigt ist

VideoBatch zeigt eine vollständige sichere Standarderklärung und mindestens die Aktion `Protokolle öffnen`.

Unbekannte Schweregrade werden vorsorglich als blockierend behandelt.

**Warum notwendig?** Ein beschädigter Fehlerkatalog darf nicht dazu führen, dass ein unsicherer Vorgang stillschweigend fortgesetzt wird.

**Kann diese Vorsicht entfallen?** Nein.

## Grenzen der Selbstheilung

Automatische Selbstheilung darf:

- sichere Standardwerte wiederherstellen;
- fehlende Benutzerordner kontrolliert anlegen;
- ungültige optionale Einstellungen zurücksetzen;
- einen alternativen Log- oder Ausgabeordner anbieten.

Automatische Selbstheilung darf niemals:

- eine Sicherheitsfreigabe erfinden;
- eine widerrufene Pluginfreigabe reaktivieren;
- Originalmedien verändern;
- Rootrechte anfordern;
- einen fehlgeschlagenen Auftrag unbegrenzt wiederholen;
- einen Wiederanlauf automatisch starten.

## Protokolle für eine Fehlermeldung sammeln

1. Hilfe- oder Diagnosebereich öffnen.
2. Systemstatus anzeigen.
3. Protokollpfad öffnen oder Bericht exportieren.
4. Fehlerzeitpunkt, betroffenen Auftrag und letzte Handlung notieren.
5. Geheimnisse, private Pfade oder persönliche Mediennamen vor Weitergabe prüfen.

## Abschlussprüfung

Eine Fehlerbehebung ist erst abgeschlossen, wenn:

- die ursprüngliche Ursache nicht mehr besteht;
- der betroffene Bereich einen plausiblen Zustand zeigt;
- die Vorprüfung grün ist;
- ein kleiner Test erfolgreich war oder nachvollziehbar nicht nötig ist;
- Originalmedien unverändert sind;
- kein unbegrenzter Wiederholungsversuch läuft.

## Nächster Schritt

Bei Startproblemen `START_HIER_save_.md`, bei Bedienfragen `docs/BENUTZERHANDBUCH.md`, bei Installationsproblemen `AUTOINSTALLATION_save_.md` und bei Updateproblemen `UPDATE_SYSTEM.md` verwenden.
