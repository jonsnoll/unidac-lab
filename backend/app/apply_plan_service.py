import re


from app.catalog_service import get_device
from app.desired_topology_service import (
    get_desired_topology,
)
from app.image_service import get_image
from app.libvirt_service import (
    get_domains,
    get_networks,
)


LAB_ID = "vxlan-fgt-01"


def node_token(node_id):
    value = node_id.split(":")[-1]

    return (
        value
        .replace("-", "")
        [:8]
        .lower()
    )


def slugify(value):
    value = value.strip().lower()

    value = re.sub(
        r"[^a-z0-9._-]+",
        "-",
        value,
    )

    value = value.strip("-")

    return value or "node"


def runtime_domain_name(node):
    token = node_token(
        node["id"]
    )[:4]

    name = slugify(
        node["name"]
    )[:38]

    return (
        f"ulab-{name}-{token}"
    )


def runtime_network_name(node):
    return (
        f"ulab-net-"
        f"{node_token(node['id'])}"
    )


def runtime_bridge_name(node):
    # Interface Linux precisa ficar curta.
    return (
        f"ulb{node_token(node['id'])}"
    )


def find_links_for_port(
    links,
    node_id,
    port_id,
):
    matches = []

    for link in links:
        if (
            link["source"] == node_id
            and
            link.get("source_port")
            == port_id
        ):
            matches.append(
                (
                    link,
                    link["target"],
                )
            )

        elif (
            link["target"] == node_id
            and
            link.get("target_port")
            == port_id
        ):
            matches.append(
                (
                    link,
                    link["source"],
                )
            )

    return matches


