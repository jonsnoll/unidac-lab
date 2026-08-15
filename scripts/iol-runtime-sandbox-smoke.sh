#!/usr/bin/env bash
set -euo pipefail

cd /home/felipe/unidac-lab

IMAGE_ID="cisco-iol-l2-adventerprise-15-1-20140814"
CISCO_IMAGE="$PWD/images/store/cisco/$IMAGE_ID/base.bin"
RUNTIME_IMAGE="unidac-lab-iol-runtime:0.4-dev"

echo
echo "=================================================="
echo " IOL RUNTIME SANDBOX SMOKE"
echo "=================================================="

test -s "$CISCO_IMAGE"

docker image inspect \
  "$RUNTIME_IMAGE" \
  >/dev/null

OUTPUT="$(
    docker run \
      --rm \
      --network none \
      --read-only \
      --cap-drop ALL \
      --security-opt no-new-privileges:true \
      -v "$CISCO_IMAGE:/images/base.bin:ro" \
      "$RUNTIME_IMAGE" \
      /images/base.bin
)"

printf '%s\n' "$OUTPUT"

printf '%s\n' "$OUTPUT" \
  | grep -Fq \
      'IOL COMPAT SANDBOX = PASS'

printf '%s\n' "$OUTPUT" \
  | grep -Fq \
      'Cisco executable was NOT started.'

echo
echo "IOL RUNTIME SANDBOX SMOKE = PASS"
