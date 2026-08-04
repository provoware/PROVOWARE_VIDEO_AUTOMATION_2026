# Plugin-OS-Isolierung 2.8.2

## Unterstützter Vertrag

Nur `validator` ist implementiert und erlaubt. `quick_mode_provider` und `exporter` bleiben gesperrt, bis Laufzeit, Datenvertrag, Berechtigungsmodell und Tests vollständig vorhanden sind.

## Linux-Schutzschichten

1. Ed25519-Signatur und Inhalts-Hash
2. statische AST-Prüfung ohne Importe oder dynamische Codefunktionen
3. isolierter Pythonstart
4. User-, Netzwerk-, PID- und Mount-Namespace
5. schreibgeschütztes Chroot-Dateisystem mit kleinem tmpfs
6. eingeschränkte Builtins
7. Seccomp-Filter gegen Prozess-, Netzwerk-, Mount- und Kerneloperationen
8. CPU-, Speicher-, Dateigrößen- und Dateideskriptorlimits
9. festes Zeitlimit

Fehlt eine verpflichtende Schutzschicht, wird das Plugin nach dem Fail-Closed-Prinzip nicht ausgeführt.
