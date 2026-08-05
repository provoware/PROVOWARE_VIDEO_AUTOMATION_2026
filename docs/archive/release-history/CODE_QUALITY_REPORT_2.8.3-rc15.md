# Code- und Installationsqualität 2.8.3-rc15

Schwerpunkte dieser Iteration:

- aktiver Slot unveränderlich,
- vollständiger Aufbau des inaktiven Slots,
- atomarer A/B-Umschalter,
- Boot-Erfolgsbestätigung,
- automatischer Boot-Rollback,
- Wiederaufnahme nach Stromausfall in jeder Transaktionsphase,
- Ed25519-signierter Channel-Index,
- signierte Einzelpakete zusätzlich zum signierten Manifest,
- monotone Releasefolge gegen Replay und Downgrade,
- HTTPS-only für Remotequellen,
- Download nur geänderter Komponenten,
- doppelte Controllergeneration als Rückfall.
