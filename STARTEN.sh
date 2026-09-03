#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
BOOTSTRAP_PYTHON="${VIDEOBATCH_BOOTSTRAP_PYTHON:-python3}"

case "${1:-}" in
  -h|--help|hilfe|--hilfe)
    exec bash "$ROOT_DIR/start.sh" --help
    ;;
esac

if ! command -v "$BOOTSTRAP_PYTHON" >/dev/null 2>&1; then
  printf '%s\n' \
    "FEHLER: Python 3 wurde nicht gefunden." \
    "VideoBatch wurde nicht gestartet; Originalmedien wurden nicht verändert." \
    "Lösung: Python 3 installieren oder VIDEOBATCH_BOOTSTRAP_PYTHON auf einen gültigen Python-3-Befehl setzen." \
    "Danach: bash start.sh --doctor" >&2
  exit 127
fi

exec "$BOOTSTRAP_PYTHON" "$ROOT_DIR/scripts/debug_launcher.py" "$@"
