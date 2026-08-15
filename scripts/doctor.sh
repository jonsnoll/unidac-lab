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

CURRENT_USER="$(
    id -un
)"


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


section() {
    echo
    echo "=================================================="
    echo " $1"
    echo "=================================================="
}


check_command() {
    local command="$1"

    if command -v \
      "$command" \
      >/dev/null 2>&1
    then
        pass "command available: $command"
    else
        fail "command missing: $command"
    fi
}


check_container() {
    local container="$1"
    local status
    local health

    if ! docker inspect \
      "$container" \
      >/dev/null 2>&1
    then
        fail "container missing: $container"
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

    if [ "$status" = "running" ] \
      && {
        [ "$health" = "healthy" ] \
        || [ "$health" = "none" ]
      }
    then
        pass \
          "$container: $status/$health"
    else
        fail \
          "$container: $status/$health"
    fi
}


section "UNIDAC-LAB DOCTOR"

echo "Repository : $ROOT_DIR"
echo "User       : $CURRENT_USER"
echo "Kernel     : $(uname -r)"


section "REQUIRED COMMANDS"

for command_name in \
  git \
  docker \
  curl \
  python3 \
  virsh \
  ip \
  tc \
  tcpdump \
  systemctl
do
    check_command \
      "$command_name"
done


section "KVM / LIBVIRT"

if [ -e /dev/kvm ]; then
    pass "/dev/kvm exists"
else
    fail "/dev/kvm missing"
fi


if virsh \
  -c qemu:///system \
  list --all \
  >/dev/null 2>&1
then
    pass "libvirt qemu:///system accessible"
else
    fail "libvirt qemu:///system inaccessible"
fi


if systemctl is-active \
  --quiet libvirtd
then
    pass "libvirtd active"
else
    fail "libvirtd inactive"
fi


section "AGENTD"

if systemctl is-active \
  --quiet unidac-lab-agentd
then
    pass "unidac-lab-agentd active"
else
    fail "unidac-lab-agentd inactive"
fi


GROUP_ENTRY="$(
    getent group \
      unidac-lab \
      2>/dev/null \
      || true
)"

if [ -n "$GROUP_ENTRY" ]; then
    pass "group unidac-lab exists"
else
    fail "group unidac-lab missing"
fi


if id -nG \
  | tr ' ' '\n' \
  | grep -qx \
      'unidac-lab'
then
    pass \
      "current shell has unidac-lab group"
else
    MEMBERS="$(
        printf '%s' \
          "$GROUP_ENTRY" \
        | cut -d: -f4
    )"

    case ",$MEMBERS," in
        *",$CURRENT_USER,"*)
            warn \
              "user is registered in unidac-lab but current shell has not refreshed group membership"
            ;;
        *)
            fail \
              "user is not a member of unidac-lab"
            ;;
    esac
fi


section "DOCKER"

if docker info \
  >/dev/null 2>&1
then
    pass "Docker Engine accessible"
else
    fail "Docker Engine inaccessible"
fi


if docker compose version \
  >/dev/null 2>&1
then
    pass "Docker Compose available"
else
    fail "Docker Compose unavailable"
fi


if docker compose config \
  >/dev/null 2>&1
then
    pass "compose.yaml valid"
else
    fail "compose.yaml invalid"
fi


check_container \
  unidac-lab-backend

check_container \
  unidac-lab-frontend


section "HTTP / AGENT"

if curl -fsS \
  -o /dev/null \
  http://127.0.0.1/
then
    pass "frontend HTTP reachable"
else
    fail "frontend HTTP unreachable"
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
    pass "backend -> AgentD healthy"
else
    fail "backend -> AgentD failed"
fi


section "BACKEND SECURITY BOUNDARY"

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
    pass \
      "backend non-root uid=$BACKEND_UID"
else
    fail \
      "backend user invalid uid=$BACKEND_UID"
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


section "LAB RUNTIME DATA"

if [ -d labs ]; then
    pass "labs directory exists"
else
    fail "labs directory missing"
fi


if [ -w labs ]; then
    pass "labs directory writable"
else
    fail "labs directory not writable"
fi


for runtime_file in \
  labs/vxlan-fgt-01/desired_topology.json \
  labs/vxlan-fgt-01/layout.json
do
    if [ -f "$runtime_file" ]; then
        pass "runtime file exists: $runtime_file"

        if python3 -m json.tool \
          "$runtime_file" \
          >/dev/null 2>&1
        then
            pass "valid JSON: $runtime_file"
        else
            fail "invalid JSON: $runtime_file"
        fi

        if git check-ignore \
          -q \
          "$runtime_file"
        then
            pass "runtime file ignored by Git: $runtime_file"
        else
            fail "runtime file is not ignored: $runtime_file"
        fi
    else
        warn \
          "runtime file absent; backend will bootstrap it on first save: $runtime_file"
    fi
done


if git ls-files \
  --error-unmatch \
  labs/.gitkeep \
  >/dev/null 2>&1
then
    pass "labs/.gitkeep tracked"
else
    fail "labs/.gitkeep not tracked"
fi


section "CATALOG"

if python3 - <<'PY' \
  >/dev/null 2>&1
import json

with open(
    "catalog/devices/generic/windows-vm.json"
) as file:
    data = json.load(file)

assert data.get("enabled") is False
assert data.get("availability") == "coming-soon"
PY
then
    pass "Windows template is Coming Soon / disabled"
else
    fail "Windows template availability is incorrect"
fi


section "APPLY PLAN"

if [ ! -x backend/.venv/bin/python ]; then
    fail "backend Python venv missing"
else
    APPLY_RESULT="$(
        PYTHONPATH=backend \
        backend/.venv/bin/python - <<'PY' \
        2>&1
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

if not plan.get("ready"):
    raise SystemExit(1)

if summary.get("errors", 0) != 0:
    raise SystemExit(1)
PY
    )"

    if [ "$?" -eq 0 ]; then
        pass "Apply Plan: $APPLY_RESULT"
    else
        fail "Apply Plan: $APPLY_RESULT"
    fi
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
    warn "active netem qdisc detected:"
    printf '%s\n' "$NETEM_LINES"
else
    pass "no active netem qdisc detected"
fi


section "REPOSITORY"

if git diff --check \
  >/dev/null 2>&1
then
    pass "git diff --check"
else
    fail "git diff --check failed"
fi


if [ -z "$(git status --short)" ]; then
    pass "Git worktree clean"
else
    warn "Git worktree has changes"
    git status --short
fi


section "SUMMARY"

echo "PASS : $PASS_COUNT"
echo "WARN : $WARN_COUNT"
echo "FAIL : $FAIL_COUNT"
echo

if [ "$FAIL_COUNT" -gt 0 ]; then
    echo "RESULT: UNHEALTHY"
    exit 1
fi

if [ "$WARN_COUNT" -gt 0 ]; then
    echo "RESULT: HEALTHY WITH WARNINGS"
    exit 0
fi

echo "RESULT: HEALTHY"
exit 0
