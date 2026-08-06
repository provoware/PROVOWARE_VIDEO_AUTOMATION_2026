# Automatische Installation – VideoBatch Fast 2.8.3-rc24

## Ziel

Diese Anleitung erklärt, was die automatische Installation tut, welche Schritte zwingend erforderlich sind und wie ein sicherer Rückfall funktioniert.

## Pflichtgrad

- **Pflicht:** Plattformprüfung, Schreibprobe, Signatur- und Hashprüfung, Selbsttest und abschließende Slotprüfung.
- **Empfohlen:** Vorherige Sicherung wichtiger Projekte.
- **Optional:** Installation in einen abweichenden Benutzerordner.

## Voraussetzungen

- Linux x86-64 auf Ubuntu oder Kubuntu 22.04 beziehungsweise 24.04
- normaler Benutzerzugang
- vollständig heruntergeladenes Installationspaket
- genügend freier Speicherplatz
- keine laufende VideoBatch-Produktion

## Sicherheitsgrundsatz

VideoBatch installiert in benutzereigene XDG-Pfade. Pauschale Rootrechte, `chmod 777` und rekursive Besitzänderungen sind nicht vorgesehen.

**Warum notwendig?** Dadurch bleiben Systemdateien und fremde Benutzerdateien außerhalb des Installationsbereichs geschützt.

**Kann entfallen?** Nein. Wird stattdessen mit Rootrechten oder globalen Schreibrechten gearbeitet, ist die Sicherheitsgrenze nicht mehr nachvollziehbar.

## Sicherung und Rückweg

Vor einer Aktualisierung bleibt der bestätigte aktive A/B-Slot unverändert. Der neue Stand wird ausschließlich im inaktiven Slot aufgebaut. Erst nach erfolgreicher Prüfung wird `current` atomar umgeschaltet.

**Rückweg:** Scheitert der erste Start oder die abschließende Prüfung, wird automatisch auf den zuletzt bestätigten Slot zurückgeschaltet.

## Schritt-für-Schritt-Ablauf

### Schritt 1: Betriebssystem und Architektur prüfen

**Automatisch erledigt.**

Geprüft werden Betriebssystem, Architektur und benötigte Werkzeuge.

**Warum notwendig?** Ein Paket für eine falsche Plattform darf nicht installiert werden.

**Kann entfallen?** Nein.

**Erwartetes Ergebnis:** Die Plattform wird als unterstützt gemeldet.

### Schritt 2: Installationsziel prüfen

**Automatisch erledigt.**

Der Zielordner wird durch eine echte Schreibprobe geprüft.

**Warum notwendig?** Nur eine reale Schreibprobe zeigt, ob Dateien dort sicher angelegt, ersetzt und gelöscht werden können.

**Kann entfallen?** Nein. Eine reine Rechteanzeige reicht nicht aus.

**Bei einem Fehler:** Einen anderen Benutzerordner auswählen oder den vorgeschlagenen XDG-Standardpfad verwenden.

### Schritt 3: Unbrauchbare Altpfade behandeln

**Automatisch oder nach Bestätigung.**

Ein beschädigter oder unbrauchbarer Altpfad wird nicht überschrieben. Er wird entweder sicher quarantänisiert oder durch einen neuen Benutzerpfad ersetzt.

**Warum notwendig?** Dadurch bleibt der alte Zustand für Diagnose und Rücknahme erhalten.

**Kann entfallen?** Nur wenn der vorhandene Pfad vollständig nutzbar ist.

### Schritt 4: Paketidentität prüfen

**Automatisch erledigt.**

Geprüft werden Signatur, SHA-256, Paketgröße und Entpackgrenzen.

**Warum notwendig?** Damit manipulierte, beschädigte oder unvollständige Pakete vor dem Entpacken blockiert werden.

**Kann entfallen?** Nein.

**Bei einem Fehler:** Installation abbrechen und Paket erneut aus einer verifizierten Quelle herunterladen.

### Schritt 5: Inaktiven A/B-Slot aufbauen

**Automatisch erledigt.**

Der bestätigte aktive Slot bleibt unangetastet. Der neue Stand wird vollständig im inaktiven Slot vorbereitet.

**Warum notwendig?** Ein fehlgeschlagenes Update darf die funktionsfähige Installation nicht zerstören.

**Kann entfallen?** Nein, wenn ein sicherer Rückfall gewährleistet bleiben soll.

### Schritt 6: Runtime-, Medien- und UI-Selbsttest ausführen

**Automatisch erledigt.**

Geprüft werden Python-Laufzeit, FFmpeg, grundlegende Medienverarbeitung und Start der Benutzeroberfläche.

**Warum notwendig?** Vollständige Dateien allein beweisen noch nicht, dass die Anwendung auf diesem System startet.

**Kann entfallen?** Nein.

### Schritt 7: `current` atomar umschalten

**Automatisch erledigt.**

Der relative `current`-Link wird erst nach bestandenem Vorabtest auf den neuen Slot gesetzt.

**Warum notwendig?** Ein atomarer Wechsel verhindert einen halben oder gemischten Installationszustand.

**Kann entfallen?** Nein.

### Schritt 8: Ersten Start bestätigen

**Automatisch mit sichtbarer Rückmeldung.**

VideoBatch wird bis zur bestätigten UI-Bereitschaft gestartet.

**Erwartetes Ergebnis:** Die Oberfläche öffnet sich und meldet einen erfolgreichen Start.

**Bei einem Fehler:** Der Installer fällt automatisch auf den vorherigen bestätigten Slot zurück.

### Schritt 9: Aktiven Slot abschließend prüfen

**Automatisch erledigt.**

Nach dem Wechsel wird der tatsächlich aktive Slot noch einmal unabhängig geprüft.

**Warum notwendig?** Dadurch wird nicht nur der vorbereitete, sondern der wirklich verwendete Stand bestätigt.

**Kann entfallen?** Nein.

## Was bei einem unsicheren Ziel passiert

Kann ein Ziel nicht sicher verwendet werden:

1. bleibt der vorhandene Inhalt unverändert;
2. nennt der Installer die konkrete Ursache;
3. erklärt er die automatische Schutzmaßnahme;
4. bietet er einen kontrollierten Benutzerpfad als Alternative an;
5. startet keine teilweise Installation.

## Was nicht getan werden darf

Nicht als Schnelllösung verwenden:

```text
sudo …
chmod -R 777 …
chown -R …
```

**Warum?** Diese Befehle können Sicherheitsgrenzen zerstören und fremde Dateien verändern.

## Abschlussprüfung

- unterstützte Plattform bestätigt
- Zielordner durch Schreibprobe bestätigt
- Signatur und SHA-256 bestanden
- inaktiver Slot vollständig aufgebaut
- Runtime-, Medien- und UI-Test bestanden
- `current` zeigt auf den bestätigten Slot
- Oberfläche startet
- vorheriger Slot bleibt als Rückfall verfügbar

## Kann die automatische Installation weggelassen werden?

Ja, wenn VideoBatch ausschließlich aus einem vollständig geprüften, portablen Projektordner gestartet wird. Dann müssen Start, Abhängigkeiten, Pfade und spätere Updates manuell kontrolliert werden. Für normale Nutzer ist die automatische Installation daher der empfohlene Weg.

## Nächster Schritt

Nach erfolgreicher Installation `START_HIER_save_.md` öffnen und das erste Testvideo erstellen.
