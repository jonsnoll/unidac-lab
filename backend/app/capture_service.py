import re
import uuid
from pathlib import Path

from app.agent_client import (
    AgentError,
    capture_start,
    capture_status,
    capture_stop,
)
from app.apply_plan_service import (
    build_apply_plan,
)


CAPTURE_ROOT = Path(
    "/var/lib/libvirt/images/"
    "unidac-lab/captures"
)

CAPTURE_ID_RE = re.compile(
    r"^cap-[a-f0-9]{32}$"
)


class CaptureError(RuntimeError):
    def __init__(
        self,
        message,
        *,
        kind="capture-error",
    ):
        super().__init__(message)

        self.kind = kind


def validate_capture_id(
    capture_id,
):
    if not CAPTURE_ID_RE.fullmatch(
        capture_id or ""
    ):
        raise CaptureError(
            "Capture ID invalido.",
            kind="invalid-capture-id",
        )


def resolve_link_target(
    link_id,
):
    plan = build_apply_plan()


    for action in plan.get(
        "actions",
        [],
    ):
        if action.get(
            "action"
        ) not in {
            "create-vm",
            "reuse-vm",
        }:
            continue


        for interface in action.get(
            "interfaces",
            [],
        ):
            if (
                interface.get("link_id")
                != link_id
            ):
                continue


            if not interface.get(
                "connected"
            ):
                raise CaptureError(
                    "Link nao esta conectado.",
                    kind=
                        "link-not-connected",
                )


            if (
                action.get("action")
                == "create-vm"
            ):
                raise CaptureError(
                    "Runtime da VM ainda "
                    "nao existe.",
                    kind=
                        "runtime-not-created",
                )


            return {
                "node_id":
                    action.get(
                        "node_id"
                    ),

                "node_name":
                    action.get(
                        "node_name"
                    ),

                "domain_name":
                    action.get(
                        "domain_name"
                    ),

                "port":
                    interface.get(
                        "port"
                    ),

                "network":
                    interface.get(
                        "network"
                    ),
            }


    raise CaptureError(
        "Link nao possui uma interface "
        "de VM capturavel.",
        kind="link-not-capturable",
    )


def start_link_capture(
    link_id,
):
    target = resolve_link_target(
        link_id
    )


    capture_id = (
        "cap-"
        + uuid.uuid4().hex
    )


    try:
        result = capture_start(
            capture_id,
            target["domain_name"],
            target["port"],
            target["network"],
        )

    except AgentError as error:
        raise CaptureError(
            f"Agent falhou: {error}",
            kind="agent-error",
        ) from error


    return {
        "status":
            "ok",

        "capture_id":
            capture_id,

        "link_id":
            link_id,

        "target":
            target,

        "result":
            result,
    }


def stop_capture(
    capture_id,
):
    validate_capture_id(
        capture_id
    )


    try:
        result = capture_stop(
            capture_id
        )

    except AgentError as error:
        raise CaptureError(
            f"Agent falhou: {error}",
            kind="agent-error",
        ) from error


    return {
        "status":
            "ok",

        "capture_id":
            capture_id,

        "result":
            result,
    }


def get_capture_status(
    capture_id,
):
    validate_capture_id(
        capture_id
    )


    try:
        result = capture_status(
            capture_id
        )

    except AgentError as error:
        raise CaptureError(
            f"Agent falhou: {error}",
            kind="agent-error",
        ) from error


    return {
        "status":
            "ok",

        "capture_id":
            capture_id,

        "result":
            result,
    }


def get_capture_file(
    capture_id,
):
    validate_capture_id(
        capture_id
    )

    status = get_capture_status(
        capture_id
    )

    result = status[
        "result"
    ]


    if result.get(
        "running"
    ):
        raise CaptureError(
            "Pare a captura antes "
            "de fazer download.",
            kind="capture-running",
        )


    path = (
        CAPTURE_ROOT /
        f"{capture_id}.pcap"
    )


    if not path.is_file():
        raise CaptureError(
            "Arquivo PCAP nao encontrado.",
            kind="capture-not-found",
        )


    return path
