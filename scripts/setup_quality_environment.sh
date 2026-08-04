#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
case "${1:-}" in
  --online|--allow-online)
    exec "$ROOT_DIR/quality-toolchain.sh" prepare --allow-online
    ;;
  "")
    exec "$ROOT_DIR/quality-toolchain.sh" prepare
    ;;
  *)
    printf 'Unbekannte Option: %s\n' "$1" >&2
    printf 'Verwendung: %s [--allow-online]\n' "$0" >&2
    exit 2
    ;;
esac
