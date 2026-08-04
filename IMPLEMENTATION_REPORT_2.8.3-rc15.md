# Implementierungsbericht 2.8.3-rc15

RC15 ersetzt die direkte Komponentenänderung im aktiven Programmbaum durch ein echtes A/B-System. Der aktive Slot wird nie geschrieben. Updates werden im inaktiven Slot vollständig aufgebaut und geprüft. Ein atomarer relativer Symlink aktiviert den Kandidaten. Der erste echte UI-Start bestätigt die Version; bei einem Fehler erfolgt automatisch der Rückfall.

Zusätzlich wurde ein statisch hostbares, Ed25519-signiertes Channel-Repository eingeführt. Es unterstützt Stable- und RC-Kanäle, relative HTTPS-URLs, monotone Releasefolgen, Mindestversionen, Komponentenabhängigkeiten und gezielte Downloads ausschließlich geänderter Teilpakete.
