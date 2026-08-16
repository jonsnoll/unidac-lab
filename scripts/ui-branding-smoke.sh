#!/usr/bin/env bash
set -euo pipefail

cd /home/felipe/unidac-lab

grep -Fq '<title>unidac-lab</title>' frontend/index.html
grep -Fq 'Felipe Gaia' frontend/src/App.jsx
grep -Fq 'className="local-user-badge"' frontend/src/App.jsx
grep -Fq '.local-user-badge {' frontend/src/App.css

grep -Fq 'LAB_ID = "vxlan-fgt-01"' backend/app/apply_plan_service.py

python3 <<'PY'
import json
from pathlib import Path

expected = {
    "catalog/devices/cisco/iol-l2-switch.json": "L2 Switch",
    "catalog/devices/cisco/iol-l3-switch.json": "L3 Router",
}

for filename, name in expected.items():
    data = json.loads(
        Path(filename).read_text(encoding="utf-8")
    )

    if data.get("name") != name:
        raise SystemExit(
            f"{filename}: nome incorreto: {data.get('name')!r}"
        )

    if data.get("enabled") is not True:
        raise SystemExit(
            f"{filename}: template nao esta enabled"
        )

    print(f"PASS {name}")

print("Internal lab id preserved: PASS")
print("UI BRANDING SMOKE = PASS")
PY
