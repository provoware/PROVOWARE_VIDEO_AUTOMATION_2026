# VideoBatch Fast – Benutzerhandbuch

**Version:** 2.8.3-rc24  
**Zielgruppe:** Nutzer ohne technische Vorkenntnisse  
**Wichtig:** Dies ist ein Release Candidate. Für wichtige Projekte zuerst mit Kopien der Medien testen.

## Ziel

Mit VideoBatch Fast werden aus Audiodateien, Bildern und Videos automatisiert fertige Videos erzeugt. Dieses Handbuch führt vom ersten Start bis zur Ergebnisprüfung und erklärt bei jedem kritischen Schritt, warum er notwendig ist und ob er ausgelassen werden darf.

## Pflichtgrad

Empfohlen für die normale Bedienung; die Sicherheits- und Ergebnisprüfungsschritte sind vor Veröffentlichung verbindlich.

## Voraussetzungen

Projekt vollständig entpacken und Originalmedien sichern.

## 2. Vor dem ersten Start

### Schritt 1: Projektpaket vollständig entpacken

**Pflichtgrad:** Pflicht.

**Aktion:** Das heruntergeladene ZIP in einen neuen, eigenen Ordner entpacken. VideoBatch nicht direkt aus dem ZIP starten.

**Warum notwendig?** Im ZIP können Dateien nicht zuverlässig geschrieben, aktualisiert oder gesichert werden.

**Kann entfallen?** Nein. Ein Start direkt aus dem Archiv kann zu fehlenden Einstellungen, Protokollen oder Ausgaben führen.

**Erwartetes Ergebnis:** Im Zielordner sind unter anderem `videobatch.sh`, `START_HIER_save_.md`, `README.md`, `src` und `scripts` sichtbar.

### Schritt 2: Originalmedien sichern

**Pflichtgrad:** Empfohlen.

**Aktion:** Für den ersten Test Kopien der gewünschten Audio-, Bild- und Videodateien verwenden.

**Warum notwendig?** VideoBatch verändert Originalmedien nicht, aber ein Test mit Kopien schützt zusätzlich vor Bedienfehlern außerhalb der Anwendung.

**Kann entfallen?** Ja. Die Anwendung arbeitet grundsätzlich lesend mit den Quellen. Für unersetzliche Dateien wird die Sicherung trotzdem dringend empfohlen.

## 3. VideoBatch starten

### Schritt 1: Terminal im Projektordner öffnen

**Aktion:** Im Dateimanager den entpackten VideoBatch-Ordner öffnen. Dort ein Terminal öffnen.

**Erwartetes Ergebnis:** Die Terminalzeile zeigt den Projektordner als aktuellen Pfad.

### Schritt 2: Starter ausführbar machen

```bash
chmod +x videobatch.sh
```

**Pflichtgrad:** Beim ersten Start Pflicht, falls die Ausführungsberechtigung fehlt.

**Warum notwendig?** Linux startet Skripte nur direkt, wenn die Ausführungsberechtigung gesetzt ist.

**Kann entfallen?** Ja, wenn die Datei bereits ausführbar ist. Ein erneuter Aufruf ist unschädlich.

### Schritt 3: Anwendung starten

```bash
./videobatch.sh
```

**Erwartetes Ergebnis:** Die VideoBatch-Oberfläche öffnet sich. Der Starter prüft vorher Laufzeit, FFmpeg, Benutzerordner und Projektzustand.

**Bei einem Fehler:** Fehlermeldung vollständig lesen. Nicht mit `sudo`, `chmod 777` oder rekursiven Besitzänderungen improvisieren. Den Abschnitt „Fehler sicher beheben“ verwenden.

## Schritt-für-Schritt-Anleitung

Die folgenden Schritte führen vom Import bis zur Ergebnisprüfung.

## 4. Erstes Video erstellen

### Schritt 1: Audiodateien hinzufügen

**Aktion:** `Audiodateien hinzufügen` auswählen und mindestens eine unterstützte Audiodatei übernehmen.

**Warum notwendig?** Die meisten Produktionsmodi benötigen eine Tonquelle.

**Kann entfallen?** Nur in einem ausdrücklich tonlosen Modus. Andernfalls bleibt der Auftrag unvollständig.

**Erwartetes Ergebnis:** Die Audioanzahl im Header oder in der Medien-KPI steigt.

### Schritt 2: Bilder oder Videos hinzufügen

**Aktion:** `Bilder hinzufügen` oder `Videos hinzufügen` auswählen.

**Warum notwendig?** Ohne visuelle Quelle kann kein normales Video erzeugt werden.

