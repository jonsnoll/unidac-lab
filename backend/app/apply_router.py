from fastapi import APIRouter

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
