#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="$ROOT_DIR/src:$ROOT_DIR/scripts${PYTHONPATH:+:$PYTHONPATH}"
exec python3 "$ROOT_DIR/scripts/stable_operator.py" "$@"
