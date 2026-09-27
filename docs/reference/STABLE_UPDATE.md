# Stable-Update 2.8.0

## Ausgang

```text
2.8.0-rc1
```

## Ziel

```text
2.8.0 stable
```

## Bindung

Das Update-Manifest enthält:

- `visual_contract_sha256`
- `baseline_bundle_sha256`
- `approval_sha256`
- `approval_key_id`
- `build_id`

Vor der Installation werden Pfade, Dateihashes und die visuelle Bindung geprüft. Danach wird eine Kandidatenkopie erzeugt, vollständig getestet und erst dann atomisch aktiviert. Eine Rückrollkopie bleibt erhalten.
