#!/usr/bin/env bash

set -u

ROOT_DIR="$(
    CDPATH= cd -- \
      "$(dirname -- "$0")/.." \
      && pwd
)"

cd "$ROOT_DIR" || exit 1

PASS_COUNT=0
WARN_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0

TMP_DIR="$(
    mktemp -d \
      /tmp/unidac-smoke.XXXXXX
)"

trap '
rm -rf "$TMP_DIR"
' EXIT


pass() {
    PASS_COUNT=$((PASS_COUNT + 1))
    printf 'PASS  %s\n' "$1"
}


warn() {
    WARN_COUNT=$((WARN_COUNT + 1))
    printf 'WARN  %s\n' "$1"
}


fail() {
    FAIL_COUNT=$((FAIL_COUNT + 1))
    printf 'FAIL  %s\n' "$1"
}


skip() {
    SKIP_COUNT=$((SKIP_COUNT + 1))
    printf 'SKIP  %s\n' "$1"
}


section() {
    echo
    echo "=================================================="
    echo " $1"
    echo "=================================================="
}


section "UNIDAC-LAB SMOKE TEST"


section "CONTROL PLANE"

for container in \
  unidac-lab-backend \
  unidac-lab-frontend
do
    if ! docker inspect \
      "$container" \
      >/dev/null 2>&1
    then
        fail "$container missing"
        continue
    fi

    STATUS="$(
        docker inspect \
          --format \
          '{{.State.Status}}' \
          "$container"
    )"

    HEALTH="$(
        docker inspect \
          --format \
          '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' \
          "$container"
    )"

    if [ "$STATUS" = "running" ] \
      && {
        [ "$HEALTH" = "healthy" ] \
        || [ "$HEALTH" = "none" ]
      }
    then
        pass \
          "$container $STATUS/$HEALTH"
    else
        fail \
          "$container $STATUS/$HEALTH"
    fi
done


section "HTTP"

HTTP_CODE="$(
    curl \
      -sS \
      -o "$TMP_DIR/index.html" \
      -w '%{http_code}' \
      http://127.0.0.1/ \
      2>/dev/null \
      || echo "000"
)"

if [ "$HTTP_CODE" = "200" ]; then
    pass "frontend HTTP 200"
else
    fail "frontend HTTP $HTTP_CODE"
fi


if grep -q \
  'id="root"' \
  "$TMP_DIR/index.html" \
  2>/dev/null
then
    pass "frontend HTML contains React root"
else
    fail "frontend HTML is unexpected"
fi


section "AGENTD"

if curl -fsS \
  http://127.0.0.1/api/lab/agent/health \
  > "$TMP_DIR/agent.json" \
  2>/dev/null
then
    if python3 - "$TMP_DIR/agent.json" <<'PY'
import json
import sys

with open(sys.argv[1]) as file:
    data = json.load(file)

assert data.get("status") == "ok"
assert data.get("component") == "unidac-lab-agent"
assert data.get("uid") == 0
PY
    then
        pass "backend -> AgentD"
    else
        fail "AgentD health payload invalid"
    fi
else
    fail "AgentD health endpoint failed"
fi


section "CATALOG"

if curl -fsS \
  http://127.0.0.1/api/catalog/devices \
  > "$TMP_DIR/catalog.json" \
  2>/dev/null
then
    if python3 - "$TMP_DIR/catalog.json" <<'PY'
import json
import sys

with open(sys.argv[1]) as file:
    data = json.load(file)

devices = data.get("devices", [])

windows = next(
    (
        item
        for item in devices
        if item.get("id")
        == "generic-windows-vm"
    ),
    None,
)

assert windows is not None
assert windows.get("enabled") is False
assert windows.get("availability") == "coming-soon"
PY
    then
        pass "Windows catalog entry is Coming Soon"
    else
        fail "Windows catalog entry is incorrect"
    fi
else
    fail "catalog API failed"
fi


section "TOPOLOGY API"

if curl -fsS \
  http://127.0.0.1/api/lab/topology \
  > "$TMP_DIR/topology.json" \
  2>/dev/null
then
    if python3 - "$TMP_DIR/topology.json" <<'PY'
