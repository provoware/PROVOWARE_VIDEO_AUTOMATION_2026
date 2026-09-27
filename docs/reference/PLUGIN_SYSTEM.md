# Plugin-System 2.8.3-rc11

Aktuell ist ausschließlich `validator` implementiert. Andere Capabilities sind nicht nur inaktiv, sondern aus `allowed_capabilities` entfernt.

Ein Validator benötigt:

1. gültiges Manifest
2. vertrauenswürdige Ed25519-Signatur
3. identischen Payload-Hash
4. sichtbare Berechtigungsfreigabe
5. nicht abgelaufene Pluginfreigabe
6. statische AST-Prüfung ohne Importe und dynamische Codefunktionen
7. verfügbare Linux-OS-Isolierung
8. erfolgreichen Sandbox-Test

Die Laufzeit verwendet User-, Netzwerk-, PID- und Mount-Namespace, Chroot, schreibgeschützte Bind-Mounts, Seccomp, Ressourcenlimits und Timeout. Fehlt eine Schicht, bleibt das Plugin inaktiv.