**Kann entfallen?** Nein, außer ein spezieller Modus erzeugt das Bild vollständig selbst.

**Erwartetes Ergebnis:** Die Medienanzahl steigt und eine Vorschau wird angezeigt.

### Schritt 3: Vorschau kontrollieren

**Aktion:** Den zuletzt aktiv angeklickten Eintrag prüfen.

**Warum notwendig?** Die Vorschau zeigt, welche Quelle aktuell maßgeblich ausgewählt ist.

**Kann entfallen?** Technisch ja, aber dann können falsche Medien unbemerkt im Auftrag bleiben.

### Schritt 4: Modus wählen

**Aktion:** Einen Schnellmodus wählen oder die Automatik verwenden.

**Empfehlung:** Beim ersten Test die Automatik verwenden.

**Warum notwendig?** Der Modus bestimmt, wie Audio, Bilder, Videos, Übergänge und Effekte kombiniert werden.

**Kann entfallen?** Ja, wenn die Automatik aktiv ist. Dann wählt VideoBatch einen passenden Modus.

### Schritt 5: Ausgabeordner prüfen

**Aktion:** Einen eigenen beschreibbaren Zielordner auswählen.

**Warum notwendig?** Das fertige Video muss sicher gespeichert werden können.

**Kann entfallen?** Nein. Ohne beschreibbares Ziel darf die Produktion nicht starten.

**Erwartetes Ergebnis:** Die Pfadprüfung meldet den Ordner als nutzbar.

### Schritt 6: Produktion starten

**Aktion:** `Automatisch prüfen und Videos erstellen` oder den entsprechenden Startschalter verwenden.

**Warum notwendig?** Vor dem Rendern werden Quellen, Pfade, Modus und benötigte Werkzeuge geprüft.

**Kann entfallen?** Nein. Ein direkter Umgehungsstart ist nicht vorgesehen.

**Erwartetes Ergebnis:** Der Auftrag erscheint in der Queue und erhält einen nachvollziehbaren Status.

### Schritt 7: Abschluss abwarten

**Aktion:** Anwendung während des Renderns geöffnet lassen und keine Quelldateien verschieben oder löschen.

**Warum notwendig?** Verschobene Quellen können einen laufenden Auftrag unterbrechen.

**Kann entfallen?** Nein, sofern der Auftrag nicht ausdrücklich pausiert oder abgebrochen wird.

### Schritt 8: Ergebnis prüfen

**Aktion:** Das fertige Video vollständig oder mindestens Anfang, Mitte und Ende abspielen.

**Warum notwendig?** Ein technisch abgeschlossener Render ersetzt keine inhaltliche Sicht- und Hörprüfung.

**Kann entfallen?** Für unwichtige Tests ja. Vor Veröffentlichung oder Archivierung nein.

## 5. Mehrere Auswahlrunden

1. Im Medienbrowser Dateien markieren.
2. `Auswahl übernehmen + im Ordner bleiben` wählen.
3. Weitere Dateien oder Ordner ergänzen.
4. Erst mit `Fertig` die Gesamtauswahl in das Projekt übernehmen.

**Warum notwendig?** Dadurch können Quellen aus mehreren Ordnern gesammelt werden, ohne den Browser jedes Mal neu zu öffnen.

**Kann entfallen?** Ja. Bei Quellen aus nur einem Ordner genügt eine Auswahlrunde.

## 6. Vorschau-Cache

Der Vorschau-Cache speichert nur von VideoBatch erzeugte Vorschaubilder im Benutzer-Cache.

### Cache prüfen

1. Medienauswahl öffnen.
2. `Vorschau-Cache` wählen.
3. Anzahl, Größe, Auslastung, Pfad und letzte Bereinigung prüfen.

### Cache sicher leeren

1. `Vorschau-Cache leeren` wählen.
2. Sicherheitsabfrage lesen.
3. Nur bestätigen, wenn keine laufende Vorschauerzeugung benötigt wird.

**Warum ist das sicher?** Entfernt werden ausschließlich eindeutig erkannte VideoBatch-Vorschaudateien und veraltete eigene Teildateien.

**Kann entfallen?** Ja. Eine Leerung ist nur bei Platzmangel, beschädigter Vorschau oder Diagnose notwendig.

**Nicht betroffen:** Originalmedien, Projektdateien und fremde Dateien.

## 7. Fehler sicher beheben

### Gelbe Meldung

1. Hinweis vollständig lesen.
2. Genannten Wert oder Pfad prüfen.
3. Empfohlene Aktion verwenden.
4. Vorgang erneut prüfen.

**Bedeutung:** Der Vorgang ist möglicherweise noch möglich, benötigt aber Aufmerksamkeit.

