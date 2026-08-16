
from pathlib import Path

from app.agent_client import (
    AgentError,
    ensure_image,
    ensure_network,
    ensure_overlay,
    ensure_vm,
    ensure_iol,
)
from app.apply_plan_service import (
    LAB_ID,
    build_apply_plan,
)
from app.image_service import (
    get_image,
)


SUPPORTED_VM_TEMPLATES = {
    "fortinet-fortigate-vm":
        "fortigate-kvm",

    "generic-linux-vm":
        "generic-qemu",
}


class ApplyError(RuntimeError):
    def __init__(
        self,
        message,
        *,
        kind="apply-error",
        plan=None,
        step=None,
        cause=None,
    ):
        super().__init__(message)

        self.kind = kind
        self.plan = plan
        self.step = step
        self.cause = cause


def validate_plan_for_execution(
    plan,
):
    if not plan.get("ready"):
        raise ApplyError(
            "Apply bloqueado porque "
            "o plano possui erros.",
            kind="plan-not-ready",
            plan=plan,
        )

    unsupported = []

    for action in plan.get(
        "actions",
        [],
    ):
        if (
            action.get("action")
            not in {
                "create-vm",
                "reuse-vm",
            }
        ):
            continue

        template_id = action.get(
            "template_id"
        )

        if (
            template_id
            not in
            SUPPORTED_VM_TEMPLATES
        ):
            unsupported.append(
                {
                    "node_id":
                        action.get(
                            "node_id"
                        ),

                    "node_name":
                        action.get(
                            "node_name"
                        ),

                    "template_id":
                        template_id,
                }
            )

    if unsupported:
        names = ", ".join(
            item.get(
                "node_name"
            )
            or
            item.get(
                "template_id"
            )
            or
            "unknown"
            for item in unsupported
        )

        raise ApplyError(
            "Apply bloqueado: existem "
            "VMs cujo perfil de runtime "
            "ainda nao e suportado: "
            f"{names}",
            kind="unsupported-vm-profile",
            plan=plan,
        )


