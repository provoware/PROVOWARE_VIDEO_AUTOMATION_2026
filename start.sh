#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"

zeige_hilfe() {
  cat <<'EOF'
PROVOWARE VideoBatch Fast – sicherer Start

Einfach starten:
  ./start.sh

Vor dem Start prüfen:
  ./start.sh --status      Letzten Startstatus anzeigen
  ./start.sh --doctor      System und Startvoraussetzungen diagnostizieren
  ./start.sh --prepare     Sichere Einrichtung/Vorbereitung ausführen

Weitere Wartung:
  ./start.sh --repair      Reparaturfunktion starten
  ./start.sh --test        Tests starten
  ./start.sh --quality     Qualitätsprüfungen starten
  ./start.sh --assurance   Erweiterte Prüfungen starten

Hilfe:
  ./start.sh --help        Diese Übersicht anzeigen

Tipp: Bei einem Startproblem zuerst --doctor ausführen. Originalmedien werden dabei nicht verändert.
EOF
}

case "${1:-}" in
  -h|--help|hilfe|--hilfe) zeige_hilfe ;;
  --diagnose) shift; exec "$ROOT_DIR/videobatch.sh" doctor "$@" ;;
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
