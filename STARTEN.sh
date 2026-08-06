#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
BOOTSTRAP_PYTHON="${VIDEOBATCH_BOOTSTRAP_PYTHON:-python3}"
exec "$BOOTSTRAP_PYTHON" "$ROOT_DIR/scripts/debug_launcher.py" "$@"
