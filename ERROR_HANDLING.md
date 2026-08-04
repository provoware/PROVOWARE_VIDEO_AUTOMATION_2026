# Fehlerhandling – 2.8.0

## Grundstruktur

Jeder Fehler erklärt Ursache, Auswirkung, automatische Schutzmaßnahme, empfohlene Lösung und sichere Alternative.

## Neue Schutzfälle

- **PLUGIN_APPROVAL_EXPIRED** – Pluginidentität oder Berechtigungen haben sich geändert; Freigabe wird automatisch deaktiviert.
- **PLUGIN_APPROVAL_REVOKED** – Nutzer hat Freigabe widerrufen; erneute Vollprüfung erforderlich.
- **VISUAL_APPROVAL_MISSING** – RC bleibt prüfbar, Stable-Freigabe wird blockiert.
- **VISUAL_APPROVAL_EXPIRED** – Manifest, Referenzbilder oder Prüfbericht wurden nach Signatur geändert.
- **VISUAL_APPROVAL_INVALID** – Signatur oder Schlüsselmaterial ist ungültig.
- **DIAGNOSTIC_REPORT_WRITE_FAILED** – Anwendung bleibt nutzbar; alternativer Logpfad wird angeboten.

Automatische Selbstheilung darf niemals eine Sicherheitsfreigabe erfinden oder reaktivieren.
