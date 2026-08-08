# Begrenzter, wiederaufnehmbarer Langzeitrender – RC24

## Status

Der ausführbare Abnahmevertrag ist implementiert. Der automatisierte Probelauf darf
interne CI-Speicher und weiche Threadgrenzen verwenden, ist aber ausdrücklich **kein**
Ersatz für den physischen Stable-Nachweis. Das Stable-Gate bleibt blockiert, bis der
identische Vertrag auf einem echten langsamen USB-Datenträger vollständig bestanden
wurde.

## Unveränderliche Kandidatenbindung

- Kandidat: `2.8.3-rc24`
- Paket: vollständiges RC24-Projekt-ZIP; im physischen Lauf verpflichtend
- Vertrag: eine einmal erzeugte JSON-Datei mit fest sortierten Eingaben, Ziel,
  Optionen und Ressourcenbudgets
- Vertragsdigest: wird beim Erststart gespeichert und bei jeder Wiederaufnahme
  unverändert verlangt
- Paket- und Eingabe-SHA-256: vor dem ersten Render vollständig erzeugt und nach dem
  Abschluss vollständig erneut geprüft
- Änderungen an Vertrag, Paket, Eingaben oder Ziel blockieren die Wiederaufnahme

## Festgelegter physischer Datensatz

Der Eingabesatz liegt auf einem **schreibgeschützt eingehängten** internen Datenträger.
Der Vertragsgenerator wählt nach stabiler, groß-/kleinschreibungsunabhängiger
Dateinamenssortierung genau 96 Audiodateien und 192 Bilder. Je Audiodatei werden zwei
Bilder zu einem Auftrag gebunden.

| Art | Anzahl | Zielumfang |
|---|---:|---|
| Audio | 96 | WAV/FLAC/AAC, vollständig mit FFprobe lesbar |
| Bilder | 192 | JPEG/PNG/TIFF, vollständig mit FFprobe lesbar |
| Aufträge | 96 | MP4/H.264, 1920×1080, vollständige Dekodierprüfung |

Zusätzliche Dateien in den Eingabeordnern werden nicht stillschweigend aufgenommen.
Die ausgewählten absoluten Pfade stehen vollständig in der Vertragsdatei.

## Reales langsames Ziel

Für einen bestandenen physischen Lauf gelten gleichzeitig:

- eigener physischer Blockdatenträger, nicht `/`, kein Loop-, RAM- oder Netzlaufwerk
- über `udevadm` als USB-Gerät bestätigt
- Dateisystem `ext4`
- schreibbar eingehängt; Originalmedien liegen auf einem anderen, schreibgeschützten
  Mount
- mindestens 500 GiB frei
- gemessene sequenzielle Schreibrate höchstens 35 MiB/s
- Zielidentität mit Gerät, Modell, Seriennummer, Dateisystem-UUID, Mountpunkt und
  Mountoptionen im Zustandsnachweis

Die Schreibmessung verwendet eine exklusive 64-MiB-Probedatei, ruft `fsync` auf und
entfernt die Datei unmittelbar danach. Bestehende Ausgaben werden niemals
überschrieben oder verschoben.

## Ressourcen- und Zeitgrenzen

Standardvertrag:

- CPU: 50 Prozent über eine eigene systemd-cgroup
- RAM: 4096 MiB über `MemoryMax`
- Aufruf-Timeout: 10 Stunden
- kumulierter Gesamt-Timeout: 20 Stunden
- Heartbeat: alle 15 Minuten
- FFmpeg-Threads: zusätzlich an das CPU-Budget angepasst

Der physische Lauf verlangt harte systemd-Grenzen. Weiche Grenzen sind nur mit den
sichtbaren Probelaufoptionen erlaubt und kennzeichnen den Ergebnisbericht dauerhaft
als `rehearsal_only`.

## Persistenter Ablauf

1. Ziel, Mounts, freier Speicher, USB-Identität, Schreibrate, FFmpeg und FFprobe
   werden vor dem Render validiert.
2. Alle Originale und das RC24-Paket erhalten ein sortiertes SHA-256-Manifest.
3. Für jeden Zielnamen wird exklusiv eine persistente Reservierungsdatei erzeugt.
4. Nach jedem vollständig geprüften Auftrag werden Zustand, Versuchszahl,
   Ausgabedateigröße und SHA-256 atomar gespeichert.
