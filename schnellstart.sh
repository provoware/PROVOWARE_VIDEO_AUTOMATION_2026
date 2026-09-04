#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [[ -x "$ROOT/STARTEN.sh" ]]; then
  exec "$ROOT/STARTEN.sh" "$@"
fi

if [[ -x "$ROOT/start.sh" ]]; then
  exec "$ROOT/start.sh" "$@"
fi

exec bash "$ROOT/STARTEN.sh" "$@"
