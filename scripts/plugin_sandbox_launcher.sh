#!/usr/bin/env bash
set -euo pipefail

ROOT="$1"
PYTHON_PATH="$2"
HOST_DIR="$3"
PLUGIN_DIR="$4"
CAPABILITY="$5"
PAYLOAD="$6"

mkdir -p "$ROOT"/{usr,lib,lib64,opt/pyvenv,app,plugin,tmp,dev}

bind_ro() {
  local source="$1" target="$2"
  [ -e "$source" ] || return 0
  mount --bind "$source" "$target"
  mount -o remount,bind,ro,nosuid,nodev "$target"
}

bind_ro /usr "$ROOT/usr"
bind_ro /lib "$ROOT/lib"
bind_ro /lib64 "$ROOT/lib64"
bind_ro /opt/pyvenv "$ROOT/opt/pyvenv"
bind_ro "$HOST_DIR" "$ROOT/app"
bind_ro "$PLUGIN_DIR" "$ROOT/plugin"
mount -t tmpfs -o size=16m,nosuid,nodev,noexec tmpfs "$ROOT/tmp"
for device in null urandom random; do
  if [ -e "/dev/$device" ]; then
    touch "$ROOT/dev/$device"
    mount --bind "/dev/$device" "$ROOT/dev/$device"
    mount -o remount,bind,ro,nosuid,nodev "$ROOT/dev/$device" || true
  fi
done

export HOME=/tmp
export TMPDIR=/tmp
export PYTHONDONTWRITEBYTECODE=1
export VIDEOBATCH_CHROOT_SANDBOX=1

chroot "$ROOT" "$PYTHON_PATH" -I /app/plugin_host.py /plugin "$CAPABILITY" "$PAYLOAD"
