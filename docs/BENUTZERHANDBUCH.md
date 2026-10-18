# VideoBatch Fast – Benutzerhandbuch

**Version:** 2.8.3-rc24  
**Zielgruppe:** Nutzer ohne technische Vorkenntnisse  
**Wichtig:** Dies ist ein Release Candidate. Für wichtige Projekte zuerst mit Kopien der Medien testen.

## Ziel

Mit VideoBatch Fast werden aus Audiodateien, Bildern und Videos automatisiert fertige Videos erzeugt. Dieses Handbuch führt vom ersten Start bis zur Ergebnisprüfung und erklärt bei jedem kritischen Schritt, warum er notwendig ist und ob er ausgelassen werden darf.

## Pflichtgrad

Der sichere erste Start und die Ergebnisprüfung sind Pflicht. Zusätzliche Gestaltung und Komfortfunktionen sind optional.

## Voraussetzungen

Das vollständige Projektpaket, FFmpeg und FFprobe müssen vorhanden sein. Für den ersten Lauf werden Kopien der Medien empfohlen.

## Schritt-für-Schritt-Anleitung

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

## 4. Erstes Video erstellen

**Entwicklungshinweis:** Die folgende Bedienung beschreibt den Entwicklungszweig zu PR #239. Sie ist **noch nicht** Teil des freigegebenen Releasekandidaten 2.8.3-rc24.

Das VideoBatch-Fenster bietet vier übersichtliche Bereiche:

1. **1 · Dateien** – Audio, Bilder und Videos auswählen und die Großvorschau nutzen.
2. **2 · Produktion** – Dateipaare prüfen und fertige Videos erstellen.
3. **Erweitert** – selten benötigte Prüfung, Sicherheit und ausgeschlossene Programmierordner.
4. **Hilfe / Werkzeuge** – zusätzliche Funktionen und Diagnose.

**Auflösung, Qualität, Bildeffekt und Ausgabeordner bleiben über allen vier Bereichen sichtbar.** Lange Dateilisten dürfen innerhalb ihrer Liste scrollen, die wichtigsten Schaltflächen sollen dabei erreichbar bleiben.

### Schritt 1: Audiodateien hinzufügen

**Aktion:** Links `1 · Dateien` öffnen. Dort `Audio auswählen …` wählen und mindestens eine unterstützte Audiodatei übernehmen.

**Warum notwendig?** Die meisten Produktionsmodi benötigen eine Tonquelle.

**Kann entfallen?** Nur in einem ausdrücklich tonlosen Modus. Andernfalls bleibt der Auftrag unvollständig.

**Erwartetes Ergebnis:** Die Audioanzahl im Header oder in der Medien-KPI steigt.

### Schritt 2: Bilder oder Videos hinzufügen

**Aktion:** Auf derselben Dateiseite rechts `Bilder/Videos auswählen …` wählen.

**Warum notwendig?** Ohne visuelle Quelle kann kein normales Video erzeugt werden.

**Kann entfallen?** Nein, außer ein spezieller Modus erzeugt das Bild vollständig selbst.

**Erwartetes Ergebnis:** Die Medienanzahl steigt und eine Vorschau wird angezeigt.

### Schritt 3: Vorschau kontrollieren

**Aktion:** Den zuletzt aktiv angeklickten Eintrag prüfen.

**Warum notwendig?** Die Vorschau zeigt, welche Quelle aktuell maßgeblich ausgewählt ist.

**Kann entfallen?** Technisch ja, aber dann können falsche Medien unbemerkt im Auftrag bleiben.

### Schritt 4: Modus wählen

**Aktion:** Oben bei **Auflösung** die Größe, bei **Qualität** den gewünschten Kompromiss zwischen Geschwindigkeit und Bildqualität sowie bei **Bildeffekt** den gewünschten Look wählen. Die Vorgaben „Originalgröße“, „Ausgewogen“ und „Kein Effekt“ sind einfache Ausgangspunkte.

**Empfehlung:** Beim ersten Test die vorgeschlagenen Einstellungen verwenden und zunächst nur einen kurzen Auftrag starten.

**Warum notwendig?** Dadurch bestimmst du, wie groß und aufwendig das Ergebnis werden soll. Die Bildeffekt-Auswahl ändert keine Überblendungen.

**Kann entfallen?** Ja. Die gespeicherten Grundwerte werden übernommen.

### Schritt 5: Ausgabeordner prüfen

