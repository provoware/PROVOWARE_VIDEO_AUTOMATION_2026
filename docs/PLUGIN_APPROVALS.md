# Widerrufbare Plugin-Freigaben

## Zweck
Eine Plugin-Freigabe gilt nur für exakt den geprüften Pluginzustand.

## Gebundene Identität
- Plugin-ID
- Plugin-Version
- signierter Inhalts-Hash
- Signaturschlüssel
- Capability
- Hash des sichtbaren Berechtigungsprofils

## Status
- `active` – unverändert freigegeben
- `revoked` – ausdrücklich widerrufen
- `expired` – automatisch nach Vertragsänderung abgelaufen

## Speicherort
Die Freigaben liegen XDG-konform im Benutzerzustand als private Datei `plugin_approvals.json` und werden atomisch geschrieben.

## Sicherheitsregel
Jede Änderung an Version, Inhalt, Schlüssel, Capability oder Berechtigungen macht die Freigabe automatisch ungültig. Das Plugin bleibt inaktiv, bis Berechtigungen erneut sichtbar geprüft und bestätigt wurden.
