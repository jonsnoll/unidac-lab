from fastapi import APIRouter
from fastapi import HTTPException

from app.agent_client import (
    AgentError,
    agent_health,
)
from app.apply_plan_service import (
    build_apply_plan,
)
from app.apply_service import (
    ApplyError,
    execute_apply,
)
from app.lifecycle_service import (
    LifecycleError,
    execute_vm_lifecycle,
    remove_vm_runtime,
)


router = APIRouter(
    prefix="/api/lab",
    tags=["apply"],
)


@router.get("/apply-plan")
def apply_plan():
    return build_apply_plan()



@router.get("/agent/health")
def get_agent_health():
    try:
        return agent_health()

    except AgentError as error:
        raise HTTPException(
            status_code=503,
            detail=str(error),
        ) from error



@router.post("/apply")
def apply_lab():
    try:
        return execute_apply()

    except ApplyError as error:
        status_code = 409

        if error.kind == "agent-error":
            status_code = 502

        raise HTTPException(
            status_code=status_code,
            detail={
                "message":
                    str(error),

                "kind":
                    error.kind,

                "step":
                    error.step,

                "plan":
                    error.plan,
            },
        ) from error



def run_lifecycle_request(
    node_id,
    operation,
):
    try:
        return execute_vm_lifecycle(
            node_id,
            operation,
        )

    except LifecycleError as error:
        status_code = 400

        if (
            error.kind
            == "vm-node-not-found"
        ):
            status_code = 404

        elif (
            error.kind
            == "runtime-not-created"
        ):
            status_code = 409

        elif (
            error.kind
            == "agent-error"
        ):
            status_code = 502

        raise HTTPException(
            status_code=status_code,
            detail={
                "message":
                    str(error),

                "kind":
                    error.kind,

                "node_id":
                    error.node_id,

                "operation":
                    error.operation,
            },
        ) from error


@router.post(
    "/nodes/{node_id}/start"
)
def start_vm_node(
    node_id: str,
):
    return run_lifecycle_request(
        node_id,
        "start",
    )


@router.post(
    "/nodes/{node_id}/shutdown"
)
def shutdown_vm_node(
    node_id: str,
):
    return run_lifecycle_request(
        node_id,
        "shutdown",
    )


@router.post(
    "/nodes/{node_id}/restart"
)
def restart_vm_node(
    node_id: str,
):
    return run_lifecycle_request(
        node_id,
        "restart",
    )



@router.delete(
    "/nodes/{node_id}/runtime"
)
def remove_runtime_vm_node(
    node_id: str,
):
    try:
        return remove_vm_runtime(
            node_id
        )

    except LifecycleError as error:
        status_code = 400

        if (
            error.kind
            == "vm-node-not-found"
        ):
            status_code = 404

        elif (
            error.kind
            == "runtime-running"
        ):
            status_code = 409

        elif (
            error.kind
            == "agent-error"
        ):
            status_code = 502

        raise HTTPException(
            status_code=status_code,
            detail={
                "message":
                    str(error),

                "kind":
                    error.kind,

                "node_id":
                    error.node_id,
            },
        ) from error
