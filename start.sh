#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"

zeige_hilfe() {
  cat <<'EOF'
PROVOWARE VideoBatch Fast 2.8.3-rc24 – sicherer Schnellstart

Normal starten:
  ./start.sh

Prüfen und helfen:
  ./start.sh --doctor       System und Startvoraussetzungen prüfen
  ./start.sh --status       letzten Startstatus anzeigen
  ./start.sh --prepare      sichere Vorbereitung ausführen
  ./start.sh --repair       gezielte Reparatur ausführen

Qualität:
  ./start.sh --test         Tests starten
  ./start.sh --quality      Qualitätsprüfung starten
  ./start.sh --assurance    erweiterte Absicherung starten

Hilfe:
  ./start.sh --help         diese Übersicht anzeigen
  ./start.sh --hilfe        deutsche Kurzform

Empfehlung bei Problemen: zuerst --doctor, erst danach --repair.
Originalmedien werden durch die Startdiagnose nicht verändert.
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
