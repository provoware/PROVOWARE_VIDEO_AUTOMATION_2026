# Changelog

Alle wichtigen Änderungen dieses Projekts werden hier in zusammengefasster, chronologischer Form dokumentiert. Die vollständige frühere Detailhistorie liegt unter `docs/archive/release-history/CHANGELOG_FULL_PRE_FINALIZATION.md`.

## Iteration 39A · A33-Lineage-Rebase & Packaging-Hygiene · 2026-09-04

- A33 mechanisch auf den kanonischen A32.2-Head `8755d5333b2f53ff8080655f8af39727db9b8c48` rebaset; danach 18 Commits voraus und 0 hinter der Basis;
- gemeinsamen Release-Dateivertrag um Ausschlüsse für `Backup/`, Python-Caches, Test-/Qualitätscaches, Bytecode und Coverage-Zwischendateien gehärtet;
- A33-Paketbau vom rohen Arbeitsbaum-ZIP auf den vorhandenen deterministischen manifestgeführten Release-Packager umgestellt;
- kanonische Werkzeugversionen aus `requirements-toolchain.lock` im CI-Lauf explizit verifiziert;
- Fokusregression 47/47 und Vollregression 477 bestanden / 2 übersprungen / 0 fehlgeschlagen;
- Coverage neu gemessen: 73,16 % Zeilen und 58,82 % Branch; 80/65-Schwellen unverändert und weiterhin blockierend;
- Architektur-Audit: 115 Module, 1.139 Funktionen, 140 Klassen, größte Python-Datei 699 Zeilen, 0 Befunde;
- deterministischen Zweitbau, Manifest-Verifikation und expliziten Paket-Hygienetest ergänzt;
- `main` und der Merge von PR #84 nach `main` blieben unangetastet.

## Unveröffentlicht · RC24-Finalbereinigung

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

## A32.2 Evidence-Reconciliation · 2026-09-04

- aktuellen 468-Test-Vollregressionsnachweis als kanonische Release-Evidence übernommen;
- Coverage 73,38 % / 59,01 % als expliziten blockierenden 80/65-Gate aufgenommen;
- README/STATUS zeigen bestandene, gesammelte und übersprungene Tests getrennt;
- keine Produkt-/Runtime-Logik geändert.
