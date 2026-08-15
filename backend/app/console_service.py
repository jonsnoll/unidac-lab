import re
import subprocess

from app.apply_plan_service import (
    build_apply_plan,
)


DOMAIN_RE = re.compile(
    r"^ulab-[a-z0-9-]{1,59}$"
)

VIRSH = "/usr/bin/virsh"

LIBVIRT_URI = "qemu:///system"


class ConsoleError(RuntimeError):
    def __init__(
        self,
        message,
        *,
        kind="console-error",
    ):
        super().__init__(message)

        self.kind = kind


def resolve_console_domain(
    node_id,
):
    plan = build_apply_plan()


    for action in plan.get(
        "actions",
        [],
    ):
        if (
            action.get("node_id")
            != node_id
        ):
            continue


        if action.get(
            "action"
        ) not in {
            "create-vm",
            "reuse-vm",
        }:
            continue


        domain_name = action.get(
            "domain_name"
        )


        if not domain_name:
            continue


        if not DOMAIN_RE.fullmatch(
            domain_name
        ):
            raise ConsoleError(
                "Dominio fora do namespace "
                "gerenciado.",
                kind=
                    "invalid-domain",
            )


        if (
            action.get("action")
            == "create-vm"
        ):
            raise ConsoleError(
                "Runtime ainda nao existe. "
                "Execute Apply Changes primeiro.",
                kind=
                    "runtime-not-created",
            )


        return {
            "node_id":
                node_id,

            "node_name":
                action.get(
                    "node_name"
                ),

            "domain_name":
                domain_name,
        }


    raise ConsoleError(
        "VM gerenciada nao encontrada.",
        kind="vm-not-found",
    )


def get_domain_state(
    domain_name,
):
    process = subprocess.run(
        [
            VIRSH,
            "-c",
            LIBVIRT_URI,
            "domstate",
            domain_name,
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


    if process.returncode != 0:
        raise ConsoleError(
            process.stderr.strip()
            or
            "Falha consultando VM.",
            kind="libvirt-error",
        )


    return process.stdout.strip()


def ensure_console_ready(
    node_id,
):
    runtime = resolve_console_domain(
        node_id
    )

    state = get_domain_state(
        runtime[
            "domain_name"
        ]
    )


    if state != "running":
        raise ConsoleError(
            "Console disponivel somente "
            "quando a VM esta running.",
            kind="vm-not-running",
        )


    runtime["state"] = state

    return runtime
