#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="${1:-$ROOT_DIR/dist}"
VERSION="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["version"])' "$ROOT_DIR/VERSION.json")"
CHANNEL="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["channel"])' "$ROOT_DIR/VERSION.json")"
if [[ "$CHANNEL" != "stable" ]]; then
  printf 'STABLE BLOCKIERT: Dieser Build ist %s; erwartet stable.\n' "$CHANNEL" >&2
  printf 'Zuerst vollständig prüfen: ./videobatch.sh verify\n' >&2
  printf 'Danach Desktopfreigabe signieren und einen eigenen Stable-Build erzeugen.\n' >&2
  exit 12
fi
python3 "$ROOT_DIR/scripts/toolchain.py" prepare --scope quality --auto-repair --quiet
python3 "$ROOT_DIR/scripts/toolchain.py" gate --scope quality --run-external --quiet
export VIDEOBATCH_QUALITY_ALREADY_VERIFIED=1
"$ROOT_DIR/test.sh"
ENV_PYTHON="$(python3 "$ROOT_DIR/scripts/toolchain.py" path --scope quality --quiet)"
"$ENV_PYTHON" "$ROOT_DIR/scripts/check_visual_approval.py" --require
"$ENV_PYTHON" "$ROOT_DIR/scripts/build_release_manifest.py"
"$ENV_PYTHON" "$ROOT_DIR/scripts/validate_release_manifest.py"
mkdir -p "$OUTPUT_DIR"
TMP_DIR="$(mktemp -d -t videobatch-stable-XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT
A="$TMP_DIR/VideoBatch_Fast_${VERSION}-a.zip"
B="$TMP_DIR/VideoBatch_Fast_${VERSION}-b.zip"
"$ENV_PYTHON" "$ROOT_DIR/scripts/package_release.py" --output "$A"
"$ENV_PYTHON" "$ROOT_DIR/scripts/package_release.py" --output "$B"
cmp --silent "$A" "$B" || { printf 'STABLE BLOCKIERT: Doppelpaketierung ist nicht byteidentisch.\n' >&2; exit 13; }
FINAL="$OUTPUT_DIR/VideoBatch_Fast_${VERSION}.zip"
cp "$A" "$FINAL"
sha256sum "$FINAL" > "$FINAL.sha256"
printf 'STABLE ERZEUGT: %s\n' "$FINAL"
cat "$FINAL.sha256"