### Rote Meldung

1. Produktion nicht wiederholt blind starten.
2. Ursache und betroffenen Schritt lesen.
3. Nur die angebotene sichere Wiederherstellungsaktion verwenden.
4. Danach Quellen, Ziel und Queue erneut kontrollieren.

**Bedeutung:** Der betroffene Vorgang wurde zum Schutz gestoppt.

### Niemals als Schnelllösung verwenden

```text
sudo …
chmod -R 777 …
chown -R …
```

Diese Eingriffe können fremde Dateien, Rechte und Sicherheitsgrenzen verändern. Sie sind für den normalen VideoBatch-Betrieb nicht erforderlich.

## 8. Fehlende Quelldateien

Wenn eine zuvor verwendete Datei verschoben oder gelöscht wurde:

1. Medien-KPI oder Fehlerdialog öffnen.
2. Genannte fehlende Datei prüfen.
3. Entweder die Datei an ihren ursprünglichen Ort zurücklegen oder `Fehlende Verweise entfernen` verwenden.
4. Medienliste erneut kontrollieren.
5. Auftrag erst danach neu vorbereiten.

**Kann der fehlende Verweis ignoriert werden?** Nein. Ein Auftrag mit nicht erreichbaren Quellen ist nicht reproduzierbar.

## 9. Queuefehler und Wiederanlauf

1. Queue öffnen.
2. Fehlgeschlagenen Auftrag auswählen.
3. Ursprüngliche Fehlermeldung lesen.
4. `Wiederanlaufquellen laden` verwenden, falls angeboten.
5. Quellen und Einstellungen prüfen.
6. Auftrag bewusst neu starten.

**Wichtig:** Das Laden der Wiederanlaufquellen startet keinen Render automatisch. Dadurch bleibt die Kontrolle beim Nutzer und Wiederholungsschleifen werden vermieden.

## 10. Effekte zurücksetzen

Bei einem ungültigen oder nicht mehr verfügbaren Effekt:

1. Effekt-KPI oder Einstellungen öffnen.
2. Ursache lesen.
3. `Sichere Automatik wiederherstellen` wählen.
4. Effekt und Übergang kontrollieren.
5. Vorschau oder Testauftrag ausführen.

**Kann dieser Schritt entfallen?** Nur wenn stattdessen ein anderer gültiger Effekt manuell gewählt wird.

## 11. Scheduler und automatische Renderstarts

### Zeitpläne verwalten

**Aktion:** Projekt, Audio-/Medienauswahl und Ausgabe prüfen. Danach `Zeitpläne verwalten` öffnen. Dort können mehrere begrenzte Pläne für das aktuelle Projekt angelegt, bearbeitet, dupliziert oder gelöscht werden.

Die Listenansicht zeigt den nächsten Termin, die Wiederholungsart, den aktuellen Status und den Serienfortschritt. Der Reiter `Verlauf` zeigt abgeschlossene, übersprungene, fehlgeschlagene oder abgebrochene Vorkommen.

### Wiederholungen

Unterstützt werden `Einmalig`, `Täglich` und `Wöchentlich`. Wiederholungen besitzen immer ein festes Intervall und eine maximale Anzahl von Läufen; eine unbegrenzte Endlosschleife kann nicht angelegt werden.

**Was wird eingefroren?** Die Reihenfolge der Audio- und Mediendateien sowie alle Batch-Optionen. Änderungen an renderrelevanten Quellen blockieren den automatischen Start. Automatische Metadaten wie Zeitstempel oder KPI-Historie machen einen ansonsten identischen Plan nicht ungültig.

### Zeitzone und Sommer-/Winterzeit

Der Plan speichert die lokale IANA-Zeitzone. Eine bei der Sommerzeitumstellung nicht existente Uhrzeit wird sicher übersprungen. Bei der doppelten Stunde der Winterzeitumstellung verwendet VideoBatch deterministisch den späteren realen Zeitpunkt. Der konkrete systemd-Timer wird anschließend als eindeutiger UTC-Zeitpunkt registriert.

### Catch-up bei verpasstem Termin

- `Einmal nachholen`: Ein verpasster Termin darf innerhalb des gewählten Catch-up-Fensters genau einmal nachgeholt werden.
- `Verspäteten Termin überspringen`: Ein verspäteter Termin wird nicht nachträglich gestartet; bei einer Serie wird der nächste reguläre Termin geplant.

Der Rechner wird nicht automatisch eingeschaltet. `Persistent=true` sorgt nur dafür, dass systemd einen verpassten Timer beim späteren Start des Benutzer-Managers meldet; VideoBatch entscheidet danach anhand der Catch-up-Regel, ob ausgeführt oder übersprungen wird.

