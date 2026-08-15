from fastapi import (
    APIRouter,
    HTTPException,
    Query,
)
from fastapi.responses import (
    FileResponse,
)

from app.capture_service import (
    CaptureError,
    get_capture_file,
    get_capture_preview,
    get_capture_status,
    start_link_capture,
    stop_capture,
)


router = APIRouter(
    prefix="/api/lab",
    tags=["capture"],
)


def capture_http_error(
    error,
):
    status_code = 400

    if error.kind in {
        "capture-not-found",
        "link-not-capturable",
    }:
        status_code = 404

    elif error.kind in {
        "runtime-not-created",
        "capture-running",
    }:
        status_code = 409

    elif error.kind == "capture-parse-error":
        status_code = 422

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


@router.post(
    "/links/{link_id}/capture/start"
)
def start_capture(
    link_id: str,
):
    try:
        return start_link_capture(
            link_id
        )

    except CaptureError as error:
        capture_http_error(
            error
        )


@router.post(
    "/captures/{capture_id}/stop"
)
def stop_capture_route(
    capture_id: str,
):
    try:
        return stop_capture(
            capture_id
        )

    except CaptureError as error:
        capture_http_error(
            error
        )


@router.get(
    "/captures/{capture_id}"
)
def capture_status_route(
    capture_id: str,
):
    try:
        return get_capture_status(
            capture_id
        )

    except CaptureError as error:
        capture_http_error(
            error
        )


@router.get(
    "/captures/{capture_id}/preview"
)
def capture_preview_route(
    capture_id: str,
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
    ),
):
    try:
        return get_capture_preview(
            capture_id,
            limit=limit,
        )

    except CaptureError as error:
        capture_http_error(
            error
        )


@router.get(
    "/captures/{capture_id}/download"
)
def capture_download(
    capture_id: str,
):
    try:
        path = get_capture_file(
            capture_id
        )

    except CaptureError as error:
        capture_http_error(
            error
        )


    return FileResponse(
        path=str(path),
        media_type=
            "application/vnd.tcpdump.pcap",
        filename=
            f"{capture_id}.pcap",
    )
