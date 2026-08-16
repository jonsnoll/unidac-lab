#!/usr/bin/env bash
set -euo pipefail

cd /home/felipe/unidac-lab

IMAGE="$PWD/images/store/cisco/cisco-iol-l2-adventerprise-15-1-20140814/base.bin"
IOLCTL="/usr/local/libexec/unidac-lab-iolctl"

INSTANCE="ulab-iol-core-smoke"
NO_LICENSE="/tmp/unidac-iol-core-smoke-no-license"

sudo rm -f "$NO_LICENSE"

sudo "$IOLCTL" \
  remove-prepared \
  --instance "$INSTANCE" \
  >/dev/null 2>&1 \
  || true

sudo "$IOLCTL" \
  --license-file "$NO_LICENSE" \
  prepare \
  --instance "$INSTANCE" \
  --image "$IMAGE" \
  --ethernet-ports 8 \
  --memory-mb 256 \
  --nvram-kb 256 \
  > /tmp/unidac-iol-core-prepare.json

sudo "$IOLCTL" \
  start-plan \
  --instance "$INSTANCE" \
  > /tmp/unidac-iol-core-plan.json

cat /tmp/unidac-iol-core-plan.json

python3 <<'PY'
import json
from pathlib import Path

data = json.loads(
    Path(
        "/tmp/unidac-iol-core-plan.json"
    ).read_text(
        encoding="utf-8"
    )
)

command = data.get(
    "command",
    []
)

if "-N" not in command:
    raise SystemExit(
        "Core command must include -N"
    )

if data.get(
    "network_bindings"
):
    raise SystemExit(
        "Core smoke must not have bindings"
    )

if data.get(
    "would_execute_ios"
) is not False:
    raise SystemExit(
        "start-plan executed IOS"
    )

print(
    "Core -N command: PASS"
)

print(
    "Core no-bindings: PASS"
)
PY

set +e

sudo "$IOLCTL" \
  start \
  --instance "$INSTANCE" \
  >/tmp/unidac-iol-core-start.txt \
  2>&1

RC=$?

set -e

cat /tmp/unidac-iol-core-start.txt

if [ "$RC" -eq 0 ]; then
    echo "ERRO: core smoke nao pode iniciar IOS."
    sudo "$IOLCTL" \
      stop \
      --instance "$INSTANCE" \
      || true
    exit 1
fi

if ! grep -Fq \
  'Startup bloqueado pelo license gate' \
  /tmp/unidac-iol-core-start.txt
then
    echo "ERRO: start foi bloqueado por motivo inesperado."
    exit 1
fi

echo "License isolation: PASS"

sudo "$IOLCTL" \
  remove-prepared \
  --instance "$INSTANCE"

rm -f \
  /tmp/unidac-iol-core-prepare.json \
  /tmp/unidac-iol-core-plan.json \
  /tmp/unidac-iol-core-start.txt

echo
echo "IOL CORE RUNTIME SMOKE = PASS"
