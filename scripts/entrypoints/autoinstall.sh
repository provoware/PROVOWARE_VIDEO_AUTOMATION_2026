#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
# Signaturprüfung im Python-Kern: openssl pkeyutl -verify · rollback · portable-smoke-test
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
if [[ -f "$SCRIPT_DIR/../ab_installer.py" ]]; then
  exec python3 "$SCRIPT_DIR/../ab_installer.py" --bundle-root "$SCRIPT_DIR/../.." "$@"
fi
exec python3 "$SCRIPT_DIR/ab_installer.py" --bundle-root "$SCRIPT_DIR" "$@"
