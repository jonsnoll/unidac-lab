#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

echo
echo "=================================================="
echo " UNIDAC-LAB PACKET PARSER SMOKE"
echo "=================================================="

docker compose exec \
  -T \
  backend \
  python - <<'PY'
from app.capture_service import (
    capture_packet_summary,
)


def mac(text):
    return bytes.fromhex(
        text.replace(":", "")
    )


def ethernet_frame(
    destination,
    source,
    field,
    payload,
):
    return (
        mac(destination)
        + mac(source)
        + int(field).to_bytes(
            2,
            "big",
        )
        + payload
    )


cases = [
    (
        "STP",
        ethernet_frame(
            "01:80:c2:00:00:00",
            "02:00:00:00:00:01",
            38,
            b"\x42\x42\x03"
            + b"\x00" * 35,
        ),
        "STP",
    ),
    (
        "LLDP",
        ethernet_frame(
            "01:80:c2:00:00:0e",
            "02:00:00:00:00:02",
            0x88CC,
            b"\x00\x00",
        ),
        "LLDP",
    ),
    (
        "LACP",
        ethernet_frame(
            "01:80:c2:00:00:02",
            "02:00:00:00:00:03",
            0x8809,
            b"\x01\x01"
            + b"\x00" * 50,
        ),
        "LACP",
    ),
    (
        "CDP",
        ethernet_frame(
            "01:00:0c:cc:cc:cc",
            "02:00:00:00:00:04",
            12,
            b"\xaa\xaa\x03"
            b"\x00\x00\x0c"
            b"\x20\x00"
            b"\x00\x00\x00\x00",
        ),
        "CDP",
    ),
    (
        "EAPOL",
        ethernet_frame(
            "01:80:c2:00:00:03",
            "02:00:00:00:00:05",
            0x888E,
            b"\x02\x00\x00\x00",
        ),
        "EAPOL",
    ),
]


for label, raw, expected in cases:
    result = capture_packet_summary(
        raw
    )

    protocol = result.get(
        "protocol"
    )

    if protocol != expected:
        raise SystemExit(
            f"FAIL: {label}: "
            f"esperado {expected}, "
            f"recebido {protocol}; "
            f"resultado={result}"
        )

    print(
        f"PASS: {label:<8} "
        f"-> {protocol:<8} "
        f"| {result.get('info')}"
    )


print()
print(
    "PACKET PARSER SMOKE = PASS"
)
PY
