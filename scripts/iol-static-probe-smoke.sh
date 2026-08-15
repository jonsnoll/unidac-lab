#!/usr/bin/env bash
set -euo pipefail

cd /home/felipe/unidac-lab

IMAGE_ID="cisco-iol-l2-adventerprise-15-1-20140814"
IMAGE="$PWD/images/store/cisco/$IMAGE_ID/base.bin"
EXPECTED_SHA256="5c1ce9b1766fe8441986ba5e3cedd72278e3f10d62503c67db03112a76b2cff2"

OUT="/tmp/unidac-iol-static-probe.json"

echo
echo "=================================================="
echo " IOL STATIC PROBE SMOKE"
echo "=================================================="

python3 \
  runtime/iol/static_probe.py \
  --image "$IMAGE" \
  --expected-sha256 "$EXPECTED_SHA256" \
  > "$OUT"

python3 <<'PY'
import json
from pathlib import Path

data = json.loads(
    Path(
        "/tmp/unidac-iol-static-probe.json"
    ).read_text(
        encoding="utf-8"
    )
)

if data.get(
    "probe_type"
) != "static-only":
    raise SystemExit(
        "Probe type mismatch"
    )

if data.get(
    "ios_executed"
) is not False:
    raise SystemExit(
        "IOS must not be executed"
    )

image = data.get(
    "image",
    {}
)

if (
    image.get(
        "sha256"
    )
    !=
    "5c1ce9b1766fe8441986ba5e3cedd72278e3f10d62503c67db03112a76b2cff2"
):
    raise SystemExit(
        "SHA mismatch"
    )

keywords = data.get(
    "keyword_matches",
    {}
)

print(
    "Keyword groups:",
    ", ".join(
        sorted(
            keywords.keys()
        )
    ),
)

print(
    "Option candidates:",
    len(
        data.get(
            "option_candidates",
            []
        )
    ),
)

print(
    "Environment candidates:",
    len(
        data.get(
            "environment_candidates",
            []
        )
    ),
)

print(
    "IOL STATIC PROBE SMOKE = PASS"
)
PY

rm -f "$OUT"