import json
import sys

with open(sys.argv[1]) as file:
    data = json.load(file)

assert isinstance(data.get("nodes"), list)
assert isinstance(data.get("links"), list)

print(
    f"Observed nodes={len(data['nodes'])} "
    f"links={len(data['links'])}"
)
PY
    then
        pass "topology API payload valid"
    else
        fail "topology API payload invalid"
    fi
else
    fail "topology API failed"
fi


section "LAYOUT API"

if curl -fsS \
  http://127.0.0.1/api/lab/layout \
  > "$TMP_DIR/layout.json" \
  2>/dev/null
then
    if python3 - "$TMP_DIR/layout.json" <<'PY'
import json
import sys

with open(sys.argv[1]) as file:
    data = json.load(file)

assert isinstance(data.get("nodes"), list)

print(
    f"Layout nodes={len(data['nodes'])}"
)
PY
    then
        pass "layout API payload valid"
    else
        fail "layout API payload invalid"
    fi
else
    fail "layout API failed"
fi


section "APPLY PLAN"

if [ ! -x backend/.venv/bin/python ]; then
    fail "backend venv missing"
else
    if PYTHONPATH=backend \
      backend/.venv/bin/python - <<'PY'
from app.apply_plan_service import build_apply_plan

plan = build_apply_plan()
summary = plan.get("summary", {})

print(
    f"ready={plan.get('ready')} "
    f"nodes={summary.get('nodes')} "
    f"links={summary.get('links')} "
    f"actions={summary.get('actions')} "
    f"errors={summary.get('errors')} "
    f"warnings={summary.get('warnings')}"
)

assert plan.get("ready") is True
assert summary.get("errors") == 0
PY
    then
        pass "Apply Plan READY"
    else
        fail "Apply Plan not READY"
    fi
fi


section "MANAGED RUNTIME"

TARGETS="$(
    PYTHONPATH=backend \
    backend/.venv/bin/python - <<'PY' \
    2>/dev/null || true
from app.apply_plan_service import build_apply_plan

plan = build_apply_plan()

for action in plan.get("actions", []):
    domain = action.get("domain_name")
    network = action.get("libvirt_network")

    if domain:
        print(f"vm|{domain}")

    if network:
        print(f"network|{network}")
PY
)"

if [ -z "$TARGETS" ]; then
    skip "no managed runtime targets in Apply Plan"
else
    while IFS='|' read -r kind name; do
        [ -n "$name" ] || continue

        if [ "$kind" = "vm" ]; then
            STATE="$(
                virsh \
                  -c qemu:///system \
                  domstate \
                  "$name" \
                  2>/dev/null \
                  || echo "missing"
            )"

            if [ "$STATE" = "running" ]; then
                pass "$name running"
            else
                fail "$name state=$STATE"
            fi

        elif [ "$kind" = "network" ]; then
            if virsh \
              -c qemu:///system \
              net-info \
              "$name" \
              2>/dev/null \
              | grep -Eq \
                  '^Active:[[:space:]]+yes[[:space:]]*$'
            then
                pass "$name active"
            else
                fail "$name is not active"
            fi
        fi
    done <<< "$TARGETS"
fi


section "WEB CONSOLE"

CONSOLE_NODE="$(
    PYTHONPATH=backend \
    backend/.venv/bin/python - <<'PY' \
    2>/dev/null || true
from app.apply_plan_service import (
    build_apply_plan,
)
from app.desired_topology_service import (
    get_desired_topology,
)

plan = build_apply_plan()
desired = get_desired_topology()

linux_node_ids = {
    node.get("id")
    for node in desired.get(
        "nodes",
        [],
    )
    if node.get("template_id")
    == "generic-linux-vm"
}

for action in plan.get(
    "actions",
    [],
):
    if (
        action.get("node_id")
        in linux_node_ids
        and action.get("domain_name")
    ):
        print(
            action.get("node_id")
        )
        break
PY
)"

if [ -z "$CONSOLE_NODE" ]; then
    skip "no VM available for console smoke"
elif [ ! -x backend/.venv/bin/python ]; then
    skip "backend venv unavailable for console smoke"
