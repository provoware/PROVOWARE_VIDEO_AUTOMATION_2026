# Langzeitrender – RC24

## Status

**Nicht ausgeführt – Gate bleibt blockiert.** Diese Datei legt das Szenario vor dem
Lauf fest. Sie ist kein Nachweis für einen bestandenen Langzeitrender.

Vorprüfung: 2026-08-04T17:12:58Z, Ubuntu 24.04.4 LTS, Linux 6.12.13 x86_64,
Arbeitsstand `c934de8aa98fd3d1addaf81065b5375b8b4aef79`. Im Prüfcontainer sind kein
RC24-Paket, kein FFmpeg, keine grafische Sitzung und kein externes Blockgerät
vorhanden. Zudem sind laut `DEVELOPMENT_STATUS.json` die Qualitätswerkzeuge und die
physische KDE-Abnahme noch offen. Der Lauf darf deshalb hier weder begonnen noch als
bestanden gewertet werden. Ursache sind die fehlenden realen Prüfmittel; die
Auswirkung ist ein weiterhin offenes Stable-Gate. Als Schutzmaßnahme bleiben
Kandidat und Status unverändert. Lösung ist die Durchführung auf dem unten
festgelegten Prüfplatz. Alternative: keine – ein internes oder gedrosseltes Ziel
ersetzt kein reales langsames externes Medium.

## Unveränderliche Kandidatenbindung

- Kandidat: `2.8.3-rc24`
- Paket: vollständiges, frisch entpacktes RC24-Projekt-ZIP
- Paket-SHA-256: **vor dem Entpacken einzutragen und danach nicht mehr zu ändern**
- Paketgröße: **vor dem Entpacken einzutragen**
- Abgleich: `VERSION.json`, `RELEASE_MANIFEST.json` und Paketprüfung müssen RC24
  bestätigen; der Paket-Hash wird vor und nach dem gesamten Szenario erneut gelesen.
- Änderungen an Paket, Eingaben, Ziel oder Prüfablauf brechen den Lauf ab. Ein neuer
  Kandidat benötigt eine neue Stable-Gate-Iteration.

## Festgelegter Datensatz

Der Eingabesatz liegt schreibgeschützt auf einem internen Datenträger. Ein
SHA-256-Manifest in stabiler, nach relativem Pfad sortierter Reihenfolge gehört zur
Evidenz.

| Art | Anzahl | Größe je Datei | Gesamtgröße | Inhalt |
| --- | ---: | ---: | ---: | --- |
| Video | 96 | 2,50 GiB | 240,00 GiB | H.264/H.265, MP4/MKV, 1080p/2160p, 25/30/50 fps |
| Audio | 96 | 100 MiB | 9,375 GiB | WAV/FLAC/AAC, 44,1/48 kHz, mono/stereo |
| Bilder | 192 | 20 MiB | 3,750 GiB | JPEG/PNG/TIFF, Hoch-/Querformat, ASCII/Umlaute/Unicode im Namen |
| **Summe** | **384** | – | **253,125 GiB** | große gemischte Medienauswahl |

Alle 384 Dateien müssen technisch lesbar sein. Beschädigte Medien gehören nicht in
den Hauptlauf, damit ein Fehler nicht die Vollständigkeitsprüfung verdeckt. Die 96
Audioelemente werden in fester Reihenfolge mit jeweils zwei Bildern zu 96
Diashow-Aufträgen verbunden. Einstellung: gemeinsamer Ausgabeordner, MP4/H.264,
1920×1080, vollständige Prüfung. Erwartete Mindestlaufzeit: acht Stunden; endet die
Verarbeitung früher, ist das Szenario nicht ausreichend und muss vor einer neuen
Iteration neu festgelegt werden.

## Reales langsames externes Ziel

- Gerät: physische USB-2.0-Festplatte, keine virtuelle Platte, kein Loop-Gerät und
  kein Netzlaufwerk
