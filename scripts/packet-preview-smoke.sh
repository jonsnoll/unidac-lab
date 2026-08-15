#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(
    cd "$(dirname "${BASH_SOURCE[0]}")/.."
    pwd
)"

cd "$REPO_ROOT"

echo
echo "=================================================="
echo " UNIDAC-LAB PACKET PREVIEW SMOKE"
echo "=================================================="

python3 <<'PY'
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8000"

def api(method, path):
    request = urllib.request.Request(
        BASE + path,
        method=method,
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=30,
        ) as response:
            body = response.read()

            return (
                response.status,
                json.loads(body) if body else {},
            )

    except urllib.error.HTTPError as error:
        body = error.read()

        try:
            data = json.loads(body)
        except Exception:
            data = {
                "raw": body.decode(errors="replace")
            }

        return error.code, data

def desired_links():
    links = []

    for path in sorted(
        Path("labs").glob("*/desired_topology.json")
    ):
        try:
            data = json.loads(path.read_text())
        except Exception:
            continue

        for link in data.get("links", []):
            link_id = (
                link.get("id")
                or link.get("link_id")
                or link.get("linkId")
            )

            if link_id and link_id not in links:
                links.append(link_id)

    return links

print()
print("===== OPENAPI =====")

status, openapi = api(
    "GET",
    "/openapi.json",
)

if status != 200:
    raise SystemExit(
        "FAIL: OpenAPI indisponivel."
    )

preview_path = (
    "/api/lab/captures/"
    "{capture_id}/preview"
)

if preview_path not in openapi.get(
    "paths",
    {},
):
    raise SystemExit(
        "FAIL: endpoint preview ausente."
    )

print(
    "PASS: endpoint preview registrado"
)

print()
print("===== CRIANDO CAPTURA =====")

capture_id = None

for link_id in desired_links():
    encoded_link = urllib.parse.quote(
        link_id,
        safe="",
    )

    status, data = api(
        "POST",
        (
            "/api/lab/links/"
            f"{encoded_link}"
            "/capture/start"
        ),
    )

    if status != 200:
        continue

    capture_id = data.get(
        "capture_id"
    )

    if not capture_id:
        continue

    print(
        "Capture:",
        capture_id,
    )

    print(
        "Interface:",
        data.get(
            "result",
            {},
        ).get(
            "interface",
            "-",
        ),
    )

    print(
        "Aguardando captura..."
    )

    time.sleep(4)

    encoded_capture = urllib.parse.quote(
        capture_id,
        safe="",
    )

    stop_status, stop_data = api(
        "POST",
        (
            "/api/lab/captures/"
            f"{encoded_capture}"
            "/stop"
        ),
    )

    if stop_status != 200:
        raise SystemExit(
            "FAIL: captura iniciou "
            "mas nao foi possivel parar."
        )

    print(
        "Tamanho:",
        stop_data.get(
            "result",
            {},
        ).get(
            "size_bytes",
            0,
        ),
        "bytes",
    )

    break

if not capture_id:
    raise SystemExit(
        "FAIL: nenhum link capturavel "
        "foi encontrado."
    )

encoded_capture = urllib.parse.quote(
    capture_id,
    safe="",
)

print()
print("===== PREVIEW =====")

status, preview = api(
    "GET",
    (
        "/api/lab/captures/"
        f"{encoded_capture}"
        "/preview?limit=20"
    ),
)

if status != 200:
    print(
        json.dumps(
            preview,
            indent=2,
        )
    )

    raise SystemExit(
        f"FAIL: preview HTTP {status}."
    )

required = {
    "status",
    "capture_id",
    "size_bytes",
    "limit",
    "returned",
    "truncated",
    "packets",
}

missing = required - set(preview)

if missing:
    raise SystemExit(
        "FAIL: campos ausentes: "
        + ", ".join(sorted(missing))
    )

if preview["capture_id"] != capture_id:
    raise SystemExit(
        "FAIL: capture_id divergente."
    )

if preview["limit"] != 20:
    raise SystemExit(
        "FAIL: limit divergente."
    )

packets = preview["packets"]

if not isinstance(
    packets,
    list,
):
    raise SystemExit(
        "FAIL: packets nao e lista."
    )

if preview["returned"] != len(packets):
    raise SystemExit(
        "FAIL: returned divergente."
    )

if len(packets) > 20:
    raise SystemExit(
        "FAIL: limite excedido."
    )

fields = {
    "number",
    "time",
    "source",
    "destination",
    "protocol",
    "length",
    "info",
}

for packet in packets:
    missing = fields - set(packet)

    if missing:
        raise SystemExit(
            "FAIL: pacote incompleto: "
            + ", ".join(sorted(missing))
        )

print(
    "PASS: preview HTTP 200"
)

print(
    "PASS: schema valido"
)

print(
    "PASS: packets=",
    len(packets),
    sep="",
)

if packets:
    print()
    print(
        "Primeiro pacote:"
    )

    print(
        json.dumps(
            packets[0],
            indent=2,
        )
    )

print()
print("===== VALIDAR LIMITES =====")

for value in (
    0,
    501,
):
    status, _ = api(
        "GET",
        (
            "/api/lab/captures/"
            f"{encoded_capture}"
            "/preview"
            f"?limit={value}"
        ),
    )

    if status != 422:
        raise SystemExit(
            f"FAIL: limit={value} "
            f"retornou {status}; "
            "esperado 422."
        )

print(
    "PASS: limit 1..500"
)

print()
print("===== DOWNLOAD PCAP =====")

url = (
    BASE
    + "/api/lab/captures/"
    + encoded_capture
    + "/download"
)

with urllib.request.urlopen(
    url,
    timeout=30,
) as response:
    magic = response.read(4)

valid_magic = {
    bytes.fromhex("d4c3b2a1"),
    bytes.fromhex("a1b2c3d4"),
    bytes.fromhex("4d3cb2a1"),
    bytes.fromhex("a1b23c4d"),
}

if magic not in valid_magic:
    raise SystemExit(
        "FAIL: download nao parece PCAP."
    )

print(
    "PASS: Download PCAP"
)

print()
print(
    "=================================================="
)

print(
    "PACKET PREVIEW SMOKE = PASS"
)

print(
    "=================================================="
)
PY