5. Heartbeats enthalten Lauf-ID, Fortschritt, aktive Auftrags-ID, verstrichene Zeit,
   Ausgabegröße und einen eigenen Digest.
6. Abbruch, Timeout oder Prozessende hinterlassen einen wiederaufnehmbaren Zustand.
   Unfertige Ausgaben werden vor dem nächsten Versuch in den Evidenzordner verschoben
   und niemals als Erfolg übernommen.
7. Bereits abgeschlossene Ausgaben werden bei Wiederaufnahme erneut per Größe,
   SHA-256, FFprobe und vollständiger Dekodierung geprüft und nicht doppelt erzeugt.
8. Nach Abschluss werden Originale nochmals vollständig gehasht, genau 96 Ausgaben
   verifiziert und ein sortiertes Ausgabemanifest erzeugt.
9. Erst danach werden die Reservierungen entfernt und genau ein terminales
   `run_completed` protokolliert.

## Vertrag erzeugen

```bash
PYTHONPATH=src python3 scripts/build_long_render_contract.py \
  --audio-dir /mnt/eingaben-ro/audio \
  --image-dir /mnt/eingaben-ro/bilder \
  --package /pfad/VideoBatch_Fast_2.8.3-rc24.zip \
  --target-dir /mnt/langsames-usb/provoware-rc24-langzeitrender \
  --output /pfad/rc24-long-render-contract.json
```

Die Vertragsdatei wird exklusiv neu angelegt. Eine vorhandene Datei wird nicht
überschrieben.

## Erstlauf und Wiederaufnahme

```bash
PYTHONPATH=src:. python3 scripts/run_long_render_acceptance.py \
  --contract /pfad/rc24-long-render-contract.json \
  --evidence-dir /pfad/stable-evidence
```

Ein kontrollierter Abbruch oder Aufruf-Timeout endet mit Statuscode `75`. Danach wird
nur derselbe Vertrag fortgesetzt:

```bash
PYTHONPATH=src:. python3 scripts/run_long_render_acceptance.py \
  --contract /pfad/rc24-long-render-contract.json \
  --resume \
  --evidence-dir /pfad/stable-evidence
```

## Evidenz

Im Zielordner entsteht `.provoware-long-render/` mit:

- `state.json` – atomarer Hauptzustand und Checkpoints
- `events.jsonl` – dauerhaft synchronisierte Ereignisfolge
- `heartbeats/heartbeat-*.json` – periodische Zustandsnachweise
- `partials/` – sicher archivierte unfertige Ausgaben vor Wiederaufnahme
- `final-report.json` – gebundener Abschlussbericht

Nach einem vollständig bestandenen **physischen** Lauf erzeugt `--evidence-dir` zusätzlich `long_render.json` im Stable-Evidence-Schema 2. Dieser Export bindet den Nachweis an Kandidat, Release-Manifest und den ausführungsrelevanten Source-Fingerprint. Rehearsals, interne Ziele oder unzureichend langsame/nicht externe Ziele können diese Stable-Evidence nicht erzeugen.

## Automatisierter Probelauf

Der Workflow `Bounded resumable long-render rehearsal` erzeugt sechs feste
Vier-Sekunden-Aufträge, stoppt kontrolliert nach zwei Aufträgen, setzt denselben
Vertrag fort und prüft:

- keine Doppelverarbeitung der ersten beiden Ausgaben
- unveränderte Eingabegrößen und SHA-256
- genau einen finalen Abschluss
- sechs vollständig geprüfte Ausgaben
- persistente Heartbeats
- entfernte Reservierungen und keine Teildateien im Ziel

Der Bericht dieses Laufs trägt dauerhaft `rehearsal_only: true`.

## Stable-Freigabebedingung

Der Langzeitrender-Blocker darf erst entfernt werden, wenn ein physischer Lauf mit
96 Aufträgen `completed` meldet, `rehearsal_only` falsch ist, alle Eingabe- und
Paket-Hashes unverändert sind, 96 Ausgaben vollständig geprüft wurden und der
Abschlussbericht eindeutig an Gerät, Vertrag, Kandidat, Start- und Endzeit gebunden
ist.
