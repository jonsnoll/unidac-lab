#!/usr/bin/env bash
set -euo pipefail

cd /home/felipe/unidac-lab

grep -Fq \
  "async function refreshIolRuntimeStates()" \
  frontend/src/App.jsx

grep -Fq \
  "action.runtime_id.startsWith(" \
  frontend/src/App.jsx

grep -Fq \
  "window.location.reload()" \
  frontend/src/App.jsx

grep -Fq \
  "{(isQemu || isIol) && runtimeAvailable && (" \
  frontend/src/components/NodePropertiesPanel.jsx

curl -fsS \
  http://127.0.0.1:8000/api/lab/apply-plan \
  > /tmp/unidac-cisco-ui-smoke-plan.json

python3 <<'PY'
import json
from pathlib import Path

plan = json.loads(
    Path(
        "/tmp/unidac-cisco-ui-smoke-plan.json"
    ).read_text(
        encoding="utf-8"
    )
)

actions = [
    action
    for action in plan.get("actions", [])
    if action.get("runtime_id", "").startswith("iol:")
]

if len(actions) < 2:
    raise SystemExit(
        f"Esperava 2 IOL runtimes; encontrei {len(actions)}"
    )

for action in actions:
    if action.get("runtime_state") != "running":
        raise SystemExit(
            f"{action.get('node_name')} != running"
        )

    if action.get("action") != "reuse-iol":
        raise SystemExit(
            f"{action.get('node_name')} nao esta reuse-iol"
        )

    print(
        f"PASS {action.get('node_name')}: "
        f"{action.get('runtime_id')} running"
    )

print("CISCO UI RECONCILIATION SMOKE = PASS")
PY
