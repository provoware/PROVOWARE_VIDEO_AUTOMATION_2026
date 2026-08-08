# Scheduler Operations und Governance

## Zweck

Dieser Vertrag beschreibt den produktiven Betriebszustand des VideoBatch-Schedulers ab Fortsetzungswelle 21. systemd ist der Wecker; VideoBatch bleibt die autoritative Quelle für Planstatus, Priorität, Queue, Catch-up, Blackout- und Ressourcenentscheidungen.

## Zustandsmodell

Aktive Zustände sind `pending`, `queued` und `running`. `paused` ist bewusst inaktiv. Terminale Zustände werden nicht erneut terminiert. Ein laufender Plan kann als `pause_after_current` markiert werden; der aktuelle Render endet kontrolliert, danach wird kein Folgetermin aktiviert.

## Priorität und Queue

Prioritäten liegen zwischen 0 und 100, Standard ist 50. Die persistente Queue ordnet ausführbare Einträge zuerst nach Priorität und danach deterministisch nach Wartezeit. Queueeinträge besitzen einen Grund, einen frühesten Wiederanlauf und eine Deadline. Die Deadline wird aus dem Catch-up-Vertrag abgeleitet und verhindert unbegrenztes Verschieben.

## Betriebsregeln

Die globale Policy unterstützt Wartungs-/Blackout-Fenster mit Wochentagen, lokaler IANA-Zeitzone und Zeitbereichen über Mitternacht. Zusätzlich wird ein Mindestwert für freien Speicher auf dem tatsächlichen Ausgabe-Dateisystem geprüft. Der sichere Parallelitätsvertrag bleibt auf einen Renderbatch gleichzeitig begrenzt.

## Reconciliation

Beim Abgleich werden Planstatus, erwartete systemd-Unit-Inhalte und tatsächlicher Unit-Zustand verglichen. Repariert werden nur deterministische Abweichungen. Ein alter unklarer `running`-Zustand wird nicht automatisch als nie ausgeführt interpretiert; außerhalb des Catch-up-Fensters wird er kontrolliert abgeschlossen statt potenziell doppelt gerendert. Projektbezogener Abgleich darf Queueeinträge anderer Projekte nicht entfernen.

## Verlauf und Export

Der Verlauf bleibt auch nach konservativem Plan-Cleanup erhalten. Der Operations-Export enthält Zeitpläne, CSV-Übersicht, Verlauf, projektbezogene Queue, globale Policy und ein Manifest mit SHA-256/Größe jeder Exportdatei.

## Sicherheitsgrenzen

Pause beendet keinen bereits laufenden FFmpeg-Prozess hart. Priorität umgeht keine Sicherheitsprüfung. Ein Blackout oder Ressourcenmangel darf nur innerhalb der Catch-up-Grenze in die Queue verschieben. Manuell veränderte systemd-Dateien gelten nicht als neue Wahrheit und werden beim Reconcile gegen den kanonischen Plan geprüft.
