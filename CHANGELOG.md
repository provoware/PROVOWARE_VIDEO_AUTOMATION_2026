# Changelog

Alle wichtigen Änderungen dieses Projekts werden hier in zusammengefasster, chronologischer Form dokumentiert. Die vollständige frühere Detailhistorie liegt unter `docs/archive/release-history/CHANGELOG_FULL_PRE_FINALIZATION.md`.

## Iteration 40A · Reference-Aligned Visual Polish · 2026-09-04

- Gesamtprojekt gegen kanonische SVG-Referenz, Design-Tokens, UI-Blueprint, Einsteigerreferenz und aktuelle Shell-Verträge auditiert;
- historische Theme-ID `neon_gravity` kompatibel beibehalten, sichtbaren Produktnamen jedoch konsistent auf `Midnight Blue` vereinheitlicht;
- Standardpalette von violett-schwarzem Legacy-Look auf die kanonische Navy-/Blue-Palette mit klaren Surface-Ebenen, Cyan-Fokus, Grün-Erfolg und gezieltem Gold/Magenta-Akzent umgestellt;
- Primärbutton-Hover von Warnfarbe entkoppelt und Fokuszustände für Standard-/Primärbuttons deutlicher abgesichert;
- vier öffentlichen Theme-Namen in `theme.py` exakt an den kanonischen Shellvertrag angeglichen;
- Reference-Alignment-Regressionsprüfung ergänzt: Name, Kernpalette in SVG, WCAG-AA-Hauptkontraste, Statusdifferenzierung und vier semantische Einsteiger-Aktionsfarben;
- alten visuellen Capture-Harness als Evidence-Lücke dokumentiert, da er noch `VideoBatchFastUI` statt der aktiven `CanonicalVideoBatchFastUI` erfasst; Baselines deshalb nicht automatisch ersetzt;
- keine Render-, Queue-, Medien-, Fehler- oder sonstige Fachlogik geändert und kein Merge durchgeführt.

## Iteration 39B · Core-vs.-Tk-Transfermatrix für PySide6/QML · 2026-09-04

- finalen 39A-Head `121211244d90932775348ac26039b3d7315e60b2` als alleinige Transferbasis festgelegt;
- maschinenlesbare Transfermatrix mit drei verpflichtenden Klassen eingeführt: A direkt wiederverwendbar, B vor Transfer entkoppeln, C Tk-spezifisch und nativ in PySide6/QML neu bauen;
- 9 toolkit-neutrale Start-, Fehler-, Audit-, Registry- und Packaging-Komponenten als A klassifiziert;
- `debug_launcher.py`, `runtime_error_hooks.py`, `canonical_shell_contract.py` und den 39A-CI-Workflow als B klassifiziert;
- `canonical_ui.py`, `canonical_shell_workspace.py` und `canonical_shell_chrome.py` als C klassifiziert und direkten Tk→Qt-Codeport ausdrücklich ausgeschlossen;
- Regressionstests ergänzt, die bekannte A/B/C-Grenzen, Toolkit-Neutralität der A-Pythonquellen und die unveränderten Stable-Gates absichern;
- als ersten echten Qt-Transfer für 39C die Extraktion eines toolkit-neutralen Runtime-Error-Cores festgelegt;
- Coverage-Schwellen 80 % Zeilen / 65 % Branch sowie physische KDE-X11-/Wayland- und Slow-Target-Soak-Gates unverändert gelassen;
- kein Merge von PR #101, PR #84 oder `main` durchgeführt.

## Iteration 39A · A33-Lineage-Rebase & Packaging-Hygiene · 2026-09-04

- A33 mechanisch auf den kanonischen A32.2-Head `8755d5333b2f53ff8080655f8af39727db9b8c48` rebaset; danach 18 Commits voraus und 0 hinter der Basis;
- gemeinsamen Release-Dateivertrag um Ausschlüsse für `Backup/`, Python-Caches, Test-/Qualitätscaches, Bytecode und Coverage-Zwischendateien gehärtet;
- A33-Paketbau vom rohen Arbeitsbaum-ZIP auf den vorhandenen deterministischen manifestgeführten Release-Packager umgestellt;
- kanonische Werkzeugversionen aus `requirements-toolchain.lock` im CI-Lauf explizit verifiziert;
- Fokusregression 47/47 und Vollregression 477 bestanden / 2 übersprungen / 0 fehlgeschlagen;
- Coverage neu gemessen: 73,16 % Zeilen und 58,82 % Branch; 80/65-Schwellen unverändert und weiterhin blockierend;
- Architektur-Audit: 115 Module, 1.139 Funktionen, 140 Klassen, größte Python-Datei 699 Zeilen, 0 Befunde;
- deterministischen Zweitbau, Manifest-Verifikation und expliziten Paket-Hygienetest ergänzt;
- finaler PR-Diff-Audit: sechs redundante Quellkopien unter `Backup/A32.2_vor_A33/` aus der Integrations-Lineage entfernt; Rückrollbarkeit erfolgt über Git-Historie und dokumentierte Basis-SHA;
- Draft-Child-PR #101 gegen die weiterhin offene PR-84-Lineage angelegt; kein Merge durchgeführt;
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