def build_apply_plan():
    desired = (
        get_desired_topology()
    )

    nodes = (
        desired.get("nodes", [])
    )

    links = (
        desired.get("links", [])
    )

    nodes_by_id = {
        node["id"]: node
        for node in nodes
    }

    actual_domains = {
        domain["name"]
        for domain in get_domains()
    }

    actual_networks = {
        network["name"]: network
        for network in get_networks()
    }


    errors = []
    warnings = []
    actions = []


    # Validação estrutural dos links.
    for link in links:
        if (
            link["source"]
            not in nodes_by_id
        ):
            errors.append(
                {
                    "type":
                        "invalid-link",

                    "link_id":
                        link["id"],

                    "message":
                        "Origem do link "
                        "nao existe.",
                }
            )

        if (
            link["target"]
            not in nodes_by_id
        ):
            errors.append(
                {
                    "type":
                        "invalid-link",

                    "link_id":
                        link["id"],

                    "message":
                        "Destino do link "
                        "nao existe.",
                }
            )


    # Infrastructure primeiro.
    for node in nodes:
        device = get_device(
            node["template_id"]
        )

        if device is None:
            errors.append(
                {
                    "type":
                        "unknown-template",

                    "node_id":
                        node["id"],

                    "message":
                        (
                            "Template nao "
                            "encontrado: "
                            f"{node['template_id']}"
                        ),
                }
            )

            continue


        if device["kind"] == "cloud":
            if (
                device["id"]
                != "cloud-nat"
            ):
                errors.append(
                    {
                        "type":
                            "unsupported-cloud",

                        "node_id":
                            node["id"],

                        "message":
                            (
                                "Tipo de cloud "
                                "ainda nao "
                                "suportado."
                            ),
                    }
                )

                continue


            default_network = (
                actual_networks.get(
                    "default"
                )
            )


            if default_network is None:
                errors.append(
                    {
                        "type":
                            "missing-default-network",

                        "node_id":
                            node["id"],

                        "message":
                            (
                                "A rede libvirt "
                                "'default' nao "
                                "existe."
                            ),
                    }
                )

                continue


            if not default_network["active"]:
                errors.append(
                    {
                        "type":
                            "inactive-default-network",

                        "node_id":
                            node["id"],

                        "message":
                            (
                                "A rede libvirt "
                                "'default' esta "
                                "inativa."
                            ),
                    }
                )

                continue


            actions.append(
                {
                    "order": 10,
                    "action":
                        "reuse-network",

                    "node_id":
                        node["id"],

                    "node_name":
                        node["name"],

                    "libvirt_network":
                        "default",

                    "reason":
                        "cloud-nat",
                }
            )


        elif (
            device["kind"]
            == "network"
        ):
            network_name = (
                runtime_network_name(
                    node
                )
            )

            bridge_name = (
                runtime_bridge_name(
                    node
                )
            )


            if (
                network_name
                in actual_networks
            ):
                actions.append(
                    {
                        "order": 20,
                        "action":
                            "reuse-network",

                        "node_id":
                            node["id"],

                        "node_name":
                            node["name"],

                        "libvirt_network":
                            network_name,

                        "bridge":
                            bridge_name,
                    }
                )

            else:
                actions.append(
                    {
                        "order": 20,
                        "action":
                            "create-network",

                        "node_id":
                            node["id"],

                        "node_name":
                            node["name"],

                        "libvirt_network":
                            network_name,

                        "bridge":
                            bridge_name,

                        "mode":
                            "isolated-l2",
                    }
                )


    # QEMU / appliances / endpoints.
    for node in nodes:
        device = get_device(
            node["template_id"]
        )

        if device is None:
            continue


        if (
            device.get("runtime")
            != "qemu"
        ):
            continue


        properties = (
            node.get(
                "properties",
                {},
            )
        )


        image_id = (
            properties.get(
                "image_id"
            )
        )


        if (
            device.get(
                "image_required"
            )
            and
            not image_id
        ):
            errors.append(
                {
                    "type":
                        "missing-image",

                    "node_id":
                        node["id"],

                    "node_name":
                        node["name"],

                    "message":
                        (
                            f"{node['name']}: "
                            "nenhuma imagem "
                            "selecionada."
                        ),
                }
            )

            continue


        image = None

        if image_id:
            image = get_image(
                image_id
            )

            if image is None:
                errors.append(
                    {
                        "type":
                            "unknown-image",

                        "node_id":
                            node["id"],

                        "message":
                            (
                                "Imagem nao "
                                "encontrada: "
                                f"{image_id}"
                            ),
                    }
                )

                continue


            if not image.get(
                "available"
            ):
                errors.append(
                    {
                        "type":
                            "image-unavailable",

                        "node_id":
                            node["id"],

                        "message":
                            (
                                "Arquivo da "
                                "imagem nao "
                                "esta disponivel."
                            ),
                    }
                )

                continue


            if (
                node["template_id"]
                not in image.get(
                    "compatible_templates",
                    [],
                )
            ):
                errors.append(
                    {
                        "type":
                            "incompatible-image",

                        "node_id":
                            node["id"],

                        "message":
                            (
                                "Imagem nao e "
                                "compativel com "
                                "o template."
                            ),
                    }
                )

                continue


        interface_count = int(
            properties.get(
                "interfaces",
                device.get(
                    "defaults",
                    {},
                ).get(
                    "interfaces",
                    1,
                ),
            )
        )


        prefix = (
            device.get(
                "interfaces",
                {},
            ).get(
                "prefix",
                "nic",
            )
        )


        bindings = []


        for index in range(
            1,
            interface_count + 1,
        ):
            port_id = (
                f"{prefix}{index}"
            )

            matches = (
                find_links_for_port(
                    links,
                    node["id"],
                    port_id,
                )
            )


            if len(matches) > 1:
                errors.append(
                    {
                        "type":
                            "duplicate-port-link",

                        "node_id":
                            node["id"],

                        "port":
                            port_id,

                        "message":
                            (
                                f"{node['name']} "
                                f"{port_id}: "
                                "mais de um link."
                            ),
                    }
                )

                continue


            if not matches:
                bindings.append(
                    {
                        "port":
                            port_id,

                        "connected":
                            False,

                        "network":
                            None,
                    }
                )

                continue


            link, peer_id = (
                matches[0]
            )

            peer_node = (
                nodes_by_id.get(
                    peer_id
                )
            )


            if peer_node is None:
                continue


            peer_device = get_device(
                peer_node[
                    "template_id"
                ]
            )


            if peer_device is None:
                continue


            if (
                peer_device["kind"]
                == "cloud"
            ):
                network_name = (
                    "default"
                )

            elif (
                peer_device["kind"]
                == "network"
            ):
                network_name = (
                    runtime_network_name(
                        peer_node
                    )
                )

            else:
                errors.append(
                    {
                        "type":
                            "unsupported-direct-link",

                        "node_id":
                            node["id"],

                        "port":
                            port_id,

                        "link_id":
                            link["id"],

                        "message":
                            (
                                "Link direto "
                                "entre dois "
                                "equipamentos "
                                "ainda nao e "
                                "suportado. "
                                "Use um node "
                                "Network."
                            ),
                    }
                )

                continue


            bindings.append(
                {
                    "port":
                        port_id,

                    "connected":
                        True,

                    "network":
                        network_name,

                    "link_id":
                        link["id"],
                }
            )


        unused_ports = [
            binding["port"]
            for binding in bindings
            if not binding[
                "connected"
            ]
        ]


        if unused_ports:
            warnings.append(
                {
                    "type":
                        "unused-ports",

                    "node_id":
                        node["id"],

                    "node_name":
                        node["name"],

                    "message":
                        (
                            "Portas sem link: "
                            + ", ".join(
                                unused_ports
                            )
                        ),
                }
            )


        domain_name = (
            runtime_domain_name(
                node
            )
        )


        domain_exists = (
            domain_name
            in actual_domains
        )


        actions.append(
            {
                "order": 50,

                "action":
                    (
                        "reuse-vm"
                        if domain_exists
                        else "create-vm"
                    ),

                "node_id":
                    node["id"],

                "node_name":
                    node["name"],

                "template_id":
                    node["template_id"],

                "domain_name":
                    domain_name,

                "vcpu":
                    int(
                        properties.get(
                            "vcpu",
                            1,
                        )
                    ),

                "memory_mb":
                    int(
                        properties.get(
                            "memory_mb",
                            1024,
                        )
                    ),

                "interfaces":
                    bindings,

                "image": (
                    {
                        "id":
                            image["id"],

                        "format":
                            image[
                                "format"
                            ],

                        "deployment":
                            image[
                                "deployment"
                            ],

                        "relative_path":
                            image[
                                "storage"
                            ][
                                "relative_path"
                            ],
                    }
                    if image
                    else None
                ),
            }
        )


    actions.sort(
        key=lambda item:
            item["order"]
    )


    return {
        "lab": LAB_ID,

        "ready":
            len(errors) == 0,

        "summary": {
            "nodes":
                len(nodes),

            "links":
                len(links),

            "actions":
                len(actions),

            "errors":
                len(errors),

            "warnings":
                len(warnings),
        },

        "errors":
            errors,

        "warnings":
            warnings,

        "actions":
            actions,
    }
