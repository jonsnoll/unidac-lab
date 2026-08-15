#!/bin/sh
set -eu

IMAGE="${1:-/images/base.bin}"

echo "=========================================="
echo " UNIDAC-LAB IOL COMPATIBILITY SANDBOX"
echo "=========================================="

if [ ! -f "$IMAGE" ]; then
    echo "ERROR: image not found: $IMAGE"
    exit 1
fi

echo
echo "===== LOADER ====="
ls -l /lib/ld-linux.so.2

echo
echo "===== LEGACY CRYPTO ====="
ls -l /usr/lib/libcrypto.so.4
readlink -f /usr/lib/libcrypto.so.4

echo
echo "===== LDD ====="

LDD_OUTPUT="$(
    ldd "$IMAGE" 2>&1 \
    || true
)"

printf '%s\n' "$LDD_OUTPUT"

if printf '%s\n' "$LDD_OUTPUT" \
  | grep -Fq 'not found'; then
    echo
    echo "IOL COMPAT SANDBOX = FAIL"
    exit 1
fi

echo
echo "IOL COMPAT SANDBOX = PASS"
echo "Cisco executable was NOT started."
