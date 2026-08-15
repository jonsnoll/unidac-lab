#!/usr/bin/env bash
set -euo pipefail

cd /home/felipe/unidac-lab

IMAGE_ID="cisco-iol-l2-adventerprise-15-1-20140814"
IMAGE="$PWD/images/store/cisco/$IMAGE_ID/base.bin"

IOLCTL="/usr/local/libexec/unidac-lab-iolctl"
INSTANCE="ulab-iol-provider-smoke"

echo
echo "=================================================="
echo " IOL PROVIDER SMOKE"
echo "=================================================="

sudo "$IOLCTL" \
  doctor \
  --image "$IMAGE" \
  > /tmp/iol-provider-doctor.json

cat /tmp/iol-provider-doctor.json

python3 <<'PY'
import json
from pathlib import Path

data = json.loads(
    Path(
        "/tmp/iol-provider-doctor.json"
    ).read_text(
        encoding="utf-8"
    )
)

if data.get("provider") != "iol":
    raise SystemExit(
        "Provider mismatch"
    )

sandbox = data.get(
    "sandbox_compatibility",
    data.get(
        "compatibility",
        {},
    ),
)

if (
    sandbox.get(
        "status"
    )
    != "pass"
):
    raise SystemExit(
        "Sandbox compatibility did not pass"
    )

private = data.get(
    "private_compatibility"
)

if (
    private is not None
    and private.get(
        "status"
    )
    != "pass"
):
    raise SystemExit(
        "Private compatibility did not pass"
    )

if data.get("startup_allowed") is not False:
    raise SystemExit(
        "Startup must remain blocked"
    )

print("Provider doctor: PASS")
PY

rm -f /tmp/iol-provider-doctor.json

sudo "$IOLCTL" \
  remove-prepared \
  --instance "$INSTANCE" \
  >/dev/null 2>&1 \
  || true

sudo "$IOLCTL" \
  prepare \
  --instance "$INSTANCE" \
  --image "$IMAGE" \
  > /tmp/iol-provider-prepare.json

cat /tmp/iol-provider-prepare.json

sudo "$IOLCTL" \
  inspect \
  --instance "$INSTANCE" \
  > /tmp/iol-provider-inspect.json

python3 <<'PY'
import json
from pathlib import Path

data = json.loads(
    Path(
        "/tmp/iol-provider-inspect.json"
    ).read_text(
        encoding="utf-8"
    )
)

if data.get("provider") != "iol":
    raise SystemExit(
        "Provider mismatch"
    )

if data.get("state") != "prepared":
    raise SystemExit(
        "Unexpected state"
    )

if (
    data.get(
        "license_gate",
        {},
    ).get(
        "required_for_start"
    )
    is not True
):
    raise SystemExit(
        "License gate missing"
    )

print("Prepare state: PASS")
PY

sudo "$IOLCTL" list

sudo "$IOLCTL" \
  remove-prepared \
  --instance "$INSTANCE" \
  > /tmp/iol-provider-remove.json

cat /tmp/iol-provider-remove.json

if sudo test -e \
  "/var/lib/unidac-lab/iol/instances/$INSTANCE.json"
then
    echo "ERRO: smoke manifest nao foi removido."
    exit 1
fi

rm -f \
  /tmp/iol-provider-prepare.json \
  /tmp/iol-provider-inspect.json \
  /tmp/iol-provider-remove.json

echo
echo "IOL PROVIDER SMOKE = PASS"
