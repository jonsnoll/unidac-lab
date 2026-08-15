
import re

from app.apply_plan_service import (
    build_apply_plan,
)


DOMAIN_RE = re.compile(
    r"^ulab-[a-z0-9-]{1,59}$"
)


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
        if action.get(
            "node_id"
        ) != node_id:
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

        adopted = (
            action.get(
                "runtime_ownership"
            )
            == "adopted"
        )

        if (
            not adopted
            and
            not DOMAIN_RE.fullmatch(
                domain_name
            )
        ):
            raise ConsoleError(
                "Dominio fora do namespace "
                "gerenciado.",
                kind="invalid-domain",
            )

        if (
            action.get(
                "action"
            )
            == "create-vm"
        ):
            raise ConsoleError(
                "Runtime ainda nao existe. "
                "Execute Apply Changes "
                "primeiro.",
                kind="runtime-not-created",
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

            "runtime_ownership":
                (
                    "adopted"
                    if adopted
                    else "managed"
                ),
        }

    raise ConsoleError(
        "VM gerenciada nao encontrada.",
        kind="vm-not-found",
    )


def ensure_console_ready(
    node_id,
):
    return resolve_console_domain(
        node_id
    )
