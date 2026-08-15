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
