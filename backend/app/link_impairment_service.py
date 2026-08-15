from app.agent_client import (
    AgentError,
    link_netem_clear,
    link_netem_set,
    link_netem_status,
)
from app.capture_service import (
    CaptureError,
    resolve_link_target,
)


class LinkImpairmentError(
    RuntimeError
):
    def __init__(
        self,
        message,
        *,
        kind=
            "link-impairment-error",
    ):
        super().__init__(message)

        self.kind = kind


def resolve_target(
    link_id,
):
    try:
        return resolve_link_target(
            link_id
        )

    except CaptureError as error:
        raise LinkImpairmentError(
            str(error),
            kind=error.kind,
        ) from error


def validate_values(
    delay_ms,
    jitter_ms,
    loss_pct,
    rate_mbit,
):
    if not 0 <= delay_ms <= 5000:
        raise LinkImpairmentError(
            "Delay precisa estar entre "
            "0 e 5000 ms.",
            kind="invalid-delay",
        )


    if not 0 <= jitter_ms <= 5000:
        raise LinkImpairmentError(
            "Jitter precisa estar entre "
            "0 e 5000 ms.",
            kind="invalid-jitter",
        )


    if (
        jitter_ms > 0
        and delay_ms == 0
    ):
        raise LinkImpairmentError(
            "Jitter exige delay maior "
            "que zero.",
            kind="invalid-jitter",
        )


    if not 0 <= loss_pct <= 100:
        raise LinkImpairmentError(
            "Loss precisa estar entre "
            "0 e 100%.",
            kind="invalid-loss",
        )


    if not 0 <= rate_mbit <= 100000:
        raise LinkImpairmentError(
            "Bandwidth precisa estar "
            "entre 0 e 100000 Mbit.",
            kind="invalid-rate",
        )


def set_link_impairment(
    link_id,
    *,
    delay_ms,
    jitter_ms,
    loss_pct,
    rate_mbit,
):
    validate_values(
        delay_ms,
        jitter_ms,
        loss_pct,
        rate_mbit,
    )

    target = resolve_target(
        link_id
    )


    try:
        result = link_netem_set(
            target["domain_name"],
            target["port"],
            target["network"],
            delay_ms,
            jitter_ms,
            loss_pct,
            rate_mbit,
        )

    except AgentError as error:
        raise LinkImpairmentError(
            f"Agent falhou: {error}",
            kind="agent-error",
        ) from error


    return {
        "status":
            "ok",

        "link_id":
            link_id,

        "target":
            target,

        "result":
            result,
    }


def clear_link_impairment(
    link_id,
):
    target = resolve_target(
        link_id
    )


    try:
        result = (
            link_netem_clear(
                target["domain_name"],
                target["port"],
                target["network"],
            )
        )

    except AgentError as error:
        raise LinkImpairmentError(
            f"Agent falhou: {error}",
            kind="agent-error",
        ) from error


    return {
        "status":
            "ok",

        "link_id":
            link_id,

        "target":
            target,

        "result":
            result,
    }


def get_link_impairment(
    link_id,
):
    target = resolve_target(
        link_id
    )


    try:
        result = (
            link_netem_status(
                target["domain_name"],
                target["port"],
                target["network"],
            )
        )

    except AgentError as error:
        raise LinkImpairmentError(
            f"Agent falhou: {error}",
            kind="agent-error",
        ) from error


    return {
        "status":
            "ok",

        "link_id":
            link_id,

        "target":
            target,

        "result":
            result,
    }