- Dateisystem: ext4
- Einhängeoptionen: `rw,nosuid,nodev,noexec`
- Freier Platz vor Start: mindestens 500 GiB
- Gemessene sequenzielle Schreibrate: höchstens 35 MiB/s; Messwert, Werkzeug und
  Gerätekennung sind vor dem Lauf zu protokollieren
- Einzutragende Identität: Hersteller, Modell, Seriennummer, `/dev`-Pfad,
  Dateisystem-UUID und Einhängepunkt
- Ausgabeordner: `<EINHÄNGEPUNKT>/provoware-rc24-langzeitrender`

Das Ziel bleibt während des Hauptlaufs physisch verbunden. Cache-, RAM-, Container-
oder künstlich gedrosselte interne Ziele sind unzulässig.

## Erwartete Ausgaben und Prüfungen

1. Vor Prozessstart existieren für alle 96 Zielnamen exklusive
   Reservierungsmarken; ein zweiter Reservierungsversuch wird abgewiesen.
2. Die Oberfläche zeigt während der Verarbeitung steigenden Gesamt- und
   Auftragsfortschritt, aktuelle Datei, verstrichene Zeit und wachsende Ausgabegröße.
   Alle 15 Minuten wird ein Zeitstempel mit Fortschrittswert dokumentiert.
3. Der Hauptlauf liefert genau ein terminales Ereignis: `batch_finished`.
4. Das Journal ist abgeschlossen, nicht als aktiv markiert und nennt dasselbe
   terminale Ereignis sowie 96 erfolgreiche Aufträge und keinen Abbruch.
5. Genau 96 endgültige MP4-Dateien entstehen. Name, Größe und SHA-256 werden in
   einem sortierten Ausgabemanifest festgehalten; jede Datei besteht die vollständige
   technische Prüfung und besitzt die erwartete Audio- und Videospur.
6. Eingabe- und Paket-Hash stimmen nach dem Lauf unverändert mit den Vorwerten
   überein. Kein Ziel wurde überschrieben.
7. Nach Abschluss gibt es keine Reservierungsmarken, temporären Ausgaben,
   unvollständigen Journale oder verwaisten FFmpeg-Prozesse.

Jede Abweichung ist ein Fehlschlag. Der Bericht muss Ursache, Auswirkung,
automatische Schutzmaßnahme, Lösung und Alternative nennen.

## Kontrollierter Abbruchfall

Erst nach vollständig bestandenem Hauptlauf wird mit demselben unveränderten Paket
ein eigener Zwei-Aufträge-Lauf in einem neuen Zielunterordner gestartet. Während des
ersten aktiven Auftrags wird einmal über die Oberfläche abgebrochen. Erwartet werden
die feste Abbruchfrist mit Eskalation bei Bedarf, genau ein `batch_cancelled`, ein
abgeschlossenes Journal, freigegebene Reservierungen, kein FFmpeg-Restprozess und
keine als erfolgreich ausgegebene Teildatei. Verändert der Fall den Kandidaten oder
würde er eine Wiederholung eines Stable-Gates erzwingen, entfällt er und wird nur als
offen dokumentiert.

## Auszufüllendes Ergebnisprotokoll

- Paket-SHA-256 und Paketgröße:
- Geräte- und Dateisystemdaten:
- KDE-/Anzeigeumgebung und FFmpeg-Version:
- Start- und Endzeit in UTC:
- Eingabemenge und bestätigte Gesamtgröße:
- Fortschrittsbeobachtungen:
- Reservierungs-, Journal-, Ereignis- und Hashnachweise:
- Anzahl und Gesamtgröße der vollständigen Ausgaben:
- Prüfung auf verwaiste Zwischenablagen und Prozesse:
- Abbruchfall oder begründeter Verzicht:
- Gesamtergebnis: **offen**

Der Langzeitrender-Blocker in `DEVELOPMENT_STATUS.json` darf erst entfernt werden,
wenn alle Felder belegt, alle erwarteten Prüfungen bestanden und die Evidenzdateien
eindeutig an Paket-Hash, Umgebung sowie Start- und Endzeit gebunden sind.
