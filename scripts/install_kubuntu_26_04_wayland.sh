#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
    SUDO=()
else
    SUDO=(sudo)
fi

printf '%s\n' \
  'VideoBatch Fast – Kubuntu 26.04 / Wayland Vorbereitung' \
  'Es werden nur benötigte Systempakete ergänzt; vorhandene Dateien werden nicht gelöscht.'

"${SUDO[@]}" apt-get update
"${SUDO[@]}" apt-get install -y --no-install-recommends \
  python3 \
  python3-tk \
  ffmpeg \
  xwayland \
  wl-clipboard \
  xdg-utils \
  xdg-desktop-portal \
  xdg-desktop-portal-kde \
  libnotify-bin

printf '\n%s\n' 'Systempakete geprüft. VideoBatch-Plattformtest folgt:'
exec python3 "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/kubuntu_26_04_wayland_check.py"