def execute_apply():
    plan = build_apply_plan()

    validate_plan_for_execution(
        plan
    )

    results = []

    try:
        for action in plan.get(
            "actions",
            [],
        ):
            action_type = action.get(
                "action"
            )


            # Cisco IOL core runtime.
            # Apply apenas prepara/reutiliza a instancia.
            # Nao envia configuracao IOS e nao conecta dataplane nesta fase.
            if action_type in {
                "create-iol",
                "reuse-iol",
            }:
                result = ensure_iol(
                    action["instance_name"],
                    action["template_id"],
                    action["memory_mb"],
                    action["interfaces"],
                )

                results.append(
                    {
                        "step": "iol",
                        "node_id": action["node_id"],
                        "node_name": action["node_name"],
                        "result": result,
                    }
                )

                continue

            if (
                action_type
                == "reuse-network"
                and
                action.get(
                    "reason"
                )
                in {
                    "cloud-nat",
                    "adopted-network",
                }
            ):
                results.append(
                    {
                        "step":
                            "network",

                        "node_id":
                            action[
                                "node_id"
                            ],

                        "node_name":
                            action[
                                "node_name"
                            ],

                        "result":
                            {
                                "status":
                                    "exists",

                                "network":
                                    action[
                                        "libvirt_network"
                                    ],

                                "reason":
                                    action.get(
                                        "reason"
                                    ),

                                "ownership":
                                    action.get(
                                        "runtime_ownership"
                                    ),
                            },
                    }
                )
                continue

            if action_type in {
                "create-network",
                "reuse-network",
            }:
                network_name = action.get(
                    "libvirt_network"
                )

                bridge_name = action.get(
                    "bridge"
                )

                if not bridge_name:
                    raise ApplyError(
                        "Rede gerenciada sem "
                        "bridge definida.",
                        kind=
                            "invalid-network-action",
                        plan=plan,
                        step=action,
                    )

                result = ensure_network(
                    network_name,
                    bridge_name,
                )

                results.append(
                    {
                        "step":
                            "network",

                        "node_id":
                            action[
                                "node_id"
                            ],

                        "node_name":
                            action[
                                "node_name"
                            ],

                        "result":
                            result,
                    }
                )
                continue

            if (
                action_type
                == "reuse-vm"
                and
                action.get(
                    "runtime_ownership"
                )
                == "adopted"
            ):
                results.append(
                    {
                        "step":
                            "vm",

                        "node_id":
                            action[
                                "node_id"
                            ],

                        "node_name":
                            action[
                                "node_name"
                            ],

                        "result":
                            {
                                "status":
                                    "adopted",

                                "domain":
                                    action[
                                        "domain_name"
                                    ],

                                "domain_uuid":
                                    action.get(
                                        "domain_uuid"
                                    ),

                                "ownership":
                                    "adopted",

                                "changed":
                                    False,
                            },
                    }
                )
                continue

            if action_type in {
                "create-vm",
                "reuse-vm",
            }:
                template_id = action[
                    "template_id"
                ]

                profile = (
                    SUPPORTED_VM_TEMPLATES[
                        template_id
                    ]
                )

                image_spec = action.get(
                    "image"
                )

                if not image_spec:
                    raise ApplyError(
                        "Acao de VM gerenciada "
                        "sem imagem.",
                        kind=
                            "invalid-vm-action",
                        plan=plan,
                        step=action,
                    )

                image_id = image_spec[
                    "id"
                ]

                image = get_image(
                    image_id
                )

                if image is None:
                    raise ApplyError(
                        "Metadata da imagem "
                        "nao encontrada: "
                        f"{image_id}",
                        kind=
                            "image-not-found",
                        plan=plan,
                        step=action,
                    )

                vendor = image.get(
                    "vendor"
                )

                if not vendor:
                    raise ApplyError(
                        "Imagem sem vendor.",
                        kind=
                            "invalid-image",
                        plan=plan,
                        step=action,
                    )

                storage_relative_path = (
                    image.get(
                        "storage",
                        {},
                    ).get(
                        "relative_path"
                    )
                )

                if not storage_relative_path:
                    raise ApplyError(
                        "Imagem sem caminho "
                        "de armazenamento.",
                        kind=
                            "invalid-image-storage",
                        plan=plan,
                        step=action,
                    )

                runtime_image_id = (
                    Path(
                        storage_relative_path
                    )
                    .parent
                    .name
                )

                if not runtime_image_id:
                    raise ApplyError(
                        "Nao foi possivel "
                        "determinar o ID "
                        "runtime da imagem.",
                        kind=
                            "invalid-image-storage",
                        plan=plan,
                        step=action,
                    )

                image_result = ensure_image(
                    vendor,
                    runtime_image_id,
                )

                results.append(
                    {
                        "step":
                            "image",

                        "node_id":
                            action[
                                "node_id"
                            ],

                        "node_name":
                            action[
                                "node_name"
                            ],

                        "result":
                            image_result,
                    }
                )

                overlay_result = ensure_overlay(
                    LAB_ID,
                    action[
                        "domain_name"
                    ],
                    vendor,
                    runtime_image_id,
                )

                results.append(
                    {
                        "step":
                            "overlay",

                        "node_id":
                            action[
                                "node_id"
                            ],

                        "node_name":
                            action[
                                "node_name"
                            ],

                        "result":
                            overlay_result,
                    }
                )

                vm_spec = {
                    "lab_id":
                        LAB_ID,

                    "domain_name":
                        action[
                            "domain_name"
                        ],

                    "profile":
                        profile,

                    "vendor":
                        vendor,

                    "image_id":
                        runtime_image_id,

                    "vcpu":
                        action[
                            "vcpu"
                        ],

                    "memory_mb":
                        action[
                            "memory_mb"
                        ],

                    "interfaces":
                        action[
                            "interfaces"
                        ],
                }

                vm_result = ensure_vm(
                    vm_spec
                )

                results.append(
                    {
                        "step":
                            "vm",

                        "node_id":
                            action[
                                "node_id"
                            ],

                        "node_name":
                            action[
                                "node_name"
                            ],

                        "result":
                            vm_result,
                    }
                )
                continue

            raise ApplyError(
                "Tipo de acao ainda nao "
                "suportado: "
                f"{action_type}",
                kind=
                    "unsupported-action",
                plan=plan,
                step=action,
            )

    except AgentError as error:
        raise ApplyError(
            f"Agent falhou: {error}",
            kind="agent-error",
            plan=plan,
            step=locals().get(
                "action"
            ),
            cause=error,
        ) from error

    final_plan = build_apply_plan()

    return {
        "status":
            "applied",

        "lab":
            LAB_ID,

        "executed":
            len(results),

        "results":
            results,

        "before": {
            "ready":
                plan[
                    "ready"
                ],

            "summary":
                plan[
                    "summary"
                ],
        },

        "after": {
            "ready":
                final_plan[
                    "ready"
                ],

            "summary":
                final_plan[
                    "summary"
                ],
        },
    }
