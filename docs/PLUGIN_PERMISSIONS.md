# Sichtbare Plugin-Berechtigungen

Vor einem Sandbox-Test zeigt die Oberfläche:

1. Plugin-ID
2. Herausgeber
3. Signaturschlüssel
4. Capability
5. Risikostufe
6. erlaubte Datenzugriffe
7. erlaubte Aktionen
8. verbotene Aktionen

Die Angaben stammen aus `registries/PLUGIN_REGISTRY.json`. Ein Plugin wird ohne Bestätigung nicht ausgeführt. Signatur, statische Prüfung und Berechtigungsanzeige ersetzen einander nicht, sondern bilden mehrere unabhängige Schutzschichten.
