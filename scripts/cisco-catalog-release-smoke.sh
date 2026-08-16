#!/usr/bin/env bash
set -euo pipefail

cd /home/felipe/unidac-lab

TMP_INSTANCE="ulab-iol-ui-smoke"
SOCKET="/run/unidac-lab/agent.sock"

cleanup() {
    python3 - "$SOCKET" "$TMP_INSTANCE" <<'PY' >/dev/null 2>&1 || true
import json
import socket
import sys

sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
sock.connect(sys.argv[1])
request = {
    "mode": "exec",
    "argv": ["iol-remove", sys.argv[2]],
}
sock.sendall((json.dumps(request) + "\n").encode())
try:
    sock.recv(65536)
except Exception:
    pass
sock.close()
PY
}
trap cleanup EXIT

python3 <<'PY'
import json
import urllib.request

with urllib.request.urlopen(
    "http://127.0.0.1:8000/api/catalog/devices",
    timeout=15,
) as response:
    data = json.load(response)

devices = {
    item["id"]: item
    for item in data.get("devices", [])
}

for device_id in (
    "cisco-iol-l2-switch",
    "cisco-iol-l3-switch",
):
    device = devices.get(device_id)
    assert device is not None, device_id
    assert device["runtime"] == "iol"
    assert device["enabled"] is True
    assert device["availability"] == "available"

print("Catalog L2/L3 released: PASS")
PY

python3 - "$SOCKET" "$TMP_INSTANCE" <<'PY'
import json
import socket
import sys

socket_path = sys.argv[1]
instance = sys.argv[2]


def call(argv):
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(socket_path)
    sock.sendall(
        (json.dumps({"mode": "exec", "argv": argv}) + "\n").encode()
    )

    data = bytearray()
    while b"\n" not in data:
        chunk = sock.recv(65536)
        if not chunk:
            break
        data.extend(chunk)
    sock.close()

    envelope = json.loads(bytes(data).split(b"\n", 1)[0].decode())
    assert envelope["ok"] is True, envelope
    assert envelope["returncode"] == 0, envelope
    payload = json.loads(envelope["stdout"])
    return payload

call(["iol-remove", instance])

result = call([
    "iol-ensure",
    instance,
    "cisco-iol-l2-switch",
    "256",
    "8",
])
assert result["status"] in {"prepared", "exists"}, result

status = call(["iol-status", instance])
assert status["status"] == "exists", status
assert status["running"] is False, status

result = call(["iol-remove", instance])
assert result.get("status") in {"removed", "missing"}, result

print("AgentD IOL prepare/status/remove: PASS")
print("Cisco executable started by smoke: FALSE")
PY

python3 <<'PY'
import json
import urllib.request

with urllib.request.urlopen(
    "http://127.0.0.1:8000/api/lab/apply-plan",
    timeout=15,
) as response:
    plan = json.load(response)

assert plan.get("ready") is True, plan
print(
    "Existing lab Apply Plan: PASS",
    plan.get("summary"),
)
PY

grep -q 'iol-status' agent/unidac-lab-agent
grep -q 'domain_name.startswith("iol:")' agent/unidac-lab-agentd
grep -q 'create-iol' backend/app/apply_plan_service.py
grep -q 'reuse-iol' backend/app/console_service.py
grep -q "device?.runtime === 'iol'" frontend/src/components/NodePropertiesPanel.jsx
grep -q "'/api/lab/iol/nodes'" frontend/src/App.jsx

echo "Static IOL UI wiring: PASS"
echo "CISCO CATALOG RELEASE SMOKE = PASS"
