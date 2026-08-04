# Folge-Iteration nach 2.8.3-rc24

- Hilfezentrum ergänzt einen einfachen Sicherheits-Tipp für gelbe und rote Hinweise.
- Grafischer Startdialog erklärt Wartezustand, automatische Prüfung und Fehlerprotokoll klarer.
- Systemstatus im Hilfezentrum erhält mehr Innenabstand und wirkt dadurch sichtbarer.

# 2.8.3-rc24

- Zentrale Fehlerauflösung gegen fehlende, unlesbare und unvollständige Registereinträge abgesichert.
- Unbekannte Schweregrade und ungültige Aktionslisten fallen sicher auf einen gestoppten Vorgang mit Protokollzugriff zurück.
- Lösungsdialog kennzeichnet Hinweise, Warnungen und gestoppte Vorgänge einheitlich in einfacher Sprache.
- Absturz beim Anklicken der bereits ausgewählten Bilderliste strukturell behoben.
- Hauptlisten-Vorschau von unbegrenzten Einzelthreads auf genau einen seriellen Vorschauarbeiter umgestellt.
- 180-ms-Debounce und Generationstoken verhindern parallele FFmpeg-Prozesse und veraltete Vorschauergebnisse.
- Aktiver Fokus der Mehrfachauswahl bestimmt zuverlässig das angezeigte Bild.
- Vorschau-PNGs werden vor Tk-Anzeige auf Dateigröße, Pixelzahl und Lesbarkeit geprüft.
- Direkte Übergabe externer Vorschaudateien an Tks nativen PNG-Decoder entfernt.
- Technische Dateiprüfung im interaktiven Lösungsdialog funktionsfähig angebunden.
- Diagnoseprotokolle verwenden bei unbeschreibbarem Statusordner einen sicheren temporären Fallback.
- Plugin-Sandboxfähigkeit wird mit einem realen Namespace-Probelauf geprüft.
- RC24-Regressionssuite mit 120 schnellen Hauptlisten-Klicks, Coalescing, Fehlerverwerfung und Decoderhärtung ergänzt.
- Diagnose- und Architekturaudits legen fehlende Elternordner in vollständig leeren Benutzerprofilen selbst an.

# 2.8.3-rc23

- Harten Medienlisten-Absturz durch vollständige Trennung von Tk-Hauptthread und Scan-/Vorschauarbeitern behoben.
- Thread-sichere Ereigniswarteschlange mit begrenztem GUI-Polling und sicherem Schließen eingeführt.
- Virtualisierte Symbolansicht mit kleinen Bild-/Video-Vorschaubildern, Mehrfachauswahl und Sammlung ergänzt.
- Listen- und Symbolansicht können im Auswahlfenster direkt gewechselt werden.
- Vorschau bleibt an den zuletzt aktiv angeklickten Eintrag gebunden und verwirft veraltete Ergebnisse.
- Eingabe-, Kombinations-, Tabellen-, Auswahl- und Schalterfarben verwenden automatisch kontrastsichere Schriftfarben.
- Medienauswahl visuell in Header, Navigation, Arbeitskarte, Vorschaukarte und Aktionsleiste gegliedert.
- RC23-Regressionssuite für schnelle Auswahlwechsel, Symbolansicht und WCAG-Kontrast ergänzt.

# 2.8.3-rc22

- interaktive, direkt ausführbare Fehlerlösungen statt reiner Informationsdialoge
- automatische Reparatur eindeutig vergessener Einstellungen
- sichere Erstellung von Ausgabe- und Projektordnern ohne Rootrechte
- korrigierte Mehrfachauswahl-Vorschau nach zuletzt aktivem Eintrag
- sammelnde Medienauswahl mit „Übernehmen und im Ordner bleiben“
- sichtbarer Auswahlstatus bereits übernommener Dateien
- permanente Headerstatistik für Dateien, Aufträge und zentrale Einstellungen
- scrollbar erklärte Lösungsdialoge mit fest sichtbaren Aktionen
- eigene visuelle Regression für das Lösungsfenster

# 2.8.3-rc20

