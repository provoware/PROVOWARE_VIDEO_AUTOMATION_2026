# Datenintegritätshärtung 2.8.2

## Projektverweise

Nicht erreichbare Audio-, Bild-, Video- und Playlistpfade bleiben in der Projektdatei erhalten. Die Oberfläche kennzeichnet sie als `offline`. Nur eine ausdrückliche Nutzeraktion entfernt sie.

## Ausgabezielreservierung

Vor dem Start werden sämtliche Ausgabepfade als Stapel geprüft und über private `O_EXCL`-Marker reserviert. Doppelte Ziele, vorhandene Ausgaben und parallele Reservierungen blockieren den gesamten Start vor FFmpeg.

## Archivtransaktion

Jede Ablage besitzt ein Journal unter `Verwendet/.transactions/` mit Zuständen von `prepared` bis `committed`. Zielgröße und SHA-256 werden vor dem Entfernen der Quelle geprüft. Bei Unsicherheit bleibt das Original erhalten.

## Runner-Abschluss

Der Runner kapselt den gesamten Stapel in `try/except/finally`, beendet noch laufende Prozessgruppen und sendet immer `batch_finished`. Interne Fehler erhalten zusätzlich `batch_failed_internal` samt begrenztem Traceback und Korrelations-ID.
