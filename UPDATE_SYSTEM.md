# Update-System 2.8.3-rc17

## Signiertes Channel-Verzeichnis

`channel-index.json` wird mit Ed25519 signiert. Es enthält getrennte Einträge für `stable` und `rc`, die jeweils Version, monotone Releasefolge, Mindest-Installer-Schema, Mindest-Ausgangsversion, Manifest-URL, Manifestgröße, SHA-256, Update-Reihenfolge sowie Komponenten-Hashes und Downloadgrößen festlegen.

URLs sind relativ zum Index und können deshalb auf jedem statischen HTTPS-Host bereitgestellt werden. Der Updater akzeptiert remote ausschließlich HTTPS. Lokale `file://`-Quellen sind nur für reproduzierbare Offline- und CI-Prüfungen zugelassen.

## A/B-Aktivierung

Der bestätigte Slot bleibt unverändert. Der inaktive Slot wird aus dem bestätigten Stand geklont, anschließend werden nur geänderte vollständige Komponenten ersetzt. Danach folgen:

1. Prüfung jeder Datei gegen das signierte Release-Manifest,
2. Prüfung jedes vollständigen Komponentenbaums,
3. Portable-Vollmanifest,
4. Runtime- und FFmpeg-Smoke-Test,
5. atomarer Wechsel des relativen `current`-Links,
6. echter Start bis zur UI-Bereitschaft,
7. endgültige Bestätigung oder automatischer Rückfall.

## Stromausfallsicherheit

`pending_transaction.json` wird vor dem Umschalten dauerhaft geschrieben. Liegt nach einem Neustart der alte Slot noch unter `current`, wird der vorbereitete Wechsel verworfen. Zeigt `current` bereits auf den neuen Slot, wird der erste Start überwacht. Scheitert er, wird der Link atomar auf den bestätigten Slot zurückgesetzt.

## Downloadökonomie

Der Channel-Index und das signierte Manifest werden zuerst geladen. Danach vergleicht VideoBatch die installierten Komponenten-Hashes. Nur Teilpakete tatsächlich geänderter Komponenten werden geladen. Jede Komponente wird dennoch vollständig ersetzt, wodurch Mischzustände innerhalb einer Komponente ausgeschlossen bleiben.

## Folge-Iteration nach 2.8.3-rc24

Keine Änderung am Updateprotokoll. Die Iteration verbessert nur Hilfe, Startfeedback und Statusdarstellung. A/B-Aktivierung, Stromausfallsicherheit und Downloadökonomie bleiben unverändert.

## Folge-Iteration · globale Standards und Basisabhängigkeiten

Keine Änderung am A/B-Updateprotokoll. Für das Basisprojekt gelten weiterhin vollständige Projekt-ZIPs als sicherer Hauptweg vor Stable. Mitlieferbar sind feste Python-Laufzeitpakete, öffentliche Schlüssel, Textkataloge, Themes, Referenzdaten und offline vorbereitete Qualitätswerkzeuge. Systemabhängige Bestandteile wie FFmpeg, Display-Server und Desktop-Pakete werden nur nach Plattform-, Lizenz-, Hash- und Rauchtestprüfung gebündelt.

## Folge-Iteration · typisierte Ereignisarchitektur

Keine Änderung am signierten Channel-, A/B- oder Rollback-Protokoll. Der `BatchRunner` liefert intern nur noch versionierte `AppEvent`-Objekte. Nicht migrierte UI-Producer dürfen den alten Nutzdatenkanal ausschließlich über `EventBuffer.put_legacy` verwenden; ein AST-Gate verhindert neue freie Ereignistupel.