- visuelle Bildreihenfolge mit Drag-and-drop, alphabetischer Sortierung, Aufnahmedatum, reproduzierbarem Zufall und Umkehrfunktion
- festes Start- und Abschlussbild als geschützte Anker
- lokale Audiowellenform mit automatischen Markern für Intro, Beat-Einsatz, ruhige Phase, Drop und Outro
- optionale Szenenkopplung mit variablen Bildzeiten und sicherem gleichmäßigem Fallback
- persistenter, größenbegrenzter Wellenformcache mit strenger Datenvalidierung
- kurze Audios mit vielen Bildern erzeugen weiterhin strikt monotone, gültige Szenengrenzen
- sämtliche neuen UI-Texte vollständig im zentralen Textkatalog
- Konfigurationsnormalisierung modularisiert; maximale Komplexität wieder unter dem Projektlimit
- Updatekanal bleibt bis zur Stable-Freigabe ein Entwickler-/Nachrelease-System und ist nicht primärer Nutzerweg

# 2.8.3-rc19

- Kontrast- und Farbsystem für bessere Sichtbarkeit nachgeschärft.
- Strg+Mausrad zoomt den Bereich unter dem Mauszeiger unabhängig.
- Schriftgröße im Header über A−, Prozentanzeige, A+ und 100 % steuerbar.
- Neuer Mehrdateimodus: Alle ausgewählten Bilder werden als automatische Diashow auf jedes Audio angewendet.
- Audiodauer wird automatisch erkannt; Bildzeiten und Überblendungen werden autonom berechnet.
- Reale FFmpeg-Regressionsprüfung für Zwei-Bild-Diashow ergänzt.

# Changelog

## 2.8.3-rc19

- Hauptoberfläche in sechs vollflächige Tabs umgebaut.
- obere Menüleiste und Tastaturkürzel ergänzt.
- getrennten Zoom je Hauptbereich eingeführt.
- splitterbasierte Layoutwiederherstellung deaktiviert, um Zurückspringen zu verhindern.
- großen Medien- und Audiobrowser mit Downloads-Start, Vorschau, Mehrfachauswahl, Ordnerimport und Sortierung ergänzt.
- Installations- und Ausgabeordner mit echter Schreibprobe und sicheren XDG-Ausweichpfaden gehärtet.
- keine pauschale Root-/sudo-Abfrage; fremde oder unbrauchbare Pfade werden nicht gewaltsam verändert.
- neue Regressionstests für Tabs, Menü, Zoom, Medienbrowser und Berechtigungsfälle.
- symbolische oder unzugängliche Alt-Installationspfade werden per `lstat` sicher erkannt und quarantänisiert.

# 2.8.3-rc17

- signierter Stable-/RC-Channel-Index mit relativen HTTPS-URLs
- monotone Releasefolge, Mindestversionen und feste Update-Reihenfolge
- Download ausschließlich geänderter Komponenten
- echtes A/B-System mit zwei vollständigen Slots
- aktiver Slot während Updates unveränderlich
- atomarer `current`-Symlink
- Boot-Erfolgsbestätigung und automatischer Rückfall
- Stromausfall-Recovery vor und nach der Umschaltung
- signierte Teilpakete zusätzlich zum signierten Release-Manifest

# 2.8.3-rc11

- UI-Bereitschaft wird vor dem Schließen des Starters technisch bestätigt.
- Automatischer sicherer Startmodus nach frühem Oberflächenfehler.
- Verifizierter System-Python-Rückfall, falls die isolierte Laufzeit nicht repariert werden kann.
- Verlorene Laufzeitmarken werden ohne Neuinstallation rekonstruiert.
- Ein zweiter Start aktiviert das vorhandene Fenster.
- Startprüfung unterscheidet bereit, Warnung und eingeschränkten Betrieb ohne UI-Blockade.

# Änderungshistorie

## 2.8.3-rc10

