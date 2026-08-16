from fastapi import APIRouter, HTTPException

from app.agent_client import (
    AgentError,
    iol_remove,
    iol_restart,
    iol_start,
    iol_stop,
)
from app.apply_plan_service import (
    build_apply_plan,
)


router = APIRouter(
    prefix="/api/lab/iol",
    tags=["iol-runtime"],
)


def resolve_iol_node(node_id):
    plan = build_apply_plan()

    for action in plan.get(
        "actions",
        [],
    ):
        if action.get("node_id") != node_id:
            continue

        if action.get("action") not in {
            "create-iol",
            "reuse-iol",
        }:
            continue

        return action

    raise HTTPException(
        status_code=404,
        detail={
            "message": "Node IOL gerenciado nao encontrado.",
            "kind": "iol-node-not-found",
        },
    )


def require_existing(action):
    if action.get("action") == "create-iol":
        raise HTTPException(
            status_code=409,
            detail={
                "message": (
                    "Runtime IOL ainda nao existe. "
                    "Execute Apply Changes primeiro."
                ),
                "kind": "runtime-not-created",
            },
        )

    instance = action.get("instance_name")
    if not instance:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Apply Plan sem instance_name IOL.",
                "kind": "invalid-iol-plan",
            },
        )

    return instance


def execute(node_id, operation):
    action = resolve_iol_node(node_id)
    instance = require_existing(action)

    operations = {
        "start": iol_start,
        "shutdown": iol_stop,
        "restart": iol_restart,
    }

    function = operations[operation]

    try:
        result = function(instance)
    except AgentError as error:
        raise HTTPException(
            status_code=502,
            detail={
                "message": str(error),
                "kind": "agent-error",
            },
        ) from error

    return {
        "status": "ok",
        "provider": "iol",
        "operation": operation,
        "node_id": node_id,
        "node_name": action.get("node_name"),
        "instance_name": instance,
        "result": result,
    }


@router.post("/nodes/{node_id}/start")
def start(node_id: str):
    return execute(node_id, "start")


@router.post("/nodes/{node_id}/shutdown")
def shutdown(node_id: str):
    return execute(node_id, "shutdown")


@router.post("/nodes/{node_id}/restart")
def restart(node_id: str):
    return execute(node_id, "restart")


@router.delete("/nodes/{node_id}/runtime")
def remove_runtime(node_id: str):
    action = resolve_iol_node(node_id)
    instance = require_existing(action)

    try:
        result = iol_remove(instance)
    except AgentError as error:
        message = str(error)
        status_code = 409 if "desligado" in message else 502
        raise HTTPException(
            status_code=status_code,
            detail={
                "message": message,
                "kind": (
                    "runtime-running"
                    if status_code == 409
                    else "agent-error"
                ),
            },
        ) from error

    return {
        "status": "ok",
        "provider": "iol",
        "operation": "remove-runtime",
        "node_id": node_id,
        "node_name": action.get("node_name"),
        "instance_name": instance,
        "result": result,
    }
