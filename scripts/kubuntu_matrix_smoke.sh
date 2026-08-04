#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
export PYTHONPATH="$ROOT/src" PYTHONDONTWRITEBYTECODE=1
python3 "$ROOT/scripts/check_release_literal_hygiene.py" \
  --report "$ROOT/RELEASE_LITERAL_HYGIENE.json"
python3 -m pytest -q
bash "$ROOT/videobatch.sh" fault-lab
python3 "$ROOT/scripts/validate_version_contract.py"
python3 "$ROOT/scripts/validate_text_resources.py"
ffmpeg -hide_banner -loglevel error -f lavfi -i sine=frequency=880:duration=0.2 -c:a aac -f null -

EVIDENCE_STAGE="$ROOT/dist-matrix-live-evidence"
EVIDENCE_ITEMS=(matrix-logs FFMPEG_TOOLCHAIN.json RELEASE_LITERAL_HYGIENE.json)
restore_matrix_evidence() {
  local item
  for item in "${EVIDENCE_ITEMS[@]}"; do
    if [[ -e "$EVIDENCE_STAGE/$item" ]]; then
      rm -rf -- "$ROOT/$item"
      mv -- "$EVIDENCE_STAGE/$item" "$ROOT/$item"
    fi
  done
  rmdir -- "$EVIDENCE_STAGE" 2>/dev/null || true
}
rm -rf -- "$EVIDENCE_STAGE"
mkdir -p -- "$EVIDENCE_STAGE"
for item in "${EVIDENCE_ITEMS[@]}"; do
  if [[ -e "$ROOT/$item" ]]; then
    mv -- "$ROOT/$item" "$EVIDENCE_STAGE/$item"
  fi
done
trap restore_matrix_evidence EXIT

MEDIA_ARGS=()
if [[ -n "${VIDEOBATCH_STATIC_MEDIA_DIR:-}" ]]; then MEDIA_ARGS=(--static-media-dir "$VIDEOBATCH_STATIC_MEDIA_DIR"); fi
python3 "$ROOT/scripts/build_portable_bundle.py" --output-dir "$ROOT/dist-matrix-a" "${MEDIA_ARGS[@]}"
python3 "$ROOT/scripts/build_portable_bundle.py" --output-dir "$ROOT/dist-matrix-b" "${MEDIA_ARGS[@]}"
python3 "$ROOT/scripts/verify_portable_reproducibility.py" \
  --first "$ROOT/dist-matrix-a" \
  --second "$ROOT/dist-matrix-b" \
  --report "$ROOT/dist-matrix-a/KUBUNTU_REPRODUCIBILITY.json"
