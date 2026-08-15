
from app.agent_client import (
    AgentError,
    vm_restart,
    vm_shutdown,
    vm_start,
)
from app.apply_plan_service import (
    build_apply_plan,
)


class LifecycleError(RuntimeError):
    def __init__(
        self,
        message,
        *,
        kind="lifecycle-error",
        node_id=None,
        operation=None,
        cause=None,
    ):
        super().__init__(message)

        self.kind = kind
        self.node_id = node_id
        self.operation = operation
        self.cause = cause


OPERATIONS = {
    "start":
        vm_start,

    "shutdown":
        vm_shutdown,

    "restart":
        vm_restart,
}


def resolve_runtime_vm(
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

        if (
            action.get(
                "action"
            )
            == "create-vm"
        ):
            raise LifecycleError(
                "A VM ainda nao existe "
                "no runtime. Execute "
                "Apply Changes primeiro.",
                kind=
                    "runtime-not-created",
                node_id=node_id,
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

            "template_id":
                action.get(
                    "template_id"
                ),

            "runtime_ownership":
                action.get(
                    "runtime_ownership",
                    "managed",
                ),
        }

    raise LifecycleError(
        "Node de VM gerenciado "
        "nao encontrado.",
        kind="vm-node-not-found",
        node_id=node_id,
    )


def execute_vm_lifecycle(
    node_id,
    operation,
):
    operation_func = OPERATIONS.get(
        operation
    )

    if operation_func is None:
        raise LifecycleError(
            "Operacao de lifecycle "
            "nao suportada.",
            kind="invalid-operation",
            node_id=node_id,
            operation=operation,
        )

    runtime = resolve_runtime_vm(
        node_id
    )

    try:
        result = operation_func(
            runtime[
                "domain_name"
            ]
        )

    except AgentError as error:
        raise LifecycleError(
            f"Agent falhou: {error}",
            kind="agent-error",
            node_id=node_id,
            operation=operation,
            cause=error,
        ) from error

    return {
        "status":
            "ok",

        "operation":
            operation,

        "node_id":
            node_id,

        "node_name":
            runtime[
                "node_name"
            ],

        "domain_name":
            runtime[
                "domain_name"
            ],

        "runtime_ownership":
            runtime[
                "runtime_ownership"
            ],

        "result":
            result,
    }


def resolve_managed_vm(
    node_id,
):
    return resolve_runtime_vm(
        node_id
    )


def remove_vm_runtime(
    node_id,
):
    from app.agent_client import (
        vm_undefine,
    )

    runtime = resolve_managed_vm(
        node_id
    )

    if (
        runtime.get(
            "runtime_ownership"
        )
        == "adopted"
    ):
        raise LifecycleError(
            "Runtime adotado e protegido. "
            "Remova apenas o vinculo do "
            "Desired State; o dominio e "
            "seu disco serao preservados.",
            kind=
                "adopted-runtime-protected",
            node_id=node_id,
            operation="remove-runtime",
        )

    try:
        result = vm_undefine(
            runtime[
                "domain_name"
            ]
        )

    except AgentError as error:
        message = str(
            error
        )

        kind = "agent-error"

        if (
            "precisa estar desligado"
            in message
        ):
            kind = "runtime-running"

        raise LifecycleError(
            message,
            kind=kind,
            node_id=node_id,
            operation="remove-runtime",
            cause=error,
        ) from error

    return {
        "status":
            "ok",

        "operation":
            "remove-runtime",

        "node_id":
            node_id,

        "node_name":
            runtime[
                "node_name"
            ],

        "domain_name":
            runtime[
                "domain_name"
            ],

        "result":
            result,
    }
