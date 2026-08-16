#!/usr/bin/env bash
set -euo pipefail

cd /home/felipe/unidac-lab

IMAGE="images/store/cisco/cisco-iol-l3-switch/base.bin"
META="images/metadata/cisco-iol-l3-switch.json"
CATALOG="catalog/devices/cisco/iol-l3-switch.json"
EXPECTED_SHA="dc74c28bfb45e8298ce220aedb21940d1f5e7c5d1967d13da5e339741c9619a9"

test -s "$IMAGE"
test -s "$META"
test -s "$CATALOG"

python3 - <<'PY'
import hashlib
import json
from pathlib import Path

image = Path("images/store/cisco/cisco-iol-l3-switch/base.bin")
meta = json.loads(Path("images/metadata/cisco-iol-l3-switch.json").read_text())
catalog = json.loads(Path("catalog/devices/cisco/iol-l3-switch.json").read_text())

digest = hashlib.sha256(image.read_bytes()).hexdigest()
assert digest == "dc74c28bfb45e8298ce220aedb21940d1f5e7c5d1967d13da5e339741c9619a9"
assert digest == meta["integrity"]["sha256"]
assert meta["format"] == "bin"
assert meta["deployment"] == "iol-executable"
assert meta["validation"]["core_boot"] is True
assert meta["validation"]["console"] is True
assert meta["validation"]["dataplane"] is False
assert meta["validation"]["automatic_ios_configuration"] is False
assert catalog["id"] == "cisco-iol-l3-switch"
assert catalog["runtime"] == "iol"
assert catalog["enabled"] is False
assert catalog["availability"] == "coming-soon"

print("L3 SHA256        : PASS")
print("L3 core boot     : PASS")
print("L3 console       : PASS")
print("L3 auto config   : FALSE")
print("L3 dataplane     : PENDING")
print("L3 catalog gate  : PASS")
PY

echo "CISCO IOL L3 CORE SMOKE = PASS"
