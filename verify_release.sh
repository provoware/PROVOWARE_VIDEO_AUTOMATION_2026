#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

case "${1:-}" in
  "")
    exec "$ROOT_DIR/test.sh" --local
    ;;
  --strict)
    shift
    [[ $# -eq 0 ]] || { printf 'Unbekannte Zusatzoption: %s\n' "$1" >&2; exit 2; }
    exec "$ROOT_DIR/test.sh"
    ;;
  --core)
    shift
    [[ $# -eq 0 ]] || { printf 'Unbekannte Zusatzoption: %s\n' "$1" >&2; exit 2; }
    exec "$ROOT_DIR/test.sh" --core
    ;;
  --help|-h)
    cat <<'EOF'
Verwendung: ./verify_release.sh [--strict | --core]

  ohne Option  Lokale Qualitätsprüfung mit vorhandener bestätigter Umgebung.
  --strict     Reproduzierbare Releaseprüfung inklusive Wheelhouse und Signaturen.
  --core       Kernprüfung ohne externe Qualitätswerkzeuge.
EOF
    ;;
  *)
    printf 'Unbekannte Option: %s\n' "$1" >&2
    exit 2
    ;;
esac