**Aktion:** Im dauerhaft sichtbaren Feld **Ausgabeordner** auf **Wählen …** klicken und einen beschreibbaren Ordner aussuchen.

**Warum notwendig?** Das fertige Video muss sicher gespeichert werden können.

**Kann entfallen?** Nein. Ohne beschreibbares Ziel darf die Produktion nicht starten.

**Erwartetes Ergebnis:** Die Pfadprüfung meldet den Ordner als nutzbar.

### Schritt 6: Produktion starten

**Aktion:** `2 · Produktion` öffnen, die Paarung kontrollieren und `▶ Prüfen & Videos erstellen` wählen.

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

## Medienbibliothek im Entwicklungszweig – nur Medien aus drei Ordnern

**Pflichtgrad:** Automatisch erledigt. Die zusätzlichen Ausschlüsse sind optional.

Das Programm merkt sich erkennbare Audio-, Bild- und Videodateien aus **Videos**, **Downloads** und **Bilder** sowie deren Unterordnern. Unter Linux kann der Bilderordner auch `Pictures` heißen. Maßgeblich ist die tatsächliche Linux-Verzeichniskonfiguration. Quellcode, ZIP-Dateien und normale Dokumente werden nicht aufgenommen.

**Beim Start:** Bereits bekannte Medien erscheinen als zuletzt gespeicherter Stand. Die Aktualität wird danach im Hintergrund kontrolliert; ein Cache-Eintrag bedeutet nicht automatisch, dass die Originaldatei noch vorhanden ist.

**Eigene Programmierordner auslassen:** Bereich **Erweitert** öffnen, **Eigene Programmierordner auslassen** aufklappen, über **Projektordner auswählen …** den Ordner wählen und **Ausgeschlossene Ordner speichern** anklicken. Es werden nur Unterordner innerhalb der drei Medien-Hauptordner akzeptiert.

**Erwartetes Ergebnis:** Die gespeicherte Anzahl ausgeschlossener Ordner wird angezeigt. Der Medienindex wird im Hintergrund neu aufgebaut, ohne Originalmedien zu löschen.

**Bei einem Fehler:** Die Meldung unter der Speichern-Schaltfläche lesen. Falsche oder unvollständige Ordnerpfade korrigieren. Wenn der Index beschädigt ist, wird eine Diagnosekopie gesichert und der Index erneut erstellt.

**Abschlussprüfung:** Einen neuen Film oder ein neues Foto in einem der drei Hauptordner ablegen, eine Programmdatei in Downloads danebenlegen und den Medienbrowser öffnen. Nur die Medien dürfen in der Mediensuche erscheinen.

**Hinweis:** Der Entwicklungszweig ist noch nicht freigegeben. Die Freigabe folgt erst nach vollständigen Qt-, Rendering-, Leistungs- und realen Kubuntu-Sichtprüfungen.

## 5. Ansicht, Zoom und Sortierreihenfolge

### Oberfläche vergrößern

Oben im Bereich **Ansicht** kann die gesamte Oberfläche auf **100 %, 125 %, 150 %, 175 % oder 200 %** gestellt werden.

Tastatur:

- `Strg+Alt+Pfeil hoch`: gesamte Oberfläche größer
- `Strg+Alt+Pfeil runter`: gesamte Oberfläche kleiner
- `Strg+Alt+0`: gesamte Oberfläche auf 100 % zurücksetzen

### Nur eine Medienliste vergrößern

Wenn der Fokus in der Audio- oder Medienliste liegt:

- `Strg + Mausrad` oder `Strg + Plus/Minus`: nur diese Liste vergrößern oder verkleinern
- `Strg+0`: nur diese Liste auf Normalgröße zurücksetzen

Die Listen-Vergrößerung und die globale Ansichtsgröße sind bewusst getrennt.

### Sortieren ohne versehentliche neue Paarung

Eine Sortierung nach Name, Änderungsdatum oder Größe verändert zunächst **nur die sichtbare Ansicht**. Die Produktionsreihenfolge der Audio-/Medienpaare bleibt unverändert.

Erst die ausdrückliche Aktion **„Ansicht als Produktionsreihenfolge übernehmen“** ändert die Reihenfolge, aus der später die Aufträge gebaut werden.

**Warum wichtig?** Dadurch kann eine reine Ansichtssortierung nicht unbemerkt andere Audio-/Bild-Paare erzeugen.