- vorausschauenden Startvertrag eingeführt
- ruhiges grafisches Bootstrap-Fenster ergänzt
- Laufzeit- und Qualitätsumgebung getrennt
- virtuelle Umgebungen inhaltsadressiert außerhalb des Projekts aufgebaut
- verschobene-venv-Fehlerklasse beseitigt
- FFmpeg-Encoderparser für reale Fähigkeitsflags korrigiert
- realen AAC-Kurztest ergänzt
- FFmpeg-Probleme beim Start zu sichtbaren, nicht blockierenden Warnungen herabgestuft
- automatische KDE-, Desktop- und Terminalstarter ergänzt
- 183 Regressionstests erreicht

# Changelog

## 2.8.3-rc10

- fehlerhafte Wheelhouse-Aufräumlogik vollständig ersetzt
- Schutz gegen Löschen von Projektwurzel, Arbeitsverzeichnis, Home und `/` ergänzt
- fehlende Wheelhouse-Manifeste und Hash-Lockfiles automatisch rekonstruierbar
- lokale Wiederverwendung aus früheren RC-Versionen und persistentem Cache ergänzt
- normaler Start vollständig ohne Rückfrage und ohne manuelle Setup-Schritte
- kompakte Fortschrittsanzeige und getrennte Detailprotokolle ergänzt
- verständliche Diagnose- und Protokollbefehle ergänzt
- zentrales Hilfezentrum mit sichtbarem Systemstatus eingeführt
- 172 Tests sowie neue Bootstrap-, Recovery-, Löschschutz- und Hilfezentrumtests

## 2.8.3-rc10

- statische sichtbare UI-Texte vollständig in den geprüften deutschen Textkatalog ausgelagert.
- zentralen Textvertrag für Schlüssel, Platzhalter und verbotene direkte UI-Literale ergänzt.
- dauerhafte Dateiablage in `safe_io.py` zentralisiert.
- Einzelinstanzsperre gegen konkurrierende Zustandsänderungen ergänzt.
- persistentes Stapeljournal mit kontrollierter Wiederherstellung ausschließlich offener Jobs eingeführt.
- Renderoptionen, Versuchszahlen und ursprüngliche Fehler im Recovery-Journal erhalten.
- Recovery-Controller aus `ui.py` ausgelagert; Hauptdatei wieder auf 588 Zeilen reduziert.
- FFmpeg-Fähigkeitsprüfung für benötigte Encoder und Filter ergänzt.
- Stillstands-Watchdog mit begrenzter SIGTERM-/SIGKILL-Eskalation ergänzt.
- vollständige Audio-/Videodekodierung in der tiefen Ergebnisprüfung ergänzt.
- begrenzten UI-Ereignispuffer und kontrolliertes Beenden von Hintergrundaufgaben ergänzt.
- Branch-Coverage aktiviert und Mindestwerte 80 Prozent Zeilen sowie 65 Prozent Branches eingeführt.
- vollständiger Stand: 166 Tests, 80,55 Prozent Zeilenabdeckung, 65,84 Prozent Branch-Abdeckung, 12/12 Simulationen und 16/16 visuelle Referenzen.

## 2.8.3-rc5

- Versionsdrift zwischen VERSION.json, pyproject.toml und Qualitätsvertrag beseitigt.
- automatisches fail-closed Versionskonsistenz-Gate ergänzt.
- Testabdeckung auf über 80 Prozent erhöht; Fehlerpfade für Validierung, Playlist, Vorschau, Ausgabeprüfung, Kalender und Medienbibliothek ergänzt.
- Wheelhouse-Vertrag an die aktuelle Buildidentität gebunden.

## 2.8.3-rc3

- RC2-Fehlerpfad behoben: `prepare` ist nicht mehr vom separaten `scripts/verify_quality_wheelhouse.py` abhängig
- Wheelhouse-Prüfung in `quality_wheelhouse_common.py` als zentrale, gemeinsam genutzte Implementierung verankert
- Installer und Orchestrator verwenden denselben Prüfkern; das separate Prüferskript ist nur noch ein optionaler CLI-Einstieg
- Paketvollständigkeits- und Fehlskript-Regressionstest ergänzt
- Releaseidentität angehoben, damit RC2 unverändert nachvollziehbar bleibt

