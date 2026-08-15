from fastapi import (
    APIRouter,
    HTTPException,
)
from pydantic import (
    BaseModel,
    Field,
)

from app.link_impairment_service import (
    LinkImpairmentError,
    clear_link_impairment,
    get_link_impairment,
    set_link_impairment,
)


router = APIRouter(
    prefix="/api/lab",
    tags=["link-impairment"],
)


class LinkImpairmentRequest(
    BaseModel
):
    delay_ms: int = Field(
        default=0,
        ge=0,
        le=5000,
    )

    jitter_ms: int = Field(
        default=0,
        ge=0,
        le=5000,
    )

    loss_pct: float = Field(
        default=0,
        ge=0,
        le=100,
    )

    rate_mbit: int = Field(
        default=0,
        ge=0,
        le=100000,
    )


def impairment_error(
    error,
):
    status_code = 400

    if error.kind in {
        "link-not-capturable",
    }:
        status_code = 404

    elif error.kind in {
        "runtime-not-created",
    }:
        status_code = 409

    elif error.kind == "agent-error":
        status_code = 502


    raise HTTPException(
        status_code=status_code,
        detail={
            "message":
                str(error),

            "kind":
                error.kind,
        },
    ) from error


@router.get(
    "/links/{link_id}/impairment"
)
def impairment_status(
    link_id: str,
):
    try:
        return get_link_impairment(
            link_id
        )

    except LinkImpairmentError as error:
        impairment_error(
            error
        )


@router.post(
    "/links/{link_id}/impairment"
)
def impairment_set(
    link_id: str,
    request:
        LinkImpairmentRequest,
):
    try:
        return set_link_impairment(
            link_id,
            delay_ms=
                request.delay_ms,
            jitter_ms=
                request.jitter_ms,
            loss_pct=
                request.loss_pct,
            rate_mbit=
                request.rate_mbit,
        )

    except LinkImpairmentError as error:
        impairment_error(
            error
        )


@router.delete(
    "/links/{link_id}/impairment"
)
def impairment_clear(
    link_id: str,
):
    try:
        return clear_link_impairment(
            link_id
        )

    except LinkImpairmentError as error:
        impairment_error(
            error
        )
