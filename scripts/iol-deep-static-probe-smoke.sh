#!/usr/bin/env bash
set -euo pipefail

cd /home/felipe/unidac-lab

IMAGE_ID="cisco-iol-l2-adventerprise-15-1-20140814"
IMAGE="$PWD/images/store/cisco/$IMAGE_ID/base.bin"
SHA="5c1ce9b1766fe8441986ba5e3cedd72278e3f10d62503c67db03112a76b2cff2"

OUT="/tmp/unidac-iol-deep-probe.json"

python3 \
  runtime/iol/deep_static_probe.py \
  --image "$IMAGE" \
  --expected-sha256 "$SHA" \
  > "$OUT"

python3 <<'PY'
import json
from pathlib import Path

data = json.loads(
    Path(
        "/tmp/unidac-iol-deep-probe.json"
    ).read_text(
        encoding="utf-8"
    )
)

if (
    data.get(
        "probe_type"
    )
    != "deep-static-only"
):
    raise SystemExit(
        "Probe type mismatch"
    )

if data.get(
    "ios_executed"
) is not False:
    raise SystemExit(
        "IOS must not execute"
    )

cluster = data.get(
    "usage_cluster",
    []
)

if not any(
    "Usage: <image> [options] <application id>"
    in item.get(
        "text",
        "",
    )
    for item in cluster
):
    raise SystemExit(
        "Usage anchor absent"
    )

anchors = data.get(
    "anchor_contexts",
    []
)

required = (
    "NETMAP",
    "iourc",
)

for target in required:
    if not any(
        target.lower()
        in item.get(
            "anchor",
            ""
        ).lower()
        for item in anchors
    ):
        raise SystemExit(
            f"Missing anchor: {target}"
        )

print(
    "Usage cluster entries:",
    len(cluster),
)

print(
    "Global option candidates:",
    len(
        data.get(
            "global_option_candidates",
            []
        )
    ),
)

print(
    "Anchor contexts:",
    len(
        anchors
    ),
)

print(
    "IOL DEEP STATIC PROBE SMOKE = PASS"
)
PY

rm -f "$OUT"