## 2.8.3-rc2

- eindeutige RC2-Artefaktidentität aus der unveränderten RC1-Ausgangsbasis erzeugt
- zentralen `QUALITY_TOOLCHAIN_CONTRACT.json` eingeführt
- Ruff 0.16.1, MyPy 2.3.0, Bandit 1.9.4 und pip-audit 2.10.1 exakt gebunden
- Onlinebezug ohne ausdrückliche Zustimmung blockiert
- vollständiges transitives Hash-Lockfile für das Offline-Wheelhouse ergänzt
- Installation auf `--no-index --require-hashes` gehärtet
- `quality.sh`, `test.sh` und `stable_release.sh` fail-closed an die Werkzeugkette gebunden
- lokale Qualitätsumgebung und Buildausgaben aus Releaseartefakten ausgeschlossen
- Teststand auf 137 Tests erweitert
- maximale Funktionskomplexität verbindlich von 45 auf 30 gesenkt
- FFmpeg-Prozessüberwachung aus dem Runner in `runner_process.py` ausgelagert
- Updatepaketprüfung in `update_validation.py` nach Hülle, Manifest, Nutzlast und visueller Bindung getrennt
- Seccomp-Aufbau in `sandbox_seccomp.py` isoliert und mit Fehlerpfadtests abgesichert
- UI-Ereignisrouting in ein wiederverwendbares Mixin ausgelagert
- Fehlerpfadabdeckung auf mindestens 74 Prozent angehoben
- Offline-Wheelhouse-Builder, Hashmanifest, Prüfer und Installer ergänzt
- strenge Qualitätsstrecke verwendet eine getrennte `.quality-venv` und blockiert bei fehlenden oder falschen Werkzeugversionen


## 2.8.2-rc1

### Datenintegrität
- Offline-Medienpfade bleiben in Projekt und Playlist erhalten.
- Ausgabeziele werden stapelweit exklusiv reserviert.
- Dateiablage verwendet atomare Transaktionsjournale und sichere Recovery.
- Runner garantiert Abschlussereignis und begrenzte Prozesseskalation.
- Ereignisse führen eine durchgehende Korrelations-ID.

### Plugin- und Updatehärtung
- Nur die implementierte Capability `validator` ist zugelassen.
- Validatoren laufen unter Linux mit Namespace, Chroot, Seccomp und Ressourcenlimits.
- ZIP-Updates werden auf Links, doppelte Namen, Traversal, Größe und Kompressionsrate geprüft.
- Kandidaten müssen vor und nach dem Selbsttest byteidentisch bleiben.
- Stable-Updategenerator liest Versionen ausschließlich aus `VERSION.json` und erzeugt reproduzierbare ZIP-Einträge.

### Codequalität
- `pyproject.toml`, exakte Lockdateien und Qualitätsregistry ergänzt.
- interne AST-, Sicherheits-, Komplexitäts- und Dateigrößengates ergänzt.
- pytest-cov-Mindestabdeckung 69 %.
- Ruff, MyPy, Bandit und pip-audit in `quality.sh` verpflichtend integriert.
- Build-Artefakterzeugung von schreibgeschützter Verifikation getrennt.

## 2.8.1-rc1

- Rasterzustände projektbezogen je Anwendungsauflösung und UI-Zoom gespeichert.
- Vier Splitterpositionen als robuste Verhältniswerte statt absolute Pixelwerte persistiert.
- Selbstheilung für kollabierte, ungültige und veraltete Layoutprofile ergänzt.
- Projektschema auf Version 3 erweitert.
- Reales GUI-Roundtrip-Szenario für Speichern, Neustart und Wiederherstellung ergänzt.
- Visuelle Referenzbasis für Version 2.8.1-rc1 erneuert und 16/16 geprüft.

# Changelog

## 2.8.0 Stable

