#!/usr/bin/env bash
set -euo pipefail

cd /home/felipe/unidac-lab

python3 <<'PY'
import hashlib
import json
from pathlib import Path

image = Path("images/store/cisco/cisco-iol-l3-switch/base.bin")
meta = json.loads(Path("images/metadata/cisco-iol-l3-switch.json").read_text())
catalog = json.loads(Path("catalog/devices/cisco/iol-l3-switch.json").read_text())

assert image.is_file()
digest = hashlib.sha256(image.read_bytes()).hexdigest()
assert digest == "dc74c28bfb45e8298ce220aedb21940d1f5e7c5d1967d13da5e339741c9619a9"
assert digest == meta["integrity"]["sha256"]
assert meta["validation"]["core_boot"] is True
assert meta["validation"]["console"] is True
assert meta["validation"]["dataplane"] is False
assert meta["validation"]["automatic_ios_configuration"] is False
assert catalog["id"] == "cisco-iol-l3-switch"
assert catalog["runtime"] == "iol"
assert catalog["enabled"] is True
assert catalog["availability"] == "available"

print("L3 image/core/console : PASS")
print("L3 catalog released   : PASS")
print("L3 automatic config   : FALSE")
print("L3 dataplane          : PENDING")
PY

echo "CISCO IOL L3 RELEASE SMOKE = PASS"
