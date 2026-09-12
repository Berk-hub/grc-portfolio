#!/bin/sh
# Runs energy/scripts/backend-link-proxy.py inside the relay container.
#
# The repository script binds 127.0.0.1 on both sides, which is right for the
# single-host v1 lab but not for a container network. Instead of editing the
# script (its hash is part of the evidence), this entrypoint rewrites the four
# host/port constants into a copy and refuses to start if any rewrite misses.
set -eu

SRC=/lab/backend-link-proxy.py
DST=/tmp/backend-link-proxy.py

LISTEN_HOST="${RELAY_LISTEN_HOST:-0.0.0.0}"
LISTEN_PORT="${RELAY_LISTEN_PORT:-18081}"
TARGET_HOST="${RELAY_TARGET_HOST:-backend-edge}"
TARGET_PORT="${RELAY_TARGET_PORT:-8081}"

for needle in 'LISTEN_HOST = "127.0.0.1"' 'LISTEN_PORT = 18081' \
              'TARGET_HOST = "127.0.0.1"' 'TARGET_PORT = 8081'; do
    if ! grep -qF "$needle" "$SRC"; then
        echo "relay: expected line not found in $SRC: $needle" >&2
        exit 64
    fi
done

sed \
    -e "s|^LISTEN_HOST = \"127.0.0.1\"|LISTEN_HOST = \"$LISTEN_HOST\"|" \
    -e "s|^LISTEN_PORT = 18081|LISTEN_PORT = $LISTEN_PORT|" \
    -e "s|^TARGET_HOST = \"127.0.0.1\"|TARGET_HOST = \"$TARGET_HOST\"|" \
    -e "s|^TARGET_PORT = 8081|TARGET_PORT = $TARGET_PORT|" \
    "$SRC" > "$DST"

echo "relay: source sha256 $(sha256sum "$SRC" | cut -d' ' -f1)"
echo "relay: $LISTEN_HOST:$LISTEN_PORT -> $TARGET_HOST:$TARGET_PORT"
exec python3 -u "$DST"
