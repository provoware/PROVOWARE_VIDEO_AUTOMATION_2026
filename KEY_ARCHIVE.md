# Verschlüsseltes Freigabeschlüsselarchiv

## Verfahren

- KDF: Scrypt
- Verschlüsselung: AES-256-GCM
- Integrität: authentifizierte Verschlüsselung
- Dateirechte: 0600
- Format: `.pvak`

## Sicherung

```bash
./start.sh --backup-approval-key --output /mnt/offline/provoware_visual_key.pvak
```

## Verifikation

```bash
PYTHONPATH=src python scripts/archive_visual_approval_key.py --verify /mnt/offline/provoware_visual_key.pvak
```

Archiv und Kennwort niemals am selben Ort aufbewahren. Der private Schlüssel wird nicht in Release- oder Updatepakete aufgenommen.
