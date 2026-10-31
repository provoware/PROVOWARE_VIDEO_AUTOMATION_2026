# Changelog

Alle wichtigen Änderungen dieses Projekts werden hier in zusammengefasster, chronologischer Form dokumentiert. Die vollständige frühere Detailhistorie liegt unter `docs/archive/release-history/CHANGELOG_FULL_PRE_FINALIZATION.md`.

## Unveröffentlicht · 31.10.2026 – Dokumentations- und Bestandsabgleich

- `README.md` für Einsteiger in **drei Ebenen** gegliedert: nummerierte und tatsächlich vorhandene Kopierbefehle, ausführlicher Ablauf mit Index, farbig gekennzeichnete Hilfe mit Erklärung technischer Begriffe.
- Aktuelle Dashboard-Schnellnotiz mit lokaler TXT-Ablage, Datenintegritätsgrenzen und 800×600-/200%-Bedienung dokumentiert; historische Release-Blöcke unverändert erhalten.
- Fehlende Root-Skripte aus Entwicklungsanleitungen durch echte Pfade `scripts/dev/test.sh`, `scripts/dev/verify_release.sh` und `scripts/dev/build_artifacts.sh` ersetzt.
- Dokumentationswegweiser und Status um frühere, inzwischen erledigte PR-Verweise bereinigt. Letzter geprüfter produktiver Stand vor diesem Dokumentationspatch: `b6d715ea65407afc7bb8a9838cea99af19ffb5d6`, 0 offene PRs; ein grüner CI-Lauf ist keine Stable-Freigabe.
- Die vorhandene Dokumentationsprüfung wird um einen Regressionstest für Drei-Ebenen-Aufbau, echte Skriptpfade und unveränderte historische Marker ergänzt. Keine Löschung historischer Beweisdokumente.

## Unveröffentlicht · Strukturmigration und Informationspflege (20.10.2026)

- Benutzer-Hauptordner auf höchstens acht Dateien reduziert; reales Entwicklungs-ZIP mit sieben Hauptordnerdateien entpackt und den Kommando-Einstieg geprüft.
- Hauptstarter auf `STARTEN.sh` vereinheitlicht; interne Skripte und Verträge nach `scripts/` beziehungsweise `config/` ausgelagert.
- Installations-, Qualitäts-, Release- und Qt-Pfade nach Migration korrigiert; Sperrdateien und `pip-audit` wieder synchronisiert.
- Sichere Paket-/Wurzelverzeichnis-Regressionen und zusätzlichen GitHub-Entpacktest ergänzt.
- Auf Commit `2ae2ae5` alle acht GitHub-Prüfläufe erfolgreich; keine reale GUI-Erstinstallation oder Stable-Endabnahme behauptet.
- Parallele PRs #247, #248 und #250 geschlossen und benötigte Änderungen in #246 konsolidiert; #250 ohne Merge geschlossen.
- README, Status, TODO, Dokumentationswegweiser und Schnellstart auf die neue Struktur und die verbleibenden Freigabesperren aktualisiert.
- Historische RC24-Nachweise unverändert belassen.

## Unveröffentlicht · RC24-Finalbereinigung

