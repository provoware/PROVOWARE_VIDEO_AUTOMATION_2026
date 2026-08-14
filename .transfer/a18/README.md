# A18 verified source transfer

Dieser Transferzweig ist ausschließlich der kontrollierte Transportweg für die vollständige reproduzierbare A18-Git-Quellbasis.

- Quelle: `I009/A18`
- Git-Quellvertrag: V2
- Scope: `772` Dateien
- Scope-SHA-256: `a67355cec422be9affb95618ebfd6e761c801db7822a2516ad0b8739a7c8e435`
- Transport: `tar.zst`, Zstandard -19
- Transport-SHA-256: `8b15c4bff6a141f5afa94bdbe3ca85fd472d2f4064cedd2a9ea6698e6b312a40`
- Transferteile: `6`
- Staging: `staging/i009-a18-github-bindung-20260814`
- Ziel: `i009-pagination-adaptive-rail-20260813`

Der Workflow reagiert ausschließlich auf `.transfer/a18/TRANSFER_READY`. Dadurch können alle Transportteile vorher ohne vorzeitigen Import hochgeladen werden.

Exit-Kriterium: Remote-Parität PASS + `GITHUB_BINDUNGSBELEG.json` PASS + `I010_GATE=FREIGEGEBEN`.
