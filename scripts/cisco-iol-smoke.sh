#!/usr/bin/env bash
set -euo pipefail

cd /home/felipe/unidac-lab

IMAGE_ID="cisco-iol-l2-adventerprise-15-1-20140814"
IMAGE="images/store/cisco/$IMAGE_ID/base.bin"
META="images/metadata/$IMAGE_ID.json"
CATALOG="catalog/devices/cisco/iol-l2-switch.json"

echo
echo "=================================================="
echo " CISCO IOL FOUNDATION SMOKE"
echo "=================================================="

test -s "$IMAGE"
test -f "$META"
test -f "$CATALOG"
test -e /lib/ld-linux.so.2

FILE_INFO="$(file "$IMAGE")"

printf '%s\n' "$FILE_INFO"

printf '%s\n' "$FILE_INFO" \
  | grep -q 'ELF 32-bit LSB executable, Intel 80386'

python3 <<'PY'
import hashlib
import json
from pathlib import Path

image_id = "cisco-iol-l2-adventerprise-15-1-20140814"

image = Path(
    f"images/store/cisco/{image_id}/base.bin"
)

metadata = json.loads(
    Path(
        f"images/metadata/{image_id}.json"
    ).read_text(
        encoding="utf-8"
    )
)

catalog = json.loads(
    Path(
        "catalog/devices/cisco/iol-l2-switch.json"
    ).read_text(
        encoding="utf-8"
    )
)

digest = hashlib.sha256(
    image.read_bytes()
).hexdigest()

if digest != metadata["integrity"]["sha256"]:
    raise SystemExit(
        "SHA256 mismatch"
    )

if metadata["format"] != "bin":
    raise SystemExit(
        "Unexpected image format"
    )

if metadata["deployment"] != "iol-executable":
    raise SystemExit(
        "Unexpected deployment"
    )

if catalog["runtime"] != "iol":
    raise SystemExit(
        "Unexpected runtime provider"
    )

if catalog.get("enabled") is not False:
    raise SystemExit(
        "IOL template must remain disabled "
        "until runtime provider is ready"
    )

print("Metadata SHA256: PASS")
print("Catalog runtime : PASS")
PY

LDD_OUT="$(ldd "$IMAGE" 2>&1 || true)"

printf '%s\n' "$LDD_OUT"

if printf '%s\n' "$LDD_OUT" \
  | grep -Fq 'libcrypto.so.4 => not found'; then
    echo
    echo "CISCO IOL HOST LIBS = PARTIAL"
    echo "libcrypto.so.4 sera tratada em userspace isolado."
else
    echo
    echo "CISCO IOL HOST LIBS = PASS"
fi

echo "CISCO IOL FOUNDATION SMOKE = PASS"
