#!/bin/sh
# Sicherer Einsteigerstart unabhängig vom aktuellen Arbeitsverzeichnis.
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec "$SCRIPT_DIR/../STARTEN.sh" "$@"
