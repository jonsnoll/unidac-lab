from fastapi import APIRouter
from fastapi import HTTPException

from app.agent_client import (
    AgentError,
    agent_health,
)
from app.apply_plan_service import (
    build_apply_plan,
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
