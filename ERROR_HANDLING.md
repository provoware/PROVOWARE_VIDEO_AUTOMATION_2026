# Fehlerhandling

## Grundstruktur

Jeder Fehler erklärt Ursache, Auswirkung, automatische Schutzmaßnahme, empfohlene Lösung und sichere Alternative.

Die zentrale Fehlerauflösung bleibt auch dann nutzbar, wenn das Fehlerregister fehlt,
nicht lesbar oder in einzelnen Feldern beschädigt ist. In diesem Fall wird eine
vollständige, sichere Standarderklärung mit der Aktion „Protokolle öffnen“ gezeigt.
Unbekannte Schweregrade werden als blockierend behandelt. Der Lösungsdialog zeigt
den Zustand in einfacher Sprache als „Hinweis“, „Warnung“ oder „Vorgang gestoppt“.

## Neue Schutzfälle

- **PLUGIN_APPROVAL_EXPIRED** – Pluginidentität oder Berechtigungen haben sich geändert; Freigabe wird automatisch deaktiviert.
- **PLUGIN_APPROVAL_REVOKED** – Nutzer hat Freigabe widerrufen; erneute Vollprüfung erforderlich.
- **VISUAL_APPROVAL_MISSING** – RC bleibt prüfbar, Stable-Freigabe wird blockiert.
- **VISUAL_APPROVAL_EXPIRED** – Manifest, Referenzbilder oder Prüfbericht wurden nach Signatur geändert.
- **VISUAL_APPROVAL_INVALID** – Signatur oder Schlüsselmaterial ist ungültig.
- **DIAGNOSTIC_REPORT_WRITE_FAILED** – Anwendung bleibt nutzbar; alternativer Logpfad wird angeboten.

Automatische Selbstheilung darf niemals eine Sicherheitsfreigabe erfinden oder reaktivieren.