- Oberfläche auf ein moderneres Blau-Anthrazit-Design umgestellt.
- Kacheln, Tabs, Tabellen, Fortschrittsbalken, Versionsanzeige und Fokusdarstellung modernisiert.
- Visuellen Freigabevertrag auf Schema 2 angehoben.
- Laufzeitpfade, Zeitstempel, Pixelmittelwerte, dHash-Werte und Meldungstexte vom Freigabehash getrennt.
- Normalisierten visuellen Reporthash ergänzt.
- Verschlüsselte Schlüsselarchivierung mit Scrypt und AES-256-GCM ergänzt.
- CLI für Erzeugung und Verifikation von Offline-Schlüsselarchiven ergänzt.
- Stable-Updatevalidierung an visuellen Vertrag und Abnahmehash gebunden.
- Stable-Updatepaket von 2.8.0-rc1 auf 2.8.0 erzeugt und praktisch installiert.
- Release-Manifest um Channel, Build und visuelle Freigabebindung erweitert.
- Visuelles Offline-Dashboard modernisiert und Normalisierungsstatus sichtbar gemacht.
- Tests auf 90 erweitert.

## 2.8.0-rc1

- 2×2-Arbeitsraster, Profi-Debug-Footer, Plugin-Freigabeverwaltung und signierte Desktop-Abnahme eingeführt.

## 2.8.3-rc10

- autonome Ein-Klick-Finalisierung ergänzt
- Stable-Versionen im Versionsvertrag unterstützt
- reale automatisierte Desktopfreigabe mit Screenshot-Hash ergänzt
- Stable-Gate verlangt nun zwingend eine gültige Desktopfreigabe
- transaktionale Stable-Arbeitskopie und deterministischer Abschlussbericht ergänzt
- sämtliche Setup-Rückfragen entfernt

## 2.8.3-rc13

- vollständig eingebettete portable Linux-x86_64-Laufzeit eingeführt
- festes FFmpeg/FFprobe einschließlich nativer Bibliotheken integriert
- selbstentpackenden, hashgeprüften Ein-Datei-Starter ergänzt
- System-Python, System-FFmpeg und Netzwerk zur Laufzeit entkoppelt
- portable Bootstrap-Schnellstrecke ohne Toolchain-Aufbau ergänzt
- explizite FFmpeg-/FFprobe-Pfade für portable Builds ergänzt
- zwölfstufiges, sandboxiertes Fehlerlabor integriert
- Fehlerlabor im Hilfezentrum, Terminal und Release-Gate verfügbar gemacht
- ENOSPC, Schreibabbruch, Rechte, Zielverlust, FFmpeg-Absturz, Stillstand, Suspend, 100-Jobs, Langzeitfortschritt, Konfigurations- und Recoveryfälle abgesichert

## 2.8.3-rc13

- RC12-Stack-Smashing durch strikte Trennung von Python- und FFmpeg-Laufzeit behoben.
- FFmpeg startet in bereinigter Hostumgebung ohne fremden Loader und ohne fremdes `LD_LIBRARY_PATH`.
- SHA-256-Prüfung der selbstentpackenden Portable-Nutzlast ergänzt.
- Ed25519-Signaturkette für Artefakte, Manifeste und offizielle Updates ergänzt.
- Reproduzierbare Kubuntu-22.04/24.04-X11/Wayland-Buildmatrix ergänzt.

## 2.8.3-rc14
- Signierte Auto-Installation mit nummerierten Komponentenpaketen bis 30 MB.
- Fester Installationspfad ohne Versionsnummer.
- Atomare Teilupdates mit automatischem Rollback.

## 2.8.3-rc17

- A/B-Rollbackstatus vollständig konsistent gemacht.
- Offline-`--verify-only` ohne ursprüngliches Installerpaket ermöglicht.
- Release-ID, Channel-Generation, Ablaufdatum und Same-Origin-Downloadschutz ergänzt.
- Archive und vollständige Slots strikt allowlist- und größenbasiert validiert.
- Speicherplatzvorprüfung, vollständiges fsync und automatische Komponentenreparatur ergänzt.
- Nummerierte Komplettausgabe mit maximal 30 MB je ZIP eingeführt.
- RC15→RC16-Controllerbrücke nach Anwendungsrollback hashgebunden selbstheilend gemacht.
