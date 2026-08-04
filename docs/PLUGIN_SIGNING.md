# Signierte Plugins

## Sicherheitsziel

Ein Plugin wird nur akzeptiert, wenn:

1. Manifest und Python-Code den statischen Plugin-Vertrag erfüllen,
2. alle Plugin-Dateien in der Signatur enthalten sind,
3. die Ed25519-Signatur gültig ist,
4. der öffentliche Schlüssel im Vertrauensregister aktiv ist,
5. der Schlüssel nicht widerrufen wurde,
6. der isolierte Selbsttest erfolgreich ist.

## Vertrauensregister

`registries/PLUGIN_TRUST_REGISTRY.json`

Das Paket enthält ausschließlich öffentliche Schlüssel. Private Signaturschlüssel dürfen niemals im Projekt, Plugin oder Release-ZIP liegen.

## Schlüsselpaar erzeugen

```bash
PYTHONPATH=src python scripts/generate_plugin_keypair.py \
  --private ~/sichere_keys/plugin_private.pem \
  --public ~/sichere_keys/plugin_public.pem
```


## Öffentlichen Schlüssel registrieren

```bash
PYTHONPATH=src python scripts/register_plugin_public_key.py \
  ~/sichere_keys/plugin_public.pem \
  --key-id mein-publisher-key \
  --publisher "Mein Herausgeber"
```

Das Werkzeug erstellt vorher eine Sicherung des Vertrauensregisters.

## Plugin signieren

```bash
PYTHONPATH=src python scripts/sign_plugin.py plugins/mein_plugin \
  --private-key ~/sichere_keys/plugin_private.pem \
  --key-id mein-publisher-key
```

## Signaturdatei

`plugin.sig.json` enthält:

- Algorithmus
- Schlüssel-ID
- Hash des kanonischen Signaturinhalts
- Dateiliste und SHA-256-Werte
- kryptografische Signatur
- Signaturzeitpunkt

## Manipulation

Nachträgliche Änderungen an `plugin.py`, `plugin.json` oder weiteren Plugin-Dateien machen die Signatur ungültig.

Das Tool:

- blockiert das Plugin,
- führt es nicht aus,
- verschiebt es in `plugins/quarantine/`,
- legt `QUARANTINE_REASON.txt` an,
- lässt die Kernanwendung weiterlaufen.

## Laufzeitisolation

Validator-Plugins werden zusätzlich mit:

```text
python -I plugin_host.py …
```

in einem separaten Prozess mit Zeitlimit ausgeführt.
