#!/usr/bin/env bash
set -euo pipefail

cd /home/felipe/unidac-lab

IMAGE_ID="cisco-iol-l2-adventerprise-15-1-20140814"
IMAGE="$PWD/images/store/cisco/$IMAGE_ID/base.bin"
IOLCTL="/usr/local/libexec/unidac-lab-iolctl"
INSTANCE="ulab-iol-plumbing-smoke"

echo
echo "=================================================="
echo " IOL RUNTIME PLUMBING SMOKE"
echo "=================================================="

sudo "$IOLCTL" \
  remove-prepared \
  --instance "$INSTANCE" \
  >/dev/null 2>&1 \
  || true

sudo "$IOLCTL" \
  doctor \
  --image "$IMAGE" \
  > /tmp/iol-plumbing-doctor.json

python3 <<'PY'
import json
from pathlib import Path

data = json.loads(
    Path(
        "/tmp/iol-plumbing-doctor.json"
    ).read_text(
        encoding="utf-8"
    )
)

if data.get("provider") != "iol":
    raise SystemExit(
        "Provider mismatch"
    )

if (
    data.get(
        "private_compatibility",
        {},
    ).get(
        "status"
    )
    != "pass"
):
    raise SystemExit(
        "Private compatibility failed"
    )

if (
    data.get(
        "ubridge",
        {},
    ).get(
        "installed"
    )
    is not True
):
    raise SystemExit(
        "uBridge missing"
    )

print("Doctor plumbing: PASS")
PY

sudo "$IOLCTL" \
  ubridge-self-test

sudo "$IOLCTL" \
  prepare \
  --instance "$INSTANCE" \
  --image "$IMAGE" \
  --ethernet-ports 8 \
  --memory-mb 256 \
  --nvram-kb 256 \
  --bridge port1=virbr100 \
  --bridge port2=virbr101 \
  > /tmp/iol-plumbing-prepare.json

sudo "$IOLCTL" \
  start-plan \
  --instance "$INSTANCE" \
  > /tmp/iol-plumbing-plan.json

cat /tmp/iol-plumbing-plan.json

python3 <<'PY'
import json
from pathlib import Path

plan = json.loads(
    Path(
        "/tmp/iol-plumbing-plan.json"
    ).read_text(
        encoding="utf-8"
    )
)

command = plan.get(
    "command",
    []
)

expected = [
    "iou.bin",
    "-e",
    "2",
    "-s",
    "0",
    "-n",
    "256",
    "-m",
    "256",
]

if command[:9] != expected:
    raise SystemExit(
        "Unexpected IOL command: "
        + repr(
            command
        )
    )

bindings = {
    item["port"]: item
    for item
    in plan.get(
        "network_bindings",
        []
    )
}

if (
    bindings["port1"]["bay"],
    bindings["port1"]["unit"],
) != (
    0,
    0,
):
    raise SystemExit(
        "port1 mapping failed"
    )

if (
    bindings["port2"]["bay"],
    bindings["port2"]["unit"],
) != (
    0,
    1,
):
    raise SystemExit(
        "port2 mapping failed"
    )

if plan.get(
    "would_execute_ios"
) is not False:
    raise SystemExit(
        "Dry plan executed IOS"
    )

print("IOL command contract: PASS")
print("port1 -> bay0/unit0  : PASS")
print("port2 -> bay0/unit1  : PASS")
print("IOS executed         : FALSE")
PY

NETMAP="$(
    sudo python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(
    Path(
        "/var/lib/unidac-lab/iol/instances/ulab-iol-plumbing-smoke.json"
    ).read_text(
        encoding="utf-8"
    )
)

print(
    data["runtime"]["netmap"]
)
PY
)"

echo
echo "===== NETMAP HEAD ====="
sudo head -8 "$NETMAP"

LINES="$(
    sudo wc -l \
      < "$NETMAP"
)"

if [ "$LINES" -ne 64 ]; then
    echo "ERRO: NETMAP deveria ter 64 linhas."
    exit 1
fi

echo "NETMAP 64 entries: PASS"

set +e

sudo "$IOLCTL" \
  start \
  --instance "$INSTANCE" \
  >/tmp/iol-start-blocked.txt \
  2>&1

START_RC=$?

set -e

cat /tmp/iol-start-blocked.txt

if [ "$START_RC" -eq 0 ]; then
    echo "ERRO: smoke nao pode iniciar IOS."
    sudo "$IOLCTL" \
      stop \
      --instance "$INSTANCE" \
      || true
    exit 1
fi

if ! grep -Fq \
  'Startup bloqueado pelo license gate' \
  /tmp/iol-start-blocked.txt
then
    echo "ERRO: start falhou por motivo inesperado."
    exit 1
fi

echo "License gate start block: PASS"

sudo "$IOLCTL" \
  remove-prepared \
  --instance "$INSTANCE"

rm -f \
  /tmp/iol-plumbing-doctor.json \
  /tmp/iol-plumbing-prepare.json \
  /tmp/iol-plumbing-plan.json \
  /tmp/iol-start-blocked.txt

echo
echo "IOL RUNTIME PLUMBING SMOKE = PASS"
