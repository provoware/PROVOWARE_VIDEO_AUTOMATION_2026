#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
action="${1:-prepare}"
if [[ $# -gt 0 ]]; then shift; fi
case "$action" in
  gate) exec python3 "$ROOT_DIR/scripts/toolchain.py" gate --scope runtime "$@" ;;
  status) exec python3 "$ROOT_DIR/scripts/toolchain.py" status "$@" ;;
  prepare) exec python3 "$ROOT_DIR/scripts/toolchain.py" prepare --scope runtime --auto-repair "$@" ;;
  build) exec python3 "$ROOT_DIR/scripts/toolchain.py" build --scope runtime --allow-online "$@" ;;
  contract|verify|install) exec python3 "$ROOT_DIR/scripts/toolchain.py" "$action" --scope runtime "$@" ;;
  *) printf 'Unbekannte Aktion: %s\n' "$action" >&2; exit 2 ;;
esac
