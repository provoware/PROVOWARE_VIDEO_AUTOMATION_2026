# A18 verified source transfer

Dieser Transferzweig ist ausschließlich der kontrollierte Transportweg für die vollständige reproduzierbare A18-Git-Quellbasis.

- Quelle: `I009/A18`
- Git-Quellvertrag: V2
- Scope: `772` Dateien
- Scope-SHA-256: `ba62a986d88405d21264d05853ee0086df876c012b0dc6a9c55e9b37ecaff591`
- Transport: `tar.zst`, Zstandard -19
- Transport-SHA-256: `3c0051bca07deff0243dd42fb59f37f33a1d1e958c320268a890e4c79fd96df4`
- Transferteile: `6`
- Staging: `staging/i009-a18-github-bindung-20260814`
- Ziel: `i009-pagination-adaptive-rail-20260813`

Der Workflow reagiert ausschließlich auf `.transfer/a18/TRANSFER_READY`. Dadurch können alle Transportteile vorher ohne vorzeitigen Import hochgeladen werden.

Exit-Kriterium: Remote-Parität PASS + `GITHUB_BINDUNGSBELEG.json` PASS + `I010_GATE=FREIGEGEBEN`.
