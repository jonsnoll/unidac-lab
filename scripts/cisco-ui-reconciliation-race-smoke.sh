#!/usr/bin/env bash
set -euo pipefail

cd /home/felipe/unidac-lab

python3 <<'PY'
from pathlib import Path

text = Path(
    "frontend/src/App.jsx"
).read_text(
    encoding="utf-8"
)

topology_start = text.find(
    "  const refreshRuntimeStates ="
)

iol_start = text.find(
    "async function refreshIolRuntimeStates()",
    topology_start,
)

if topology_start < 0:
    raise SystemExit(
        "refreshRuntimeStates missing"
    )

if iol_start < 0:
    raise SystemExit(
        "refreshIolRuntimeStates missing"
    )

topology = text[
    topology_start:iol_start
]

if "'/api/lab/topology'" not in topology:
    raise SystemExit(
        "Topology endpoint missing"
    )

if "?.runtime === 'iol'" not in topology:
    raise SystemExit(
        "IOL exclusion missing from topology poll"
    )

iol_poll = text[
    iol_start:
]

if "'/api/lab/apply-plan'" not in iol_poll:
    raise SystemExit(
        "Apply Plan endpoint missing from IOL poll"
    )

print("PASS topology poll excludes IOL")
print("PASS IOL poll owns IOL runtime state")
PY

curl -fsS \
  http://127.0.0.1:8000/api/lab/apply-plan \
  > /tmp/unidac-cisco-ui-race-smoke-plan.json

python3 <<'PY'
import json
from pathlib import Path

plan = json.loads(
    Path(
        "/tmp/unidac-cisco-ui-race-smoke-plan.json"
    ).read_text(
        encoding="utf-8"
    )
)

iol = [
    action
    for action in plan.get("actions", [])
    if str(
        action.get(
            "runtime_id",
            "",
        )
    ).startswith("iol:")
]

if len(iol) < 2:
    raise SystemExit(
        "Expected at least two IOL actions"
    )

for action in iol:
    if action.get("runtime_state") != "running":
        raise SystemExit(
            f"{action.get('node_name')} is not running"
        )

    print(
        "PASS",
        action.get("node_name"),
        action.get("runtime_state"),
    )

print("CISCO UI RECONCILIATION RACE SMOKE = PASS")
PY