## 6. Mehrere Auswahlrunden

1. Im Medienbrowser Dateien markieren.
2. `Auswahl übernehmen + im Ordner bleiben` wählen.
3. Weitere Dateien oder Ordner ergänzen.
4. Erst mit `Fertig` die Gesamtauswahl in das Projekt übernehmen.

**Warum notwendig?** Dadurch können Quellen aus mehreren Ordnern gesammelt werden, ohne den Browser jedes Mal neu zu öffnen.

**Kann entfallen?** Ja. Bei Quellen aus nur einem Ordner genügt eine Auswahlrunde.

## 7. Vorschau-Cache

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

## 8. Fehler sicher beheben

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

## 9. Fehlende Quelldateien

Wenn eine zuvor verwendete Datei verschoben oder gelöscht wurde:

1. Medien-KPI oder Fehlerdialog öffnen.
2. Genannte fehlende Datei prüfen.
3. Entweder die Datei an ihren ursprünglichen Ort zurücklegen oder `Fehlende Verweise entfernen` verwenden.
4. Medienliste erneut kontrollieren.
5. Auftrag erst danach neu vorbereiten.

**Kann der fehlende Verweis ignoriert werden?** Nein. Ein Auftrag mit nicht erreichbaren Quellen ist nicht reproduzierbar.

## 10. Queuefehler und Wiederanlauf

1. Queue öffnen.
2. Fehlgeschlagenen Auftrag auswählen.
3. Ursprüngliche Fehlermeldung lesen.
4. `Wiederanlaufquellen laden` verwenden, falls angeboten.
5. Quellen und Einstellungen prüfen.
6. Auftrag bewusst neu starten.

**Wichtig:** Das Laden der Wiederanlaufquellen startet keinen Render automatisch. Dadurch bleibt die Kontrolle beim Nutzer und Wiederholungsschleifen werden vermieden.

## 11. Effekte zurücksetzen

Bei einem ungültigen oder nicht mehr verfügbaren Effekt:

1. Effekt-KPI oder Einstellungen öffnen.
2. Ursache lesen.
3. `Sichere Automatik wiederherstellen` wählen.
4. Effekt und Übergang kontrollieren.
5. Vorschau oder Testauftrag ausführen.

**Kann dieser Schritt entfallen?** Nur wenn stattdessen ein anderer gültiger Effekt manuell gewählt wird.

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

## Hilfe: SHA-256, Dateiindex und Prüfstatus verstehen

**Ziel:** Eine Meldung zur Dateiprüfung einordnen, ohne technische
Vorkenntnisse. **Pflichtgrad:** Für die normale Videoproduktion optional.

**Einfach erklärt:** SHA-256 ist ein digitaler Fingerabdruck des
*Dateiinhalts*. Ändert sich der Inhalt, ändert sich normalerweise
der Fingerabdruck. Bei reinem Umbenennen bleibt er gleich;
deshalb kontrolliert VideoBatch auch den Speicherpfad.

**Wichtig: zwei getrennte Aufgaben.** Der **Medienindex** zeigt
deine Musik, Fotos und Videos. Der **Projekt-Dateiindex** ist ein
Entwicklungswerkzeug und kontrolliert Programmdateien und deren
Änderungen. Du musst diesen nicht bedienen, um Videos zu erzeugen.
Originalmedien werden durch die Projekt-Dateiprüfung nicht verändert.

**Prüfstatus:** „Bestanden“ bedeutet: ein bestimmter Test wurde
erfolgreich ausgeführt. „Wiederverwendet“ darf künftig nur dann
erscheinen, wenn der passende Test für genau denselben geprüften
Stand nachweislich erfolgreich war. Ein beschädigter, unbekannter
oder veralteter Nachweis verlangt einen neuen Test. **Keine
Sicherheitsprüfung und keine Releasefreigabe wird ersetzt.**

**Bei einem Fehler:** Nichts an Originalmedien ändern und keine
pauschalen Berechtigungen vergeben. Entwickler finden Befehle,
Schutzregeln und weitere Prüfungen in
[Dateiindex und Prüfstrategie](PROJEKTORDNER_DATEIINDEX_PRUEFSTRATEGIE.md).

**Abschlussprüfung:** Der normale Start und die Medienauswahl
funktionieren weiterhin ohne SHA-256-Eingaben. Eine Hilfeauswahl
zeigt nur Informationen an und startet keine Hintergrundprüfungen.