### Schutz vor parallelen Renderläufen

VideoBatch besitzt eine globale prozessübergreifende Render-Sperre. Dadurch können ein manueller GUI-Render und ein Scheduler-Render nicht gleichzeitig zwei Batches starten. Bei einem Konflikt wird ein Schedulertermin nur innerhalb seines zulässigen Catch-up-Fensters verschoben; danach wird das konkrete Vorkommen als Konflikt protokolliert.

### Wachhalten während des Renderns

Ist `Schlafmodus während des Renderns verhindern` aktiviert, verwendet VideoBatch `systemd-inhibit`, damit ein laufender Batch nicht durch normalen Schlafmodus oder Shutdown unterbrochen wird. Die Option wirkt nur während des tatsächlichen Renderlaufs.

### Aktion nach erfolgreichem Rendern

Optional kann nach einem vollständig erfolgreichen Batch `Energiesparen` angefordert werden. Scheitert nur diese Energieaktion, bleibt der Renderlauf als erfolgreich protokolliert; die Energieabweichung wird separat gespeichert.

### Plan bearbeiten, duplizieren oder löschen

Beim Bearbeiten wird zuerst der neue Plan erfolgreich registriert und erst danach der alte aufgehoben. Schlägt die neue Registrierung fehl, bleibt der bestehende Plan erhalten. `Duplizieren` erzeugt eine neue Scheduler-ID. Ein gelöschter Plan wird deaktiviert und als `cancelled` im Verlauf dokumentiert.

### Betriebssteuerung und Operationsansicht

Der Scheduler besitzt ab Welle 21 eine zentrale Ansicht `Was läuft wann und warum?`. Sie zeigt aktive, pausierte und wartende Serien, Priorität, Queueposition, nächsten Termin und den konkreten Grund für einen Wartestatus.

- `Pause`: Ein noch nicht gestarteter Plan wird deaktiviert. Läuft der aktuelle Render bereits, wird er kontrolliert beendet und die Serie danach pausiert.
- `Fortsetzen`: Ein pausierter Plan wird nur dann wieder aktiviert, wenn sein Catch-up-Vertrag noch eine sichere Ausführung erlaubt; veraltete Vorkommen werden nachvollziehbar übersprungen.
- `Priorität`: Werte von 0 bis 100 steuern ausschließlich die Reihenfolge wartender Schedulerläufe. Sie umgehen weder Catch-up-, Blackout- noch Ressourcenregeln.
- `Betriebsregeln`: Globale Wartungs-/Blackout-Fenster und ein Mindestwert für freien Ausgabespeicher können vorgegeben werden.
- `Abgleichen`: Prüft den internen Plan gegen die tatsächlichen systemd-User-Units und repariert kontrollierbare Drift. Ein unsicherer alter `running`-Zustand wird nicht blind nochmals gerendert.
- `Export`: Sichert Zeitpläne, Verlauf, Queue und Policy gemeinsam mit einem SHA-256-Manifest in einem Diagnose-ZIP.
- `Aufräumen`: Entfernt ausschließlich ausreichend alte terminale Serien; aktuelle und aktive Pläne sowie die Historie bleiben erhalten.

### Konfliktwarteschlange

Ist die globale Render-Lease belegt oder blockiert eine Betriebsregel den Start, wird ein zulässiger Lauf in eine persistente Queue aufgenommen. Höhere Priorität wird zuerst berücksichtigt; innerhalb gleicher Priorität bleibt die zeitliche Reihenfolge erhalten. Die Queue darf keinen Termin über sein Catch-up-Limit hinaus am Leben halten.

### Wartungsfenster und Ressourcen

Blackout-Fenster werden in einer IANA-Zeitzone gespeichert und dürfen über Mitternacht reichen. Vor dem tatsächlichen Renderstart prüft VideoBatch zusätzlich den freien Speicher des Ausgabe-Dateisystems. Eine blockierende Regel wird als Ursache gespeichert und ist in der Operationsansicht sichtbar.

### Reconciliation nach Neustart oder manueller Änderung

VideoBatch betrachtet seine Scheduler-Daten als autoritativ und systemd als Ausführungsmechanismus. Fehlen erwartete Timer-/Service-Dateien oder wurden sie verändert, kann `Abgleichen` sie aus dem gültigen Plan neu erzeugen. Pausierte bzw. abgeschlossene Pläne dürfen dabei keine aktiven Units behalten.

### Prognosequalität und Kalibrierung

