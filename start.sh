#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
case "${1:-}" in
  --repair) shift; exec "$ROOT_DIR/videobatch.sh" repair "$@" ;;
  --prepare) shift; exec "$ROOT_DIR/videobatch.sh" setup "$@" ;;
  --test) shift; exec "$ROOT_DIR/videobatch.sh" test "$@" ;;
  --quality) shift; exec "$ROOT_DIR/videobatch.sh" quality "$@" ;;
  --assurance) shift; exec "$ROOT_DIR/videobatch.sh" assurance "$@" ;;
  --backup-approval-key) shift; exec "$ROOT_DIR/videobatch.sh" backup-approval-key "$@" ;;
  --status) shift; exec "$ROOT_DIR/videobatch.sh" startup-status "$@" ;;
  --doctor) shift; exec "$ROOT_DIR/videobatch.sh" doctor "$@" ;;
  "") exec "$ROOT_DIR/STARTEN.sh" ;;
  *) exec "$ROOT_DIR/STARTEN.sh" "$@" ;;
esac
