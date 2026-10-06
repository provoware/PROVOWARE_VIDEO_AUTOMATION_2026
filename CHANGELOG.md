# Changelog

Alle wichtigen Änderungen dieses Projekts werden hier in zusammengefasster, chronologischer Form dokumentiert. Die vollständige frühere Detailhistorie liegt unter `docs/archive/release-history/CHANGELOG_FULL_PRE_FINALIZATION.md`.

## Unveröffentlicht · RC24-Finalbereinigung

- Qt-Statusausgaben, 100–200-%-Skalierung und Tastatur-Zoom für Barrierefreiheit korrigiert
- Sortierung der Medienlisten von der Produktionsreihenfolge entkoppelt; Übernahme nur noch ausdrücklich
- veralteten, nicht deklarierten RC24-Qualitätsbericht aus dem Release-Stamm archiviert
- Release-Dateivertrag gegen nicht deklarierte `_save_`-Dateien im Projektstamm gehärtet
- `manifest.json` gegen kanonische Release-Evidenz auf Name, Version, Kanal, Build-Datum, Artefaktpolitik und Einstieg abgesichert
- aktuelle Release-Unterlagen auf Kubuntu 26.04 / KDE Plasma / natives Wayland bereinigt; alte X11-/Vierfachmatrix-Aussagen entfernt
- physische UI-Freigabe nach den letzten UI-/Skalierungsänderungen wieder fail-closed auf offen gesetzt; neue 100/150/200-%-Sichtabnahme erforderlich
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