- realen 125-%-Sichtbefund behoben: Dateien, Ausgabe und Produktion liegen nicht mehr gleichzeitig in drei gequetschten Spalten, sondern auf getrennten Arbeitsseiten
- Hauptarbeitsbereich benötigt keine eigene Scrollfläche mehr; nur echte Datenlisten scrollen bei umfangreichen Inhalten intern
- Dateiauswahl zeigt Audio und Bilder/Videos nebeneinander mit ausreichend hohen Listen und dauerhaft sichtbaren Aktionsschaltern
- Projekt, Hilfe und Diagnose öffnen als Zusatzbereiche, ohne den aktiven Drei-Schritt-Arbeitsbereich dauerhaft zu verkleinern
- Alt+1, Alt+2 und Alt+3 öffnen jetzt zuerst die passende sichtbare Arbeitsseite und setzen danach den Fokus
- reale Release-Sichtabnahme auf 100 %, 125 %, 150 % und 200 % erweitert
- Qt-Statusausgaben, 100–200-%-Skalierung und Tastatur-Zoom für Barrierefreiheit korrigiert
- Sortierung der Medienlisten von der Produktionsreihenfolge entkoppelt; Übernahme nur noch ausdrücklich
- veralteten, nicht deklarierten RC24-Qualitätsbericht aus dem Release-Stamm archiviert
- Release-Dateivertrag gegen nicht deklarierte `_save_`-Dateien im Projektstamm gehärtet
- `manifest.json` gegen kanonische Release-Evidenz auf Name, Version, Kanal, Build-Datum, Artefaktpolitik und Einstieg abgesichert
- aktuelle Release-Unterlagen auf Kubuntu 26.04 / KDE Plasma / natives Wayland bereinigt; alte X11-/Vierfachmatrix-Aussagen entfernt
- physische UI-Freigabe bleibt fail-closed offen; nach dem realen 125-%-Befund ist eine neue 100/125/150/200-%-Sichtabnahme erforderlich
- Nutzerfeedback im Footer klar in **Status** und **Nächster Schritt** getrennt, semantisch eingefärbt und für schmale Fenster responsiv gestapelt
- Hilfevertrag auf die tatsächlich zuständige Hilfeseite ausgerichtet
- Zustandsberechnung für Medien, Aufträge und Effekte getrennt, ohne sichtbare Ausgabe zu ändern
- Gestaltungsprüfung in kleine, gleichwertige Teilprüfungen gegliedert
- `BatchRunner` vollständig auf direkte, versionierte `AppEvent`-Ausgabe migriert
- typisierte Pflicht-Payloads für Start, Auftrag, Fehler und Stapelabschluss ergänzt
- Legacy-Ereignisse auf `EventBuffer.put_legacy` als einzige Kompatibilitätsgrenze begrenzt
- AST-Wächter gegen neue freie `(name, payload)`-Ereignistupel ergänzt
- `SelectionPreviewController` vollständig auf direkte typisierte `AppEvent`-Ausgabe migriert
- Pflicht-Payloads für erfolgreiche und fehlgeschlagene Auswahlvorschauen ergänzt
- zentrales Ereignisregister für Kennungen, Payloadtypen, Handler und Klassifizierungen eingeführt
- fail-closed Vollständigkeitsprüfer für Producer, UI-Handler, Terminalstatus und Vertragstests ergänzt
- releasefertige eigenständige Unterlagen eindeutig mit `_save_` gekennzeichnet
- maschinenlesbaren Release-Dateistatus und zweispaltige README-Übersicht ergänzt
- historische RC-Berichte verlustfrei aus dem Projektstamm archiviert und aus Releasepaketen ausgeschlossen
- veraltete doppelte visuelle Baselines entfernt
- Changelog-Dubletten und widersprüchliche Überschriften bereinigt
- Vorschauerzeugung für FFmpeg 7+ durch explizites PNG-Ausgabeformat gehärtet
- beschädigte Cacheziele werden vor einem Neuaufbau sicher entfernt
- Tooltips verzögert, tastaturfähig, zerstörungssicher und bildschirmgebunden umgesetzt
- Cache-, Auswahl- und Hilfeaktionen mit klareren Hilfetexten und Tooltips ergänzt

## 2.8.3-rc24

- Absturz bei schnellen Klickfolgen in der ausgewählten Medienliste behoben
- serielle Vorschauverwaltung, Debounce, Generationstoken und validierte Pillow-/Tk-Übergabe ergänzt
- Thumbnail-Cache auf 1 GiB und 2.000 Dateien begrenzt
- Cache-Diagnose, sichere Leerung und pro Schlüssel arbeitende Prozesssperre ergänzt
- vollständige Kubuntu-Matrix für Ubuntu 22.04/24.04 und X11/Wayland automatisiert
- native APT-/Pip-Caches mit wöchentlichem Warmup und maschinenlesbarem Cachebericht ergänzt

## 2.8.3-rc23

- Symbolansicht, stabilere Medienauswahl und WCAG-orientierte Kontrastprüfung ergänzt
- Header, Navigation, Arbeitskarte, Vorschaukarte und Aktionsleiste visuell vereinheitlicht

## 2.8.3-rc22

- interaktive Fehlerlösungen, sichere Ordneraktionen und automatische Einstellungsreparatur ergänzt
- sammelnde Mehrfachauswahl und dauerhafte Headerstatistik eingeführt

## 2.8.3-rc20

- visuelle Bildreihenfolge, Szenenkopplung, Audiowellenform und sichere Caches ergänzt

## 2.8.3-rc19 bis rc1

- modulare Vollbildoberfläche, getrennte Zoomsteuerung, sichere Installer-/Updatepfade, A/B-Slots, Recovery, Plugin-Sandbox, Qualitätsverträge und reproduzierbare Builds schrittweise eingeführt

## 2.8.2 und früher

- Grundverträge für Datenintegrität, Ausgabeprüfung, Plugins, Updates, Layoutprofile und Buildverifikation aufgebaut