Der Reiter `Prognosequalität` bewertet, wie gut die Scheduler-Prognosen in der Vergangenheit tatsächlich waren. Er zeigt Rolling-Origin-Backtests über die letzten 30, 90 und 180 auswertbaren realen Läufe, Fehler getrennt nach Codec/Profil/Auflösung sowie echte Actual-vs-Predicted-Vergleiche aus Schedulerläufen.

- `MAE`: durchschnittliche absolute Abweichung in Sekunden.
- `Median-Fehler`: robuste typische relative Abweichung.
- `P90-Fehler`: 90 % der ausgewerteten Fehler liegen bis zu diesem Wert.
- `Bias`: zeigt, ob die ETA systematisch zu hoch oder zu niedrig liegt.
- `Fehlerdrift`: warnt, wenn die jüngsten Prognosefehler deutlich schlechter als die vorherige Baseline werden.
- `Laufzeitdrift`: warnt, wenn sich die reale Renderleistung pro Job deutlich verschiebt.

Historische Samples werden nicht plötzlich verworfen. Daten bis 30 Tage erhalten volles Gewicht; ältere Daten werden stufenweise auf 0,75 / 0,5 / 0,25 abgewertet. Dadurch kann eine frühere Hardware- oder Lastsituation aktuelle Prognosen nicht unbegrenzt dominieren.

Die angezeigte Konfidenz basiert deshalb nicht mehr nur auf der Anzahl ähnlicher Läufe: Schlechte Backtest-Güte oder erkannte Drift kann eine nominell hohe Konfidenz automatisch auf `medium` oder `low` begrenzen. Fehlen belastbare Daten, bleibt die Prognose ausdrücklich unsicher.

`Export` nimmt zusätzlich `forecast-quality.json` und `forecast-actual-vs-predicted.json` in das Scheduler-Diagnosepaket auf. Die Kalibrierung verändert keine historischen Renderjournale und führt selbst keine Jobs oder Timer aus.

### Laufzeitumgebung und Performance-Epochen

Ab Welle 24 trennt VideoBatch Prognosedaten nach der tatsächlich relevanten Renderumgebung. Berücksichtigt werden CPU-/Threadprofil, FFmpeg-Version und Build, Encoderpfad sowie die Zielmedium-/Dateisystemklasse. Hostname oder Benutzerkennung werden dafür nicht gespeichert.

Ändert sich die Umgebung deutlich, werden ältere Performancewerte nicht still mit dem neuen Zustand vermischt. Frühere Daten bleiben erhalten, werden aber als andere Umgebung bzw. ältere Performance-Epoche gekennzeichnet. Ein Rückgriff auf eine frühere Epoche derselben Umgebung begrenzt die Prognosekonfidenz bewusst auf `low`.

Verschiebt sich die reale Renderleistung innerhalb derselben Umgebung über mehrere Messungen deutlich, kann VideoBatch automatisch eine neue Performance-Epoche eröffnen. Die vorherige Baseline wird nicht gelöscht. Dadurch lässt sich später nachvollziehen, ob eine ETA-Verschlechterung eher durch eine veränderte Maschine/FFmpeg-/Zielumgebung, durch echte Performance-Drift innerhalb derselben Umgebung oder durch das Forecast-Modell selbst entstanden ist.

Die Prognoseansicht ist weiterhin read-only: Das bloße Öffnen der Operationsansicht oder eine 24/48/168-Stunden-Simulation erzeugt keine neue Epoche und verändert keine Schedulerdateien. Im Diagnoseexport liegt das Epochenarchiv zusätzlich als `forecast-environment-epochs.json` vor.

## 12. Projekt speichern und beenden

1. Laufende Produktion abschließen oder kontrolliert stoppen.
2. Projekt speichern.
3. Prüfen, ob die letzte Änderung sichtbar bestätigt wurde.
4. Anwendung normal schließen.
5. Bei wichtigen Projekten Projektdatei und Medienliste sichern.

## Abschlussprüfung

- richtige Medien verwendet
- Ton vorhanden und verständlich
- Bildformat korrekt
- Anfang, Mitte und Ende geprüft
- keine Fehlermeldung offen
- Ausgabe im gewünschten Ordner vorhanden
- Originalmedien unverändert
- Projekt gespeichert

## Nächster Schritt

- Installation: `AUTOINSTALLATION_save_.md`
- Dokumentationsübersicht: `docs/DOKUMENTATIONSINDEX.md`
- Fehlerdetails: `ERROR_HANDLING.md`
- Updates: `UPDATE_SYSTEM.md`
- Projektstruktur: `PROJEKTORDNERSTRUKTUR_save_.md`
