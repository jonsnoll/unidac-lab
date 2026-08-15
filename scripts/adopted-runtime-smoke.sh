#!/usr/bin/env bash
set -euo pipefail

cd /home/felipe/unidac-lab

echo
echo "=================================================="
echo " ADOPTED RUNTIME SMOKE"
echo "=================================================="

python3 <<'PY'
import json
import urllib.request


def get(path):
    with urllib.request.urlopen(
        "http://127.0.0.1:8000" + path,
        timeout=15,
    ) as response:
        return json.load(response)


desired = get(
    "/api/lab/desired"
)

plan = get(
    "/api/lab/apply-plan"
)

topology = get(
    "/api/lab/topology"
)

expected_desired_names = {
    "Legacy Internet / NAT",
    "FGT-DC-A",
    "FGT-DC-B",
    "UNDERLAY",
    "LAN-DC-A",
    "LAN-DC-B",
}

desired_names = {
    node.get("name")
    for node in desired.get(
        "nodes",
        [],
    )
}

missing = (
    expected_desired_names
    - desired_names
)

if missing:
    raise SystemExit(
        "Missing desired nodes: "
        + ", ".join(
            sorted(
                missing
            )
        )
    )

if not plan.get(
    "ready"
):
    raise SystemExit(
        "Apply plan is not ready: "
        + json.dumps(
            plan.get(
                "errors",
                [],
            )
        )
    )

adopted_vm_actions = {
    action.get(
        "domain_name"
    ): action
    for action in plan.get(
        "actions",
        [],
    )
    if (
        action.get(
            "runtime_ownership"
        )
        == "adopted"
        and
        action.get(
            "action"
        )
        == "reuse-vm"
    )
}

for domain in (
    "FGT-DC-A",
    "FGT-DC-B",
):
    action = adopted_vm_actions.get(
        domain
    )

    if not action:
        raise SystemExit(
            f"Adopted action missing: {domain}"
        )

expected_networks = {
    "UNDERLAY",
    "LAN-DC-A",
    "LAN-DC-B",
}

adopted_networks = {
    action.get(
        "libvirt_network"
    )
    for action in plan.get(
        "actions",
        [],
    )
    if action.get(
        "reason"
    ) == "adopted-network"
}

if (
    not expected_networks
    .issubset(
        adopted_networks
    )
):
    raise SystemExit(
        "Adopted networks missing."
    )

observed = {
    node.get("id")
    for node in topology.get(
        "nodes",
        [],
    )
}

for item in (
    "vm:FGT-DC-A",
    "vm:FGT-DC-B",
    "net:UNDERLAY",
    "net:LAN-DC-A",
    "net:LAN-DC-B",
):
    if item not in observed:
        raise SystemExit(
            f"Observed runtime missing: {item}"
        )

print(
    "Desired legacy nodes:",
    len(
        expected_desired_names
    ),
)

print(
    "Plan:",
    json.dumps(
        plan.get(
            "summary",
            {}
        ),
    ),
)

print(
    "Adopted VMs:",
    ", ".join(
        sorted(
            adopted_vm_actions
        )
    ),
)

print(
    "Adopted networks:",
    ", ".join(
        sorted(
            adopted_networks
        )
    ),
)

print(
    "ADOPTED RUNTIME SMOKE = PASS"
)
PY

python3 <<'PY'
import json
from pathlib import Path

registry = Path(
    "/etc/unidac-lab/adopted-domains.json"
)

data = json.loads(
    registry.read_text(
        encoding="utf-8"
    )
)

expected = {
    "FGT-DC-A":
        "c21e00fd-97eb-4b7c-b355-c2ef05e171f7",

    "FGT-DC-B":
        "55fd5775-bc46-4693-ab87-112eadfe01f0",
}

domains = data.get(
    "domains",
    {}
)

for name, uuid in expected.items():
    actual = (
        domains
        .get(
            name,
            {},
        )
        .get(
            "uuid"
        )
    )

    if actual != uuid:
        raise SystemExit(
            f"Registry mismatch for {name}"
        )

print(
    "ROOT REGISTRY = PASS"
)
PY
