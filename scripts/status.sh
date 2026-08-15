#!/usr/bin/env bash

set -u

ROOT_DIR="$(
    CDPATH= cd -- \
      "$(dirname -- "$0")/.." \
      && pwd
)"

cd "$ROOT_DIR" || exit 1

FAILURES=0


line() {
    printf '%-24s %s\n' \
      "$1" \
      "$2"
}


check_service() {
    local label="$1"
    local service="$2"
    local state

    state="$(
        systemctl is-active \
          "$service" \
          2>/dev/null \
          || true
    )"

    line \
      "$label" \
      "${state:-unknown}"

    if [ "$state" != "active" ]; then
        FAILURES=$((FAILURES + 1))
    fi
}


check_container() {
    local label="$1"
    local container="$2"
    local status
    local health

    if ! docker inspect \
      "$container" \
      >/dev/null 2>&1
    then
        line \
          "$label" \
          "missing"

        FAILURES=$((FAILURES + 1))
        return
    fi

    status="$(
        docker inspect \
          --format \
          '{{.State.Status}}' \
          "$container"
    )"

    health="$(
        docker inspect \
          --format \
          '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' \
          "$container"
    )"

    if [ "$health" = "none" ]; then
        line \
          "$label" \
          "$status"

        if [ "$status" != "running" ]; then
            FAILURES=$((FAILURES + 1))
        fi

        return
    fi

    line \
      "$label" \
      "$status/$health"

    if [ "$status" != "running" ] \
      || [ "$health" != "healthy" ]
    then
        FAILURES=$((FAILURES + 1))
    fi
}


echo
echo "unidac-lab Status"
echo "================="
echo


echo "[Host]"

check_service \
  "libvirtd" \
  "libvirtd"

check_service \
  "agentd" \
  "unidac-lab-agentd"

echo


echo "[Docker]"

check_container \
  "backend" \
  "unidac-lab-backend"

check_container \
  "frontend" \
  "unidac-lab-frontend"

echo


echo "[HTTP]"

if curl -fsS \
  -o /dev/null \
  http://127.0.0.1/
then
    line \
      "frontend" \
      "OK"
else
    line \
      "frontend" \
      "FAIL"

    FAILURES=$((FAILURES + 1))
fi


AGENT_JSON="$(
    curl -fsS \
      http://127.0.0.1/api/lab/agent/health \
      2>/dev/null \
      || true
)"

if [ -n "$AGENT_JSON" ] \
  && printf '%s' \
    "$AGENT_JSON" \
    | python3 -c '
import json
import sys

data = json.load(sys.stdin)

assert data.get("status") == "ok"
assert data.get("component") == "unidac-lab-agent"
assert data.get("uid") == 0
' \
      >/dev/null 2>&1
then
    line \
      "backend -> agentd" \
      "OK"
else
    line \
      "backend -> agentd" \
      "FAIL"

    FAILURES=$((FAILURES + 1))
fi

echo


echo "[Lab]"

if LAB_INFO="$(
python3 - <<'PY'
import json
from pathlib import Path

path = Path(
    "labs/vxlan-fgt-01/"
    "desired_topology.json"
)

if not path.exists():
    print(
        "0 nodes / 0 links"
    )
else:
    data = json.loads(
        path.read_text()
    )

    print(
        f"{len(data.get('nodes', []))} nodes / "
        f"{len(data.get('links', []))} links"
    )
PY
)"
then
    line \
      "desired state" \
      "$LAB_INFO"
else
    line \
      "desired state" \
      "ERROR"

    FAILURES=$((FAILURES + 1))
fi


if [ -x backend/.venv/bin/python ]; then
    APPLY_INFO="$(
        PYTHONPATH=backend \
        backend/.venv/bin/python - <<'PY' \
        2>/dev/null || true
from app.apply_plan_service import (
    build_apply_plan,
)

plan = build_apply_plan()
summary = plan.get(
    "summary",
    {},
)

state = (
    "READY"
    if (
        plan.get("ready")
        and summary.get(
            "errors",
            0,
        ) == 0
    )
    else
    "NOT READY"
)

print(
    f"{state} | "
    f"actions={summary.get('actions', 0)} "
    f"errors={summary.get('errors', 0)} "
    f"warnings={summary.get('warnings', 0)}"
)
PY
    )"

    line \
      "apply plan" \
      "${APPLY_INFO:-ERROR}"

    case "$APPLY_INFO" in
        READY*)
            ;;
        *)
            FAILURES=$((FAILURES + 1))
            ;;
    esac
else
    line \
      "apply plan" \
      "venv missing"

    FAILURES=$((FAILURES + 1))
fi

echo


echo "[Managed Runtime]"

DOMAINS="$(
    virsh \
      -c qemu:///system \
      list --all \
      --name \
      2>/dev/null \
    | grep '^ulab-' \
    || true
)"

if [ -z "$DOMAINS" ]; then
    echo "  no managed domains"
else
    while IFS= read -r domain; do
        [ -n "$domain" ] \
          || continue

        state="$(
            virsh \
              -c qemu:///system \
              domstate \
              "$domain" \
              2>/dev/null \
              || echo "unknown"
        )"

        line \
          "$domain" \
          "$state"
    done <<< "$DOMAINS"
fi

echo


echo "[Repository]"

BRANCH="$(
    git branch \
      --show-current \
      2>/dev/null \
      || echo "-"
)"

HEAD="$(
    git rev-parse \
      --short HEAD \
      2>/dev/null \
      || echo "-"
)"

line \
  "git" \
  "$BRANCH @ $HEAD"

if [ -z "$(git status --short)" ]; then
    line \
      "worktree" \
      "clean"
else
    line \
      "worktree" \
      "DIRTY"
fi

echo


if [ "$FAILURES" -eq 0 ]; then
    echo "RESULT: HEALTHY"
    exit 0
fi

echo \
  "RESULT: DEGRADED ($FAILURES failure(s))"

exit 1
