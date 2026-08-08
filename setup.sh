#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
args=()
mode="setup"
for arg in "$@"; do
  case "$arg" in
    --runtime|--quality|--allow-online) ;; # alte Aufrufe bleiben gültig
    --check) mode="check" ;;
    --offline-only|--replace) args+=("$arg") ;;
    *) printf 'Unbekannte Option: %s\n' "$arg" >&2; exit 2 ;;
  esac
done
exec "$ROOT_DIR/videobatch.sh" "$mode" "${args[@]}"