else
    export CONSOLE_NODE

    if backend/.venv/bin/python - <<'PY'
import asyncio
import os
from urllib.parse import quote

import websockets


async def main():
    node_id = os.environ[
        "CONSOLE_NODE"
    ]

    url = (
        "ws://127.0.0.1/"
        "api/lab/nodes/"
        f"{quote(node_id, safe='')}/"
        "console/ws"
    )

    received = ""

    async with websockets.connect(
        url,
        open_timeout=10,
    ) as websocket:
        await websocket.send("\r")

        for _ in range(8):
            try:
                message = (
                    await asyncio.wait_for(
                        websocket.recv(),
                        timeout=1.0,
                    )
                )
            except asyncio.TimeoutError:
                continue

            received += str(message)

            if received:
                break

    if not received:
        raise SystemExit(
            "console returned no data"
        )

    lowered = received.lower()

    if (
        "[console error]"
        in lowered
        or
        "console disponivel somente"
        in lowered
    ):
        raise SystemExit(
            received[:300]
        )

    if "console/agentd" not in lowered:
        raise SystemExit(
            "console AgentD banner not received"
        )

    print(
        received[:200]
    )


asyncio.run(main())
PY
    then
        pass "web console websocket"
    else
        fail "web console websocket"
    fi
fi


section "SECURITY BOUNDARY"

BACKEND_UID="$(
    docker exec \
      unidac-lab-backend \
      id -u \
      2>/dev/null \
      || echo "unknown"
)"

if [ "$BACKEND_UID" != "0" ] \
  && [ "$BACKEND_UID" != "unknown" ]
then
    pass "backend non-root uid=$BACKEND_UID"
else
    fail "backend uid=$BACKEND_UID"
fi


if docker exec \
  unidac-lab-backend \
  test ! -e /dev/kvm \
  >/dev/null 2>&1
then
    pass "backend has no /dev/kvm"
else
    fail "backend exposes /dev/kvm"
fi


if docker exec \
  unidac-lab-backend \
  test ! -S \
  /run/libvirt/libvirt-sock \
  >/dev/null 2>&1
then
    pass "backend has no libvirt write socket"
else
    fail "backend exposes libvirt write socket"
fi


if docker exec \
  unidac-lab-backend \
  test ! -S \
  /var/run/docker.sock \
  >/dev/null 2>&1
then
    pass "backend has no Docker socket"
else
    fail "backend exposes Docker socket"
fi


if docker exec \
  unidac-lab-backend \
  test -S \
  /run/unidac-lab/agent.sock \
  >/dev/null 2>&1
then
    pass "backend sees AgentD socket"
else
    fail "backend cannot see AgentD socket"
fi


section "NETWORK IMPAIRMENT STATE"

NETEM_LINES="$(
    tc qdisc show \
      2>/dev/null \
    | grep \
      ' netem ' \
    || true
)"

if [ -n "$NETEM_LINES" ]; then
    warn "active netem qdisc detected"
    printf '%s\n' \
      "$NETEM_LINES"
else
    pass "no active netem qdisc"
fi


section "REPOSITORY"

if git diff --check \
  >/dev/null 2>&1
then
    pass "git diff --check"
else
    fail "git diff --check"
fi


if [ -z "$(git status --short)" ]; then
    pass "Git worktree clean"
else
    if [ "${UNIDAC_SMOKE_ALLOW_DIRTY:-0}" = "1" ]; then
        warn \
          "Git worktree dirty, allowed by UNIDAC_SMOKE_ALLOW_DIRTY=1"

        git status --short
    else
        fail "Git worktree dirty"

        git status --short
    fi
fi


section "SUMMARY"

echo "PASS : $PASS_COUNT"
echo "WARN : $WARN_COUNT"
echo "SKIP : $SKIP_COUNT"
echo "FAIL : $FAIL_COUNT"
echo


if [ "$FAIL_COUNT" -gt 0 ]; then
    echo "RESULT: FAIL"
    exit 1
fi


if [ "$WARN_COUNT" -gt 0 ]; then
    echo "RESULT: PASS WITH WARNINGS"
    exit 0
fi


echo "RESULT: PASS"
exit 0
